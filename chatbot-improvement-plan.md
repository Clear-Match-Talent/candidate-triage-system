# Chatbot Improvement Plan
## Based on Agentic Chatbot Best Practices

**Goal:** Transform the data assistant from "basic LLM wrapper" to "genuinely useful agentic tool"

---

## 🚨 Critical Gaps (vs Best Practices)

### 1. No Context Pipeline
**Current:** Sending raw sample rows + minimal system prompt
**Should be:** Structured context with domain knowledge, schema definitions, common patterns

### 2. No RAG/Knowledge Base
**Current:** No grounding in recruiting domain or data quality patterns
**Should be:** KB of common issues, transformations, field meanings

### 3. Weak Tool Design
**Current:** One monolithic `execute_python` tool
**Should be:** Small, composable, validated tools with dry-run

### 4. No Agent Loop
**Current:** Single-shot LLM call
**Should be:** Plan → Execute → Reflect → Respond

### 5. No Memory
**Current:** Only last 6 chat messages
**Should be:** User preferences, learned patterns, session state

### 6. No Evaluation
**Current:** No metrics
**Should be:** Task success rate, hallucination checks, user satisfaction

---

## 📋 Implementation Plan

### **PHASE 1: Context Pipeline (Week 1)**

#### 1.1 Create Domain Knowledge Base
```python
# webapp/chatbot_knowledge.py

RECRUITING_FIELD_GLOSSARY = {
    "linkedin_url": {
        "description": "Candidate's LinkedIn profile URL",
        "common_issues": ["Missing", "Invalid format", "Privacy settings prevent access"],
        "validation": "Must start with https://linkedin.com/in/ or https://www.linkedin.com/in/",
        "importance": "high"
    },
    "experience_text": {
        "description": "Raw text of work experience from source",
        "common_issues": ["Empty despite LinkedIn URL", "Mixed with education", "Poorly formatted"],
        "cleanup_patterns": ["Remove job posting text", "Standardize date formats"],
        "importance": "critical"
    },
    "current_company": {
        "description": "Most recent employer",
        "common_issues": ["'Freelance'", "'Self-employed'", "Out of date"],
        "derivation": "Usually extracted from experience_text or LinkedIn",
        "importance": "high"
    },
    # ... add all standardized fields
}

COMMON_DATA_QUALITY_ISSUES = [
    {
        "issue": "Missing experience data despite LinkedIn URL",
        "cause": "Privacy settings or scraping failure",
        "fix": "Re-scrape or manual enrichment",
        "code_pattern": "df[df['linkedin_url'].notna() & df['experience_text'].isna()]"
    },
    {
        "issue": "Duplicate candidates with different emails",
        "cause": "Multiple applications or data source merges",
        "fix": "Use ingestion deduplication or manual review",
        "code_pattern": "df.groupby('full_name')['email'].nunique() > 1"
    },
    # ... add more patterns
]

SUCCESSFUL_TRANSFORMATIONS = [
    {
        "user_intent": "Clear all experience data",
        "code": "df['experience_text'] = ''; df['current_company'] = ''; df['current_title'] = ''",
        "explanation": "Clears all experience-related fields",
        "use_when": "User wants to reset experience data before re-enrichment"
    },
    {
        "user_intent": "Copy field A to field B",
        "code": "df['target_field'] = df['source_field']",
        "explanation": "Copies values from one column to another",
        "use_when": "User wants to duplicate or move data between columns"
    },
    # ... add more examples
]
```

