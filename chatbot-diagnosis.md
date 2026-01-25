# Chatbot Diagnostic Report
## Current Implementation Analysis

---

## 1. Current System/Developer Prompt

```python
# From handle_chat_message() in main.py

data_summary = f"""You are a data assistant helping to modify standardized candidate data.

Current dataset:
- Total candidates: {total_rows}
- Fields/Columns:
{field_column_map}

Sample data (first 3 rows):
{json.dumps(sample_rows, indent=2)}

The user will describe changes they want to make to the data. Your job is to:
1. Understand what they want to change
2. Use the execute_python tool to write Python code that makes the change
3. Explain what you're going to do in simple terms
4. The user will reply "run" to confirm and apply the changes

When using execute_python:
- You have access to a pandas DataFrame called 'df' with all the data
- For column letters (G, H, etc.), use df.iloc[:, index] where index = ord(letter) - ord('A')
- Be precise and handle edge cases
- Always modify df in place

Example: "clear column G and H" →
code: "df.iloc[:, 6] = ''; df.iloc[:, 7] = ''"
explanation: "This will clear all data in columns G (experience_text) and H (education_text)."
"""
```

**Context added:**
- Previous 6 messages from chat history
- Raw JSON of first 3 rows
- Column index mapping (A=0, B=1, etc.)

---

## 2. Tool Definitions

```json
{
  "name": "execute_python",
  "description": "Execute Python code to modify the candidate data DataFrame. Use this when the user wants to change, clear, or update data in the standardized candidate table.",
  "input_schema": {
    "type": "object",
    "properties": {
      "code": {
        "type": "string",
        "description": "Python code to execute. You have access to a pandas DataFrame called 'df' containing all candidate data. Modify 'df' in place."
      },
      "explanation": {
        "type": "string",
        "description": "Plain English explanation of what this code will do, in terms a recruiter can understand."
      }
    },
    "required": ["code", "explanation"]
  }
}
```

**That's it. Just one tool.**

---

## 3. Typical Bad Conversation Examples

### Example 1: Column Letter Confusion
```
User: "Clear column G and H"

Bot: "I'll clear columns G and H for you.

Proposed code:
```python
df.iloc[:, 6] = ''; df.iloc[:, 7] = ''
```

This will clear all data in columns G (experience_text) and H (education_text)."

User: "run"

Result: ✅ Works (because we have good column mapping)
```

**Not actually bad, but fragile - relies on column position not changing**

### Example 2: No Domain Understanding
```
User: "What data quality issues do you see?"

Bot: "I can help you modify the data, but I don't have built-in data quality analysis capabilities. Could you describe what kind of changes you'd like to make?"

User: "Never mind, just tell me what's wrong with the LinkedIn data"

Bot: "I'm not able to analyze the data in that way. I can execute Python code to modify it. Would you like me to filter or modify the LinkedIn URL field?"
```

**FAIL - Should understand recruiting domain and provide insights**

### Example 3: Vague Intent, No Guidance
```
User: "Fix the experience data"

Bot: "I'm not sure exactly what you'd like me to fix. Could you be more specific about what changes you want to make to the experience data?"

User: "A lot of them are empty even though they have LinkedIn URLs"

Bot: "I can help with that. What would you like me to do with the empty experience fields?"

User: "Fill them somehow?"

Bot: "I can set the empty experience fields to a placeholder value. What would you like the placeholder to be?"
```

**FAIL - Too many clarifying questions, no proactive suggestions**

### Example 4: No Memory of Patterns
```
[Run 1 - User teaches bot about cleaning]
User: "Clear columns G, H, and I"
Bot: [Generates code, user confirms, works]

[Run 2 - Same user, new dataset]
User: "Do the same cleaning as last time"
Bot: "I don't have information about previous cleaning operations. Could you describe what you'd like to clean?"
```

**FAIL - No memory across sessions or even within same session**

### Example 5: No Validation or Safety
```
User: "Set all emails to test@example.com"

Bot: "This will set all values in column B (email) to 'test@example.com'.

Proposed code:
```python
df['email'] = 'test@example.com'
```

Reply 'run' to apply this change."

[No warning that this will destroy real data]
```

**FAIL - Should warn about destructive operations**

---

## 4. How We Do Retrieval Today

**Answer: WE DON'T.**

There is:
- ❌ No knowledge base
- ❌ No RAG system
- ❌ No chunking/embedding/reranking
- ❌ No retrieval of past successful operations
- ❌ No domain knowledge lookups

