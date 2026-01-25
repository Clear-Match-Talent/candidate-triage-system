# Agent-Native Architecture Principles
## Philosophical Foundation for Candidate Triage System

> **Source:** Agent-native Architectures guide (Dan Shipper & Claude)
> **Applied to:** Candidate Triage System - specifically the Data Assistant chatbot

---

## Core Principles

### 1. **Parity**
**Definition:** Whatever the user can do through the UI, the agent should be able to achieve through tools.

**Test:** Pick any UI action. Can the agent accomplish it?

**Current State:**
- ❌ User can manually edit CSV columns → Agent cannot
- ❌ User can re-run enrichment → Agent cannot trigger
- ❌ User can export filtered results → Agent cannot
- ✅ User can clear fields → Agent can (via execute_python)

**Goal:** Agent should be able to:
- Trigger re-standardization after modifications
- Initiate AI evaluation workflow
- Export/download specific data subsets
- Manage run lifecycle (approve, restart, delete)
- Access all data quality analysis the UI shows

---

### 2. **Granularity**
**Definition:** Tools should be atomic primitives. Features are outcomes achieved by an agent operating in a loop.

**Test:** To change behavior, do you edit prompts or refactor code?

**Current State:**
- ❌ `execute_python` - monolithic tool that bundles judgment
- User must describe exact pandas operations
- Agent is a code executor, not outcome pursuer

**Anti-pattern we're doing:**
```python
# WRONG - bundled judgment
{
  "name": "execute_python",
  "description": "Execute Python code to modify data..."
}
```

**Agent-native approach:**
```python
# RIGHT - atomic primitives
[
  {"name": "analyze_field", ...},      # One action
  {"name": "clear_field", ...},        # One action  
  {"name": "copy_field", ...},         # One action
  {"name": "find_candidates", ...},    # One action
  {"name": "validate_field", ...}      # One action
]
```

**Prompt describes outcome:**
```
"Review the experience data. If fields are empty despite LinkedIn URLs,
propose a cleanup strategy. Execute if safe."
```

Agent composes tools until outcome achieved.

---

### 3. **Composability**
**Definition:** With atomic tools and parity, create new features just by writing new prompts.

**Test:** Can you add features without code changes?

**Current State:**
- ❌ New data quality check = code change
- ❌ New transformation pattern = code change
- ❌ New analysis type = code change

**Agent-Native Vision:**
```
# New feature: "Weekly data quality report"
# Just add a prompt - no code change

System Prompt Addition:
"Every Monday, analyze all runs from past week.
Report: common quality issues, success rates,
frequently cleared fields. Store in reports/weekly-{date}.md"

Tools used: list_runs, analyze_quality, write_file
```

**Another example:**
```
User: "Find candidates who worked at FAANG companies"

Agent:
1. find_candidates(criteria="experience_text contains Google|Meta|Apple|Amazon")
2. Presents results
3. User: "Export to CSV"
4. export_data(format="csv", filters=last_search)

No "FAANG filter" feature needed - emerged from composition.
```

---

### 4. **Emergent Capability**
**Definition:** Agent can accomplish things you didn't explicitly design for.

**Test:** Can it handle open-ended requests in your domain?

**Current State:**
- ❌ "What's the quality of this data?" → "I can't analyze"
- ❌ "Find duplicates by company+title" → "I can't search"
- ❌ "Compare this batch to last week's" → "I don't have history"

**Agent-Native Vision:**
```
User: "Cross-reference candidates with our past hires database
and flag anyone we've already contacted"

Agent (composed from primitives):
1. read_file("past_hires.csv")
2. find_candidates(current_run)
3. compare(field="email", field2="linkedin_url")
4. tag_candidates(matches, flag="previously_contacted")
5. Present results with counts

You didn't build "dedupe against past hires" feature.
Agent figured it out.
```

**Latent Demand Discovery:**
- Build capable foundation
- Observe what users ask agent to do
- When patterns emerge → optimize with domain tools or prompts
- You discover features, not guess them

---

### 5. **Improvement Over Time**
**Definition:** Agent-native apps get better through accumulated context and prompt refinement.

**Mechanisms:**
1. **Accumulated Context** - State persists across sessions
2. **Developer Refinement** - Ship updated prompts for all users
3. **User Customization** - Users modify prompts for their workflow
4. **Learning from Operations** - Successful patterns become examples

