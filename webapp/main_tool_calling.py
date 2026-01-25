# Tool calling implementation for data assistant

import csv
import json
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
import traceback


def execute_data_modification(code: str, standardized_data: List[Dict], run_dir: Path) -> Dict[str, Any]:
    """
    Execute Python code to modify standardized data.
    
    Args:
        code: Python code to execute (has access to 'df' pandas DataFrame)
        standardized_data: Current standardized data as list of dicts
        run_dir: Path to run directory
        
    Returns:
        Dict with 'success', 'message', and optionally 'modified_data'
    """
    try:
        # Convert to DataFrame
        df = pd.DataFrame(standardized_data)
        
        # Create namespace for code execution
        namespace = {
            'df': df,
            'pd': pd,
            'json': json,
            'Path': Path,
        }
        
        # Execute the code
        exec(code, namespace)
        
        # Get modified DataFrame
        df_modified = namespace['df']
        
        # Convert back to list of dicts
        modified_data = df_modified.to_dict('records')
        
        # Update the standardized output CSV file directly (don't touch input files)
        output_dir = run_dir / "output"
        standardized_csv = output_dir / "standardized_candidates.csv"
        
        try:
            # Write modified data to standardized output
            if len(modified_data) > 0:
                fieldnames = list(modified_data[0].keys())
                with open(standardized_csv, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(modified_data)
        except Exception as e:
            print(f"Error updating standardized CSV: {e}")
        
        return {
            'success': True,
            'message': f'Successfully modified {len(modified_data)} candidates.',
            'modified_data': modified_data
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Error executing code: {str(e)}',
            'traceback': traceback.format_exc()
        }


# Tool definition for Claude
EXECUTE_PYTHON_TOOL = {
    "name": "execute_python",
    "description": """Execute Python code to modify the candidate data.
    
You have access to a pandas DataFrame called 'df' containing all the standardized candidate data.

Common operations:
- Clear columns: df['column_name'] = ''
- Clear multiple columns: df[['col1', 'col2']] = ''
- Move data: df['target'] = df['source']; df['source'] = ''
- Filter/update rows: df.loc[df['condition'], 'column'] = new_value
- Get columns by position: df.iloc[:, 6] (0-indexed, so column G = index 6)

Example clearing columns G and H (experience_text and education_text):
df.iloc[:, 6] = ''
df.iloc[:, 7] = ''

The code should modify the 'df' variable in place.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute. Has access to pandas DataFrame 'df'."
            },
            "explanation": {
                "type": "string",
                "description": "Brief explanation in recruiting/business language; do not include any code."
            }
        },
        "required": ["code", "explanation"]
    }
}