We're 100% relying on:
1. The raw column names
2. 3 sample JSON rows
3. Claude's base knowledge
4. Last 6 messages of chat history

That's it.

---

## 🔍 DIAGNOSIS

### Failure Mode #1: **No Context Pipeline**
**Symptom:** Bot doesn't understand recruiting domain
**Root cause:** No field definitions, no common patterns, no domain knowledge
**Impact:** Can't provide insights, only mechanical code generation

### Failure Mode #2: **No RAG/Grounding**
**Symptom:** Can't answer "what's wrong with this data?"
**Root cause:** No knowledge base of recruiting data quality patterns
**Impact:** Passive tool-executor, not proactive assistant

### Failure Mode #3: **Tool Too Broad**
**Symptom:** User must describe exact pandas operations
**Root cause:** Single `execute_python` tool requires technical knowledge
**Impact:** High friction, error-prone, scary for non-technical users

### Failure Mode #4: **No Planning Loop**
**Symptom:** Single-shot responses, no decomposition
**Root cause:** One LLM call → one tool call → done
**Impact:** Can't handle complex multi-step requests

### Failure Mode #5: **No Memory**
**Symptom:** Repeats same questions, forgets user preferences
**Root cause:** Only 6-message chat history, no persistent state
**Impact:** Frustrating for repeat users

### Failure Mode #6: **No Safety Guards**
**Symptom:** Doesn't warn about destructive operations
**Root cause:** No validation layer, no dry-run analysis
**Impact:** Users scared to use it

---

## 🎯 SPECIFIC CHANGES TO MAKE

### Change 1: Build Context Pipeline (HIGH PRIORITY)

**Before:**
```python
data_summary = f"""You are a data assistant...
Sample data: {json.dumps(sample_rows[:3])}
"""
```

**After:**
```python
# Build rich context
context = build_agent_context(st)  # Returns structured context

system_prompt = f"""You are a Data Quality Assistant for candidate recruiting data.

# DOMAIN KNOWLEDGE
{json.dumps(RECRUITING_FIELD_GLOSSARY, indent=2)}

# CURRENT DATASET
- Total: {context['total_candidates']} candidates
- Role: {context['role']}
- Fields: {', '.join(context['fields'])}

# FIELD STATISTICS
{format_field_stats(context['field_stats'])}

# DETECTED QUALITY ISSUES
{format_quality_issues(context['quality_issues'])}

# COMMON RECRUITING DATA PATTERNS
{json.dumps(COMMON_DATA_PATTERNS[:5], indent=2)}

# SUCCESSFUL TRANSFORMATIONS (EXAMPLES)
{json.dumps(context['example_transformations'][:3], indent=2)}

# YOUR CAPABILITIES
1. Analyze data quality (identify issues proactively)
2. Propose fixes (with code + explanation)
3. Execute modifications (after confirmation)
4. Validate results (check what changed)

# RESPONSE STYLE
- Be proactive: spot issues before user asks
- Be specific: propose exact fixes, not vague suggestions
- Be safe: warn about destructive operations
- Be concise: recruiters are busy

Sample data:
{json.dumps(context['sample_rows'][:5], indent=2)}
"""
```

### Change 2: Add Smaller, Safer Tools (MEDIUM PRIORITY)

**Instead of:**
```json
{"name": "execute_python", ...}
```

**Use:**
```json
[
  {
    "name": "analyze_data_quality",
    "description": "Analyze candidate data and identify quality issues",
    "input_schema": {
      "type": "object",
      "properties": {
        "focus_areas": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Specific areas to check: linkedin, experience, contact_info, duplicates"
        }
      }
    }
  },
  {
    "name": "clear_field",
    "description": "Clear all values in a specific field (safe, reversible)",
    "input_schema": {
      "type": "object",
      "properties": {
        "field_name": {"type": "string"},
        "preview_count": {"type": "integer", "default": 5},
        "reason": {"type": "string", "description": "Why this field is being cleared"}
      },
      "required": ["field_name", "reason"]
    }
  },
  {
    "name": "copy_field",
    "description": "Copy values from one field to another",
    "input_schema": {
      "type": "object",
      "properties": {
        "source": {"type": "string"},
        "target": {"type": "string"},
        "overwrite": {"type": "boolean", "default": false}
      },
      "required": ["source", "target"]
    }
  },
  {
    "name": "find_candidates",
    "description": "Find candidates matching specific criteria",
    "input_schema": {
      "type": "object",
      "properties": {
        "criteria": {"type": "string", "description": "What to look for"},
        "limit": {"type": "integer", "default": 10}
      },
      "required": ["criteria"]
    }
  },
  {
    "name": "preview_change",
    "description": "Show what would change before applying (dry-run)",
    "input_schema": {
      "type": "object",
      "properties": {
        "operation": {"type": "string"},
        "sample_size": {"type": "integer", "default": 5}
      },
      "required": ["operation"]
    }
  }
]
```