**Current State:**
- ❌ No context accumulation (starts fresh each run)
- ❌ No learning from successful operations
- ❌ No user customization of behavior

**Agent-Native Vision:**

`/runs/{run_id}/context.md`:
```markdown
# Data Assistant Context

## What I Know About This Run
- Role: Senior Backend Engineer
- 127 candidates processed
- Common issue: 43 missing experience despite LinkedIn
- User prefers: clearing empty fields vs placeholder text

## Successful Operations This Session
1. Cleared columns G, H for data reset
2. User confirmed this prevents enrichment conflicts

## Learned Patterns
- This user always clears experience before re-enrichment
- They prefer concise explanations, not verbose code
```

`/memory/chatbot_learnings.json`:
```json
{
  "common_workflows": [
    {
      "pattern": "clear_experience_before_enrichment",
      "frequency": 12,
      "typical_sequence": ["clear_field(experience_text)", "clear_field(current_company)"]
    }
  ],
  "user_preferences": {
    "explanation_style": "concise",
    "confirmation_threshold": "destructive_only"
  }
}
```

---

## Practical Patterns

### Context Files

**The `context.md` Pattern:**

Create `/runs/{run_id}/agent_context.md`:

```markdown
# Data Assistant Context

## Who I Am
Data quality assistant for recruiting candidate triage.

## What I Know About This Dataset
- Total candidates: 127
- Role: Senior Backend Engineer  
- Fields: 15 columns (see field_definitions.json)
- Quality issues detected: 3 (see quality_report.json)

## What Exists
- Standardized data: runs/{run_id}/output/standardized_candidates.csv
- Quality report: runs/{run_id}/analysis/quality_issues.json
- User modifications log: runs/{run_id}/agent_log.md

## Recent Activity
- User cleared columns G, H (5 minutes ago)
- Re-standardization completed (3 minutes ago)
- User asked about duplicate detection (2 minutes ago)

## My Guidelines
- Always preview destructive changes before applying
- Explain in recruiter terms, not technical jargon
- Proactively spot quality issues
- Cite specific row numbers when giving examples

## Current State
- Run state: standardized (ready for evaluation)
- Pending actions: None
- Last tool executed: clear_field(experience_text)
```

Agent reads this at session start, updates as state changes.

### Files as Universal Interface

**Why files work for agents:**
- ✅ **Already Known** - Agents understand file operations naturally
- ✅ **Inspectable** - Users can see what agent created
- ✅ **Portable** - Export, backup, sync trivial
- ✅ **Self-Documenting** - `/runs/backend-engineer-batch/notes.md` is clear

**Our Directory Structure:**
```
runs/
├── {run_id}/
│   ├── meta.json              # Run metadata
│   ├── input/                 # Original CSVs
│   ├── output/                # Pipeline outputs
│   ├── analysis/              # Agent-generated analysis
│   │   ├── quality_report.json
│   │   ├── field_stats.json
│   │   └── recommendations.md
│   ├── agent_context.md       # Agent working memory
│   ├── agent_log.md          # Agent action history
│   └── memory.json           # Learned preferences
```

**Agent can naturally:**
```python
# Discover what exists
list_files("runs/abc123/output")

# Read data
read_file("runs/abc123/output/standardized_candidates.csv")

# Write analysis
write_file("runs/abc123/analysis/quality_report.md", content)

# Update context
append_file("runs/abc123/agent_log.md", "Cleared experience_text")
```

### Tool Design Principles

**Atomic Primitives (Good):**
```python
analyze_field(field_name, include_examples=True)
clear_field(field_name, preview_count=5)
copy_field(source, target, overwrite=False)
find_candidates(criteria, limit=10)
validate_field(field_name, validation_type="email")
```

**Bundled Workflow (Anti-pattern):**
```python
# WRONG - bundles too much judgment
analyze_and_fix_quality_issues()
smart_organize_data()
```

**Domain Tools as Shortcuts:**

Start with primitives:
- `read_file`, `write_file`, `list_files`
- Generic, flexible, composable

Add domain tools for common patterns:
- `analyze_recruiting_data()` - knows what to look for
- `detect_duplicates()` - knows common matching strategies
- `validate_contact_info()` - knows email/phone/LinkedIn patterns

**Key:** Domain tools are shortcuts, not gates. Primitives still available.

### Dynamic Capability Discovery

**Instead of 50 static tools for 50 data types:**

