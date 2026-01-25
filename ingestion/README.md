# CSV Ingestion and Standardization System

A system for ingesting candidate CSV files from multiple sources (SeekOut, Pin Wrangle, Clay, etc.) and standardizing them into a unified format.

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Usage

```bash
# Process single CSV file
python -m ingestion.main sample-data/seekout-export.csv

# Process multiple CSV files
python -m ingestion.main file1.csv file2.csv file3.csv

# Specify output directory
python -m ingestion.main *.csv --output-dir output/

# Skip deduplication
python -m ingestion.main *.csv --no-dedupe

# Verbose output
python -m ingestion.main *.csv --verbose
```

## Output Files

1. **standardized_candidates.csv**: All unique candidates in standard format
2. **duplicates_report.csv**: All duplicate records (if any found)

## Standard Schema

**Required columns:**
- `linkedin_url`
- `first_name`
- `last_name`
- `location`
- `company_name`
- `title`

**Optional columns:**
- `experience_text`
- `education_text`
- `summary`
- `skills`

## How It Works

1. **Source Detection**: Identifies CSV source format by analyzing column names
2. **Column Mapping**: Maps source columns to standard columns using known patterns
3. **Data Extraction**: Extracts and normalizes data from source rows
4. **Deduplication**: Groups records by LinkedIn URL and keeps the most complete record
5. **Output Generation**: Writes standardized CSV and duplicate report

## Adding New Source Formats

Edit `ingestion/config/column_mappings.py` to add mappings for new source formats:

```python
KNOWN_MAPPINGS["new_source"] = {
    "linkedin_url": ["LinkedIn URL", "linkedin", ...],
    "first_name": ["First Name", "fname", ...],
    # ... etc
}
```