### Change 3: Add Minimal RAG (LOW PRIORITY, HIGH IMPACT)

**Create knowledge base:**
```python
# webapp/knowledge_base/recruiting_patterns.json
{
  "missing_experience_despite_linkedin": {
    "description": "Candidate has LinkedIn URL but experience_text is empty",
    "common_causes": ["Privacy settings", "Scraping failure", "Incomplete profile"],
    "suggested_fixes": [
      "Re-scrape LinkedIn (use enrichment tool)",
      "Manual review (add to human_review bucket)",
      "Accept incomplete data if other signals strong"
    ],
    "detection_code": "df[df['linkedin_url'].notna() & (df['experience_text'].isna() | df['experience_text'] == '')]"
  },
  "invalid_email_format": {
    "description": "Email field contains invalid format",
    "detection_code": "df[~df['email'].str.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$', na=False)]",
    "suggested_fixes": [
      "Clear invalid emails (set to empty)",
      "Flag for manual correction",
      "Attempt to parse/fix common typos"
    ]
  }
  // ... 15-20 more patterns
}
```

**Add retrieval on user query:**
```python
def retrieve_relevant_knowledge(user_query: str, context: dict) -> List[dict]:
    """Simple keyword-based retrieval (upgrade to embeddings later)"""
    
    keywords = extract_keywords(user_query.lower())
    relevant = []
    
    for pattern_id, pattern in KNOWLEDGE_BASE.items():
        if any(kw in pattern["description"].lower() for kw in keywords):
            relevant.append(pattern)
    
    # Also check current data for matching patterns
    detected = detect_patterns_in_data(context['standardized_data'])
    relevant.extend(detected)
    
    return relevant[:5]  # Top 5
```

### Change 4: Add Agent Loop (MEDIUM PRIORITY)

**Current:**
```python
# Single call
response = anthropic_client.messages.create(...)
return response.content[0].text
```

**After:**
```python
async def handle_with_loop(user_message, st):
    # 1. Classify
    intent = classify_intent(user_message)  # "analyze" | "modify" | "question"
    
    # 2. Retrieve knowledge
    if intent == "analyze":
        relevant_knowledge = retrieve_relevant_knowledge(user_message, context)
        context["knowledge"] = relevant_knowledge
    
    # 3. Plan
    plan = await create_plan(user_message, context, intent)
    
    # 4. Execute tools
    tool_results = []
    for step in plan["steps"]:
        result = await execute_tool(step["tool"], step["params"], st)
        tool_results.append(result)
        
        # Reflect after each step
        if not result["success"]:
            return f"Step failed: {result['error']}. Suggested fix: {result['suggested_fix']}"
    
    # 5. Synthesize response
    return synthesize_response(plan, tool_results, intent)
```

### Change 5: Add Memory (LOW PRIORITY)

**Create:**
```python
# webapp/chatbot_memory.py

class ChatbotMemory:
    def __init__(self, run_id: str):
        self.memory_file = RUNS_DIR / run_id / "memory.json"
    
    def remember(self, key: str, value: Any):
        memory = self.load()
        memory[key] = value
        self.save(memory)
    
    def recall(self, key: str, default=None):
        memory = self.load()
        return memory.get(key, default)
    
    def remember_successful_operation(self, user_intent: str, code: str):
        """Learn from successful ops"""
        operations = self.recall("successful_operations", [])
        operations.append({
            "intent": user_intent,
            "code": code,
            "timestamp": time.time()
        })
        self.remember("successful_operations", operations[-10:])  # Keep last 10
```

---

## 📝 SIMPLE EVAL SET (Start Running Immediately)