```python
# Two tools handle everything

list_available_fields()
→ ["email", "linkedin_url", "experience_text", "current_company", ...]

analyze_field(field_name, analysis_type)
→ works with any discovered field

# When new field added to schema...
# Agent automatically discovers it
# No code change needed
```

**When to use:**
- Dataset schema changes over time
- Want agent to work with any field
- Don't want to maintain tool per field

### Agent Execution Loop

**Not this (request/response):**
```
User: "Fix the data"
→ Agent: "What should I fix?"
→ User: "The experience fields"
→ Agent: "How should I fix them?"
[endless back-and-forth]
```

**This (outcome-driven loop):**
```
User: "Fix the experience data quality issues"

Agent loop:
1. Analyze current state
2. Detect issue: 43 LinkedIn URLs without experience  
3. Assess options: re-scrape, clear, flag for review
4. Propose: "Clear empty experience fields to prepare for re-enrichment"
5. User confirms: "run"
6. Execute: clear_field(experience_text)
7. Validate: Check result
8. Complete: Report outcome
```

**Completion Signals:**

Explicit, not heuristic:

```python
# WRONG - heuristic detection
if no_tool_calls_for_3_iterations:
    assume_complete = True

# RIGHT - explicit signal  
return AgentResult(
    success=True,
    output="Cleared 43 empty experience fields",
    shouldContinue=False  # ← Explicit completion
)
```

### Approval & User Agency

**Stakes vs Reversibility Matrix:**

| Stakes | Reversibility | Pattern | Example |
|--------|--------------|---------|---------|
| Low | Easy | Auto-apply | Analyze field statistics |
| Low | Hard | Quick confirm | Clear non-critical field |
| High | Easy | Suggest + apply | Modify data (checkpointed) |
| High | Hard | Explicit approval | Delete run, trigger evaluation |

**Our chatbot currently:**
- ✅ Propose → confirm pattern (good!)
- ❌ No distinction between safe/destructive (improve)
- ❌ No dry-run preview (add this)

**Agent-native approach:**

```python
# Safe operation - auto-execute
analyze_field("email")
→ Executes immediately, shows results

# Risky operation - preview + confirm
clear_field("experience_text", dry_run=True)
→ "This will clear 127 values. Preview (first 5):"
→ User confirms: "run"
→ clear_field("experience_text", dry_run=False)

# Destructive - multiple confirms
delete_run(run_id)
→ "⚠️ This will permanently delete run and all data."
→ "Type run ID to confirm: _____"
```

---

## Roadmap: Transforming the Data Assistant

### Current State Assessment

**What we have:**
- Basic chat interface
- Single `execute_python` tool
- Propose → confirm workflow
- Regex fallback for simple intents

**Violations of agent-native principles:**

| Principle | Current State | Gap |
|-----------|--------------|-----|
| Parity | Agent can't trigger workflows, export data | Missing 60% of UI capabilities |
| Granularity | Monolithic execute_python tool | Anti-pattern: bundled judgment |
| Composability | Every feature requires code | Can't add features via prompts |
| Emergent | Can only do exactly what we coded | Zero unexpected capability |
| Improvement | No context, no learning | Starts fresh every session |

**Agent-Native Transformation Score: 15/100**

---

### Phase 1: Atomic Tools (Week 1-2)
**Goal:** Replace monolithic tool with composable primitives

**Actions:**
1. **Break execute_python into atomic operations:**
   ```python
   # Data Quality Tools
   - analyze_field(field_name, include_examples)
   - validate_field(field_name, validation_type)  
   - detect_duplicates(match_fields)
   - find_candidates(criteria, limit)
   
   # Data Modification Tools
   - clear_field(field_name, dry_run)
   - copy_field(source, target, overwrite)
   - fill_field(field_name, value, condition)
   
   # Workflow Tools
   - trigger_standardization(run_id)
   - trigger_evaluation(run_id)
   - export_data(format, filters)
   ```

2. **Add domain knowledge:**
   - Create `webapp/chatbot_knowledge.py` (field glossary, patterns)
   - Create `webapp/chatbot_context.py` (context builder)
   - Upgrade system prompt with recruiting domain expertise

3. **Implement dry-run pattern:**
   - All destructive operations show preview
   - Explicit confirmation required
   - Show before/after for first 5 rows

**Success Criteria:**
- ✅ User can ask "what's wrong with this data?" → Agent analyzes
- ✅ User can describe outcome → Agent composes tools
- ✅ Behavior changes via prompt edits, not code refactors

**Agent-Native Score After Phase 1: 45/100**