#### 1.2 Build Context Builder
```python
# webapp/chatbot_context.py

def build_agent_context(st: RunStatus) -> dict:
    """Build structured context for the agent"""
    
    if not st.standardized_data:
        return {"error": "No data loaded"}
    
    fields = list(st.standardized_data[0].keys())
    total_rows = len(st.standardized_data)
    
    # Data quality analysis
    quality_issues = analyze_data_quality(st.standardized_data)
    
    # Field usage stats
    field_stats = {
        field: {
            "filled": sum(1 for row in st.standardized_data if row.get(field)),
            "empty": sum(1 for row in st.standardized_data if not row.get(field)),
            "unique": len(set(row.get(field, '') for row in st.standardized_data))
        }
        for field in fields
    }
    
    return {
        "dataset_info": {
            "total_candidates": total_rows,
            "fields": fields,
            "role": st.role_label
        },
        "field_definitions": {
            field: RECRUITING_FIELD_GLOSSARY.get(field, {"description": "Unknown field"})
            for field in fields
        },
        "field_stats": field_stats,
        "quality_issues": quality_issues,
        "sample_rows": st.standardized_data[:3],
        "common_issues": COMMON_DATA_QUALITY_ISSUES,
        "example_transformations": SUCCESSFUL_TRANSFORMATIONS[:5]
    }

def analyze_data_quality(data: List[dict]) -> List[dict]:
    """Detect common data quality issues"""
    issues = []
    
    # Check for missing critical fields
    for field in ["email", "full_name"]:
        missing = sum(1 for row in data if not row.get(field))
        if missing > 0:
            issues.append({
                "severity": "critical",
                "issue": f"{missing} candidates missing {field}",
                "affected_rows": missing
            })
    
    # Check for LinkedIn URLs without experience
    linkedin_no_exp = sum(
        1 for row in data 
        if row.get("linkedin_url") and not row.get("experience_text")
    )
    if linkedin_no_exp > 0:
        issues.append({
            "severity": "high",
            "issue": f"{linkedin_no_exp} LinkedIn profiles without experience data",
            "affected_rows": linkedin_no_exp,
            "suggested_fix": "Re-scrape or use enrichment tool"
        })
    
    return issues
```

#### 1.3 Upgrade System Prompt
```python
# In handle_chat_message():

def build_system_prompt(context: dict) -> str:
    """Build rich system prompt with domain knowledge"""
    
    return f"""You are a Data Quality Assistant for candidate recruitment data.

# YOUR ROLE
Help recruiters clean, standardize, and prepare candidate data for evaluation.
You have deep knowledge of recruiting data patterns, common quality issues, and best practices.

# CURRENT DATASET
- **Total candidates:** {context['dataset_info']['total_candidates']}
- **Role:** {context['dataset_info']['role']}
- **Fields:** {len(context['dataset_info']['fields'])} columns

# FIELD DEFINITIONS
{json.dumps(context['field_definitions'], indent=2)}

# FIELD STATISTICS
{json.dumps(context['field_stats'], indent=2)}

# DETECTED QUALITY ISSUES
{json.dumps(context['quality_issues'], indent=2)}

# COMMON DATA ISSUES IN RECRUITING
{json.dumps(context['common_issues'][:3], indent=2)}

# EXAMPLE TRANSFORMATIONS
{json.dumps(context['example_transformations'], indent=2)}

# YOUR CAPABILITIES
You can help with:
1. **Data quality analysis** - Identify missing, invalid, or inconsistent data
2. **Field transformations** - Clear, copy, derive, or standardize fields
3. **Pattern detection** - Find duplicates, outliers, or anomalies
4. **Batch operations** - Apply changes to all or filtered candidates

# TOOL USAGE RULES
- Use `execute_python` to propose data modifications
- Always explain what you're going to do in plain English
- Show the code you'll run for transparency
- Wait for user confirmation before applying changes
- Be conservative - prefer smaller, safer changes
- If unsure, ask clarifying questions (max 1 at a time)

# RESPONSE STYLE
- Be concise and action-oriented
- Propose specific fixes, not vague suggestions
- When showing code, explain it in recruiter terms
- Use bullet points for multiple issues
- Suggest next steps after each action

# SAFETY
- Never delete candidate records (only clear fields)
- Always validate field names before operations
- Check for edge cases (empty values, special characters)
- Warn about destructive operations

---

Sample data (first 3 rows):
{json.dumps(context['sample_rows'], indent=2)}
"""
```

### **PHASE 2: Better Tools (Week 2)**

Break `execute_python` into specific, validated operations:

```python
# webapp/chatbot_tools.py

CHATBOT_TOOLS = [
    {
        "name": "analyze_field",
        "description": "Get detailed statistics about a specific field",
        "input_schema": {
            "type": "object",
            "properties": {
                "field_name": {"type": "string"},
                "include_examples": {"type": "boolean", "default": True}
            },
            "required": ["field_name"]
        }
    },
    {
        "name": "clear_field",
        "description": "Clear all values in a specific field (sets to empty string)",
        "input_schema": {
            "type": "object",
            "properties": {
                "field_name": {"type": "string"},
                "dry_run": {"type": "boolean", "default": True}
            },
            "required": ["field_name"]
        }
    },
    {
        "name": "copy_field",
        "description": "Copy values from one field to another",
        "input_schema": {
            "type": "object",
            "properties": {
                "source_field": {"type": "string"},
                "target_field": {"type": "string"},
                "overwrite_existing": {"type": "boolean", "default": False},
                "dry_run": {"type": "boolean", "default": True}
            },
            "required": ["source_field", "target_field"]
        }
    },
    {
        "name": "filter_candidates",
        "description": "Show candidates matching specific criteria",
        "input_schema": {
            "type": "object",
            "properties": {
                "condition": {"type": "string", "description": "Python boolean expression"},
                "limit": {"type": "integer", "default": 10}
            },
            "required": ["condition"]
        }
    },
    {
        "name": "detect_duplicates",
        "description": "Find potential duplicate candidates based on specified fields",
        "input_schema": {
            "type": "object",
            "properties": {
                "match_fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Fields to compare (e.g., ['email', 'linkedin_url'])"
                }
            },
            "required": ["match_fields"]
        }
    },
    {
        "name": "validate_field",
        "description": "Check if field values match expected format/pattern",
        "input_schema": {
            "type": "object",
            "properties": {
                "field_name": {"type": "string"},
                "validation_type": {
                    "type": "string",
                    "enum": ["email", "url", "phone", "date", "regex"]
                },
                "pattern": {"type": "string", "description": "Regex pattern (if validation_type=regex)"}
            },
            "required": ["field_name", "validation_type"]
        }
    }
]
```

### **PHASE 3: Agent Loop (Week 3)**

Implement Plan → Execute → Reflect pattern:

```python
# webapp/chatbot_agent.py

async def handle_message_with_loop(run_id: str, user_message: str, st: RunStatus) -> str:
    """Agent loop: classify → plan → execute → reflect → respond"""
    
    # 1. CLASSIFY INTENT
    intent = classify_intent(user_message, st)
    # Returns: "analyze" | "modify" | "question" | "confirm"
    
    if intent == "confirm":
        return handle_confirmation(st)
    
    # 2. BUILD CONTEXT
    context = build_agent_context(st)
    
    # 3. PLAN (ask Claude to think through the steps)
    plan = await create_plan(user_message, context, intent)
    # Returns: {"steps": [...], "tools_needed": [...], "risks": [...]}
    
    # 4. EXECUTE (run tools, collect results)
    results = await execute_plan(plan, st)
    
    # 5. REFLECT (did we succeed? any issues?)
    reflection = await reflect_on_results(plan, results, user_message)
    # Returns: {"success": bool, "issues": [...], "next_steps": [...]}
    
    # 6. RESPOND
    if reflection["success"]:
        # If destructive, ask confirmation
        if plan.get("needs_confirmation"):
            st.pending_action = {
                "plan": plan,
                "results": results,
                "timestamp": time.time()
            }
            save_run_to_db(st)
            return format_confirmation_prompt(plan, results)
        else:
            # Safe operation, auto-apply
            apply_changes(st, results)
            return format_success_response(plan, results, reflection["next_steps"])
    else:
        return format_error_response(reflection["issues"], suggested_fixes=reflection.get("suggested_fixes"))
```

### **PHASE 4: Memory & Learning (Week 4)**

Add persistent memory:

```python
# webapp/chatbot_memory.py

class ChatbotMemory:
    """Remember user preferences and successful patterns"""
    
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.memory_file = RUNS_DIR / run_id / "chatbot_memory.json"
    
    def remember_preference(self, key: str, value: Any):
        """Store user preference"""
        memory = self.load()
        memory["preferences"][key] = value
        self.save(memory)
    
    def remember_successful_transformation(self, user_intent: str, code: str, result: str):
        """Learn from successful operations"""
        memory = self.load()
        memory["successful_transformations"].append({
            "intent": user_intent,
            "code": code,
            "result": result,
            "timestamp": time.time()
        })
        self.save(memory)
    
    def recall_similar_intent(self, current_intent: str) -> Optional[dict]:
        """Find similar past operations"""
        memory = self.load()
        # Use simple text similarity or embeddings
        for trans in memory.get("successful_transformations", []):
            if similarity(trans["intent"], current_intent) > 0.8:
                return trans
        return None
```

### **PHASE 5: Evaluation Framework (Week 5)**

Build test harness:

```python
# webapp/chatbot_eval.py

EVAL_TASKS = [
    {
        "id": "clear_single_column",
        "user_message": "Clear column G",
        "expected_tool": "clear_field",
        "expected_params": {"field_name": "experience_text"},
        "success_criteria": lambda result: result["tool"] == "clear_field"
    },
    {
        "id": "copy_field_simple",
        "user_message": "Copy email to backup_email",
        "expected_tool": "copy_field",
        "expected_params": {"source_field": "email", "target_field": "backup_email"},
        "success_criteria": lambda result: result["params"]["source_field"] == "email"
    },
    {
        "id": "analyze_quality",
        "user_message": "What data quality issues do you see?",
        "expected_tool": None,  # Should use analysis, not modifications
        "success_criteria": lambda result: "quality" in result["response"].lower()
    },
    # ... 20-50 more real tasks
]

def run_eval():
    """Run evaluation suite and generate report"""
    results = []
    for task in EVAL_TASKS:
        result = simulate_user_message(task["user_message"])
        success = task["success_criteria"](result)
        results.append({
            "task_id": task["id"],
            "success": success,
            "response": result,
            "timestamp": time.time()
        })
    
    report = generate_eval_report(results)
    print(report)
    return results
```

---

## 🎯 Quick Wins (Do This Weekend)

If you want immediate improvement with minimal code:

### 1. Upgrade System Prompt (30 min)
Add field glossary + common patterns to system prompt

### 2. Add Dry-Run (1 hour)
Before executing any Python code, show:
- Which rows will be affected
- Before/after preview (first 3 rows)
- "This will modify X candidates. Confirm?"

### 3. Better Error Messages (30 min)
When regex fails to parse intent:
```python
return """I'm not sure how to help with that. Here's what I can do:

**Data Quality:**
- "Show me candidates with missing emails"
- "Find duplicates"
- "Check LinkedIn URL validity"

**Modifications:**
- "Clear column G" (clears experience_text)
- "Copy email to backup_email"
- "Set all current_company to '[To be enriched]'"

**Analysis:**
- "What's the data quality like?"
- "Show me field statistics"

What would you like to do?"""
```

### 4. Add "Suggest Next Steps" (30 min)
After every response, add:
```python
next_steps = [
    "✨ Approve and run evaluation",
    "🔍 Analyze data quality",
    "📋 Show field statistics",
    "🧹 Clear another column"
]
return response + "\n\n**Suggested next steps:**\n" + "\n".join(next_steps)
```

---

## 📊 Success Metrics

Track these to know if improvements are working:

1. **Task Success Rate**: % of user intents correctly executed
2. **Confirmation Rounds**: Avg # of back-and-forth messages to complete task
3. **Tool Accuracy**: % of correct tool selections
4. **Hallucination Rate**: % of responses with invented data
5. **User Satisfaction**: Thumbs up/down after each response

---

## 🚀 Recommended Immediate Action

**Start with Phase 1.1 + 1.2 this weekend:**
1. Create `chatbot_knowledge.py` with field glossary
2. Create `chatbot_context.py` with context builder
3. Update system prompt in `handle_chat_message()`

This alone will make the chatbot feel 3x smarter without changing tool architecture.

Want me to implement any of these phases now?