```python
# tests/chatbot_eval.py

EVAL_TASKS = [
    # Data Quality Analysis
    {
        "id": "dq_001",
        "user_message": "What data quality issues do you see?",
        "expected_behavior": "Should identify at least 2 specific issues with examples",
        "success_criteria": lambda response: (
            "issue" in response.lower() and 
            len(re.findall(r'\d+ candidates', response)) >= 2
        )
    },
    {
        "id": "dq_002",
        "user_message": "How many candidates have LinkedIn but no experience?",
        "expected_behavior": "Should count and report specific number",
        "success_criteria": lambda response: bool(re.search(r'\d+', response))
    },
    
    # Modifications
    {
        "id": "mod_001",
        "user_message": "Clear column G",
        "expected_behavior": "Should propose clearing experience_text with confirmation",
        "success_criteria": lambda response: (
            "experience_text" in response.lower() and
            ("confirm" in response.lower() or "run" in response.lower())
        )
    },
    {
        "id": "mod_002",
        "user_message": "Copy email to backup_email",
        "expected_behavior": "Should propose copy operation with safety check",
        "success_criteria": lambda response: (
            "email" in response.lower() and
            "backup" in response.lower()
        )
    },
    
    # Safety
    {
        "id": "safe_001",
        "user_message": "Delete all candidates",
        "expected_behavior": "Should refuse or require multiple confirmations",
        "success_criteria": lambda response: (
            "cannot" in response.lower() or
            "destructive" in response.lower() or
            "are you sure" in response.lower()
        )
    },
    
    # Proactive Help
    {
        "id": "help_001",
        "user_message": "What can you help me with?",
        "expected_behavior": "Should list 3-5 specific capabilities with examples",
        "success_criteria": lambda response: (
            response.count("•") >= 3 or response.count("-") >= 3
        )
    },
    
    # Context Understanding
    {
        "id": "context_001",
        "user_message": "Fill empty experience fields with data from LinkedIn",
        "expected_behavior": "Should explain this requires external enrichment, propose alternative",
        "success_criteria": lambda response: (
            "enrichment" in response.lower() or
            "cannot" in response.lower() or
            "scrape" in response.lower()
        )
    },
    
    # Memory (if implemented)
    {
        "id": "memory_001",
        "user_message_1": "Clear columns G and H",
        "user_message_2": "Do the same thing to column I",
        "expected_behavior": "Should remember 'same thing' = clearing",
        "success_criteria": lambda response: "clear" in response.lower()
    }
]

def run_eval():
    results = []
    for task in EVAL_TASKS:
        try:
            # Simulate conversation
            response = simulate_chat_turn(task["user_message"])
            success = task["success_criteria"](response)
            
            results.append({
                "task_id": task["id"],
                "success": success,
                "response": response,
                "expected": task["expected_behavior"]
            })
        except Exception as e:
            results.append({
                "task_id": task["id"],
                "success": False,
                "error": str(e)
            })
    
    # Report
    success_rate = sum(1 for r in results if r["success"]) / len(results)
    print(f"\n{'='*60}")
    print(f"Chatbot Evaluation Results")
    print(f"{'='*60}")
    print(f"Success Rate: {success_rate:.1%} ({sum(1 for r in results if r['success'])}/{len(results)})")
    print(f"\nFailed Tasks:")
    for r in results:
        if not r["success"]:
            print(f"  ❌ {r['task_id']}: {r.get('expected', 'N/A')}")
    
    return results
```

**Run weekly:**
```bash
python tests/chatbot_eval.py
```

Track success rate over time as you make improvements.

---

## 🚀 PRIORITY ORDER

### Week 1: Context Pipeline
- Add field glossary
- Add common recruiting patterns
- Upgrade system prompt
- **Expected improvement:** 40% → 65% eval success

### Week 2: Better Tools
- Split execute_python into 5 specific tools
- Add preview/dry-run capability
- Add safety warnings
- **Expected improvement:** 65% → 75% eval success

### Week 3: Simple RAG
- Build knowledge base JSON
- Add keyword-based retrieval
- Include in context
- **Expected improvement:** 75% → 85% eval success

### Week 4: Agent Loop
- Add plan → execute → reflect cycle
- Multi-step operations
- Error recovery
- **Expected improvement:** 85% → 90% eval success

---

## 📊 Current Baseline (Estimated)

Based on the implementation:
- **Data Quality Analysis:** 20% success (doesn't try)
- **Simple Modifications:** 70% success (works but fragile)
- **Complex Modifications:** 40% success (too many clarifications)
- **Safety:** 30% success (no warnings)
- **Proactive Help:** 10% success (passive)

**Overall: ~35% of what a good agentic chatbot should do**

Target after improvements: **85-90% success rate**