---

### Phase 2: Context & Memory (Week 3)
**Goal:** Agent accumulates knowledge and improves over time

**Actions:**
1. **Implement context files:**
   ```
   /runs/{run_id}/
   ├── agent_context.md      # Working memory
   ├── agent_log.md         # Action history  
   ├── memory.json          # Learned preferences
   └── analysis/
       ├── quality_report.md
       └── recommendations.md
   ```

2. **Agent reads/updates context:**
   - Load `agent_context.md` at session start
   - Update after each operation
   - Log successful patterns to memory

3. **Learning from operations:**
   ```json
   {
     "successful_patterns": [
       {
         "user_intent": "clear experience before enrichment",
         "tools_used": ["clear_field", "clear_field"],
         "frequency": 8,
         "typical_sequence": ["experience_text", "current_company"]
       }
     ],
     "user_preferences": {
       "explanation_style": "concise",
       "auto_apply_threshold": "safe_only"
     }
   }
   ```

4. **Context injection in prompts:**
   - Include recent activity
   - Include learned preferences
   - Include available resources
   - Include common patterns for this role

**Success Criteria:**
- ✅ Agent remembers user preferences within run
- ✅ Agent knows what files exist and what's been done
- ✅ Repeat users get faster, smarter assistance

**Agent-Native Score After Phase 2: 65/100**

---

### Phase 3: Agent Loop & Parity (Week 4)
**Goal:** Agent pursues outcomes with full UI parity

**Actions:**
1. **Implement agent loop:**
   ```
   1. Classify intent (analyze | modify | workflow)
   2. Plan (decompose into steps)
   3. Execute (use tools, handle errors)
   4. Reflect (did it work? what next?)
   5. Respond (outcome + next steps)
   ```

2. **Add workflow tools (achieve parity):**
   ```python
   - trigger_standardization(run_id)
   - trigger_evaluation(run_id)  
   - export_data(run_id, format, filters)
   - update_run_state(run_id, state)
   - delete_run(run_id, confirm_id)
   ```

3. **Multi-step operations:**
   ```
   User: "Clean the data and start evaluation"
   
   Agent:
   1. analyze_field("experience_text")
   2. Detect 43 empty despite LinkedIn
   3. clear_field("experience_text", dry_run=True)
   4. Preview → User confirms
   5. clear_field("experience_text")
   6. trigger_evaluation(run_id)
   7. Report: "Evaluation started with cleaned data"
   ```

4. **Error recovery:**
   - If tool fails, agent adjusts approach
   - Proposes alternative strategies
   - Doesn't just give up

**Success Criteria:**
- ✅ Agent can accomplish any UI workflow
- ✅ Agent handles multi-step requests
- ✅ Agent recovers gracefully from failures

**Agent-Native Score After Phase 3: 85/100**

---

### Phase 4: Emergent Capability (Week 5-6)
**Goal:** Agent can do things we didn't explicitly design

**Actions:**
1. **Dynamic capability discovery:**
   ```python
   - list_available_fields(run_id)
   - get_field_metadata(field_name)  
   - analyze_field(field_name, analysis_type)
   # Works with ANY field, even ones added later
   ```

2. **Cross-run analysis:**
   ```
   User: "Compare quality of this batch vs last week's batches"
   
   Agent:
   1. list_runs(filters={"created_after": "2026-01-18"})
   2. For each: analyze_quality()
   3. Compare metrics: missing_data_rate, duplicate_rate
   4. Generate comparative report
   ```

3. **Composable features:**
   ```
   User: "Create a weekly quality report"
   
   → Add to prompts (no code):
   "Every Monday, analyze past week's runs.
   Report: common issues, success rates, patterns.
   Save to reports/weekly-{date}.md"
   ```

4. **Observe latent demand:**
   - Log all user requests
   - Track which succeed/fail
   - Identify emerging patterns
   - Optimize common patterns with domain tools

**Success Criteria:**
- ✅ Users can request things we didn't build
- ✅ Agent figures out how to accomplish them
- ✅ We discover features by observing requests

**Agent-Native Score After Phase 4: 95/100**

---

## Architecture Decisions

### Files vs Database

**Use files for:**
- ✅ Agent context and working memory
- ✅ Quality reports and analysis
- ✅ Action logs and history
- ✅ Configuration and preferences
- ✅ Exported reports

**Use database for:**
- ✅ Run metadata (searchable, queryable)
- ✅ Candidate data (structured, indexed)
- ✅ Session state (ephemeral)
- ✅ Chat messages (high volume)

**Hybrid approach:**
```
/runs/{run_id}/
├── agent_context.md     ← File (agent reads/writes)
├── quality_report.md    ← File (human readable)
└── analysis/            ← Files (inspectable)

Database:
- runs table (metadata, state, timestamps)
- messages table (chat history)
- candidates table (structured data)
```

**Why this works:**
- Agent can reason about files naturally
- Users can inspect/edit agent work
- Database handles queries/filters efficiently
- Best of both worlds

### Tool Registry Pattern

```python
# tools/registry.py

AGENT_TOOLS = {
    "data_quality": [
        analyze_field,
        validate_field,
        detect_duplicates,
        find_candidates
    ],
    "data_modification": [
        clear_field,
        copy_field,
        fill_field
    ],
    "workflow": [
        trigger_standardization,
        trigger_evaluation,
        export_data
    ],
    "file_operations": [
        read_file,
        write_file,
        list_files
    ]
}

def get_tools_for_agent(agent_type: str) -> List[Tool]:
    """Get appropriate tool subset for agent type"""
    if agent_type == "data_assistant":
        return AGENT_TOOLS["data_quality"] + AGENT_TOOLS["data_modification"]
    elif agent_type == "workflow_assistant":
        return AGENT_TOOLS["workflow"] + AGENT_TOOLS["file_operations"]
```

**Benefits:**
- Clear tool organization
- Easy to add new tools
- Different agents get different tool subsets
- Tools are composable, not siloed

---

## Success Metrics

### Technical Metrics

**Parity Score:**
- % of UI actions achievable via agent tools
- Target: 95%+

**Composability Score:**
- # of features added via prompts (not code)
- Target: 80% of new features via prompts

**Emergent Capability Rate:**
- # of successful requests for things we didn't build
- Target: 30%+ of requests

### User Metrics

**Task Success Rate:**
- % of user intents successfully completed
- Current: ~35%
- Target: 85%+

**Clarification Efficiency:**
- Avg # of back-and-forth messages to complete task
- Target: ≤ 2 rounds

**Tool Accuracy:**
- % of correct tool selections
- Target: 90%+

### Product Metrics

**Latent Demand Discovery:**
- Track: What users ask for that we didn't build
- Use: Prioritize feature development

**Agent Utilization:**
- % of runs that use chatbot
- % of data modifications done via agent vs manual
- Target: 60%+ of data prep uses agent

---

## Anti-Pattern Checklist

Before shipping any agent feature, verify:

- [ ] **Not request/response only** - Agent operates in loop until outcome achieved
- [ ] **Not workflow executor** - Agent makes decisions, not just calling our workflow
- [ ] **Not orphaned UI actions** - Everything in UI is achievable by agent
- [ ] **Not bundled judgment** - Tools are atomic, prompts describe outcomes
- [ ] **Not context-starved** - Agent knows what exists, what's been done
- [ ] **Not artificially limited** - Agent can do what users can do
- [ ] **Not heuristic completion** - Explicit completion signals
- [ ] **Not static when dynamic would serve** - Can discover new capabilities

---

## Next Steps

**Immediate (This Weekend):**
1. Review compound engineering GitHub repo (link needed)
2. Codify agent-native principles into `ARCHITECTURE.md`
3. Update `chatbot-improvement-plan.md` with agent-native framing
4. Create `ROADMAP.md` with phased approach

**Week 1:**
1. Implement atomic tools (replace execute_python)
2. Build chatbot_knowledge.py (domain expertise)
3. Upgrade system prompts
4. Add dry-run previews

**Week 2:**
1. Implement context files pattern
2. Add agent_context.md to runs
3. Create memory/learning system
4. Test composability (can we add features via prompts?)

**Ongoing:**
1. Track user requests (latent demand)
2. Measure success metrics
3. Observe emergent capability
4. Iterate based on what users actually ask for

---

## Questions for Further Discussion

1. **Compound engineering repo** - Need link to review and incorporate
2. **Self-modification** - Should agent be able to update its own prompts?
3. **Approval gates** - What's the right balance for our use case?
4. **Mobile considerations** - Do we need mobile access? (Checkpointing, etc.)
5. **Multi-agent coordination** - Should we have specialized agents for different tasks?

---

*This document is a living guide. As we build and learn, we'll update these principles based on what actually works.*
