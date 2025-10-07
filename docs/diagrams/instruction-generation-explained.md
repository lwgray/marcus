# How Agent Instructions Are Generated

## You're Right - They ARE Templated!

Both the AI-generated and fallback instructions use templates, just in different ways.

---

## The Two Paths

### Path 1: AI Available (Line 491)

**File:** `src/integrations/ai_analysis_engine.py:486-492`

```python
prompt = self.prompts["task_instructions"].format(
    task=json.dumps(task_data, indent=2),
    agent=json.dumps(agent_data, indent=2)
)

instructions = await self._call_claude(prompt)
```

**AI Prompt Template (Line 148-181):**
```
You are generating detailed task instructions for a developer.

Task: {task}
Assigned to: {agent}

IMPORTANT: Look at the task data to determine the task type (check the 'type' field).
Generate instructions appropriate for the task type:

For DESIGN tasks:
- Focus on planning, architecture, and specifications
- Include creating diagrams, API specs, data models
- NO implementation code yet
- Deliverables: design documents, wireframes, API contracts

For IMPLEMENTATION tasks:
- Focus on actual coding and building
- Reference the design specifications
- Include specific code components to build
- Deliverables: working code with tests

For TESTING tasks:
- Focus on test scenarios and coverage
- Include unit, integration, and edge cases
- Deliverables: test suites with good coverage

Generate clear, actionable instructions that:
1. Define the task objective based on its type
2. List specific steps appropriate for the task type
3. Include acceptance criteria
4. Note any dependencies or prerequisites
```

✅ **AI has FREEDOM within the template constraints**
- Can customize steps based on task description
- Can be creative about approach
- Can use task-specific terminology

❌ **But still GUIDED by template structure**
- Must follow Design/Implement/Test pattern
- Must include deliverables
- Must be "appropriate for task type"

### Path 2: Fallback (No AI) (Line 497-576)

**File:** `src/integrations/ai_analysis_engine.py:527-568`

```python
if task_type == "design":
    implementation_steps = """2. **Design Steps**
   - Research existing patterns and best practices
   - Create architecture diagrams
   - Define API endpoints and data models
   - Document component interfaces
   - Create wireframes or mockups if needed"""

    definition_of_done = """3. **Definition of Done**
   - Design documentation is complete
   - API specifications are defined
   - Data models are documented
   - Technical approach is clear"""
```

❌ **HARDCODED template - same for every design task**
- "Research existing patterns" - generic
- "Create architecture diagrams" - generic
- "Define API endpoints" - generic
- Does NOT use task description in steps

---

## What Agent Receives

### Fallback Template Output

```markdown
## Task Assignment for Team Member

**Task:** Design User Authentication

**Description:** Users must be able to register, log in, and log out of the application.

**Priority:** high
**Estimated Hours:** 8
**Type:** Design

### Instructions:

1. **Review Requirements**
   - Read the task description carefully
   - Check any linked documentation
   - Identify dependencies: None

2. **Design Steps**                                    ← GENERIC
   - Research existing patterns and best practices     ← GENERIC
   - Create architecture diagrams                      ← GENERIC
   - Define API endpoints and data models              ← GENERIC
   - Document component interfaces                     ← GENERIC
   - Create wireframes or mockups if needed            ← GENERIC

3. **Definition of Done**                              ← GENERIC
   - Design documentation is complete                  ← GENERIC
   - API specifications are defined                    ← GENERIC
   - Data models are documented                        ← GENERIC
   - Technical approach is clear                       ← GENERIC
```

**Problem:**
- Description says "register, log in, log out"
- But steps don't mention registration, login, or logout specifically
- Agent must INFER from description what to actually design

### AI-Generated Output (When AI Available)

**AI receives:**
```json
{
  "name": "Design User Authentication",
  "description": "Users must be able to register, log in, and log out of the application.",
  "type": "design"
}
```

**AI template guides it to generate:**
```markdown
## Task: Design User Authentication

### Objective
Design the authentication system allowing users to register, log in, and log out.

### Design Steps
1. **Registration Flow**
   - Design user registration form (email, password)
   - Plan email verification process
   - Document password requirements

2. **Login Flow**
   - Design login interface
   - Plan session management approach
   - Define JWT token strategy

3. **Logout Flow**
   - Design logout mechanism
   - Plan token invalidation
   - Document session cleanup

### Deliverables
- Authentication flow diagrams
- API endpoint specifications:
  - POST /api/register
  - POST /api/login
  - POST /api/logout
- Security documentation
- Data models (User, Session)

### Definition of Done
- All flows are documented
- API contracts are defined
- Security approach is clear
```

✅ **BETTER - Uses task description**
- Mentions "register, log in, log out" specifically
- Creates concrete steps for each
- Still follows Design methodology

❌ **Still templated structure**
- Follows "Design Steps" → "Deliverables" → "Definition of Done" pattern
- Always mentions diagrams, API specs, documentation

---

## The Template Layers

### Layer 1: Task Type (Design/Implement/Test)
**Determined by:** Task name or labels (line 465-468)

```python
if "design" in task.name.lower() or "type:design" in task_labels:
    task_type = "design"
elif "test" in task.name.lower() or "type:testing" in task_labels:
    task_type = "testing"
else:
    task_type = "implementation"
```

### Layer 2: AI Prompt Template
**Location:** Line 148-181

Tells AI:
- "For DESIGN tasks: Focus on planning, architecture..."
- "For IMPLEMENTATION tasks: Focus on actual coding..."
- "For TESTING tasks: Focus on test scenarios..."

### Layer 3: AI Freedom (if AI available)
**Location:** Line 491

AI can be creative WITHIN the template constraints:
- Use task description to generate specific steps
- Create concrete deliverables
- Customize to project type

### Layer 4: Hardcoded Fallback (if AI unavailable)
**Location:** Line 527-568

Completely generic:
- Same steps for every design task
- Same steps for every implementation task
- Same steps for every testing task

---

## Comparison

### Fallback Template (No AI)

**For "Design User Authentication":**
```
2. Design Steps:
   - Research existing patterns    ← Generic, not about auth
   - Create architecture diagrams  ← Generic, not about login/logout
   - Define API endpoints          ← Generic, not specific endpoints
```

**For "Design Todo CRUD":**
```
2. Design Steps:
   - Research existing patterns    ← SAME
   - Create architecture diagrams  ← SAME
   - Define API endpoints          ← SAME
```

**For "Design Filtering":**
```
2. Design Steps:
   - Research existing patterns    ← SAME
   - Create architecture diagrams  ← SAME
   - Define API endpoints          ← SAME
```

❌ **Identical for ALL design tasks!**

### AI-Generated (With AI)

**For "Design User Authentication":**
```
- Design registration form with email/password
- Plan JWT token strategy
- Define /register, /login, /logout endpoints
```

**For "Design Todo CRUD":**
```
- Design todo creation form
- Plan data model for todos
- Define /todos GET/POST/PUT/DELETE endpoints
```

**For "Design Filtering":**
```
- Design filter UI controls
- Plan query parameter strategy
- Define /todos?status=active endpoint
```

✅ **Customized per task!**

---

## Why Templates Exist

### Good Reasons:

1. **Consistency** - All design tasks follow same methodology
2. **Completeness** - Ensures nothing is forgotten (diagrams, specs, docs)
3. **Quality** - Enforces best practices (80% coverage, code review)
4. **Coordination** - Design → Implement → Test flow is clear

### The Problem:

Templates are applied at TWO levels:
1. **Task descriptions** - Makes them generic and noisy
2. **Agent instructions** - Makes them repetitive

**Better approach:**
- Task descriptions: Pure AI, no templates
- Agent instructions: AI-guided templates (current AI path)

---

## Your Methodology Requirement

You want to keep "Design, Implement, Test" methodology. Good news:

### This Is Already Enforced!

**Location 1:** Task naming (advanced_parser.py:1030-1059)
```python
if "design" in task_id.lower():
    name, description = self._generate_design_task(...)
elif "implement" in task_id.lower():
    name, description = self._generate_implementation_task(...)
elif "test" in task_id.lower():
    name, description = self._generate_testing_task(...)
```

**Location 2:** Task type detection (ai_analysis_engine.py:465-468)
```python
if "design" in task.name.lower() or "type:design" in task_labels:
    task_type = "design"
```

**Location 3:** AI prompt template (ai_analysis_engine.py:157-172)
```
For DESIGN tasks:
- Focus on planning, architecture, and specifications
...

For IMPLEMENTATION tasks:
- Focus on actual coding and building
...

For TESTING tasks:
- Focus on test scenarios and coverage
...
```

**The methodology is PRESERVED in:**
1. ✅ Task names ("Design X", "Implement X", "Test X")
2. ✅ Task labels ("type:design", "type:implementation", "type:testing")
3. ✅ Instruction generation (AI knows task type)

**Can be REMOVED from:**
- ❌ Task descriptions (don't need template boilerplate)

---

## Proposed Solution

### Keep Methodology, Remove Noise

**Task Description (Clean):**
```
Users must be able to register, log in, and log out of the application.
```

**Task Name (Methodology):**
```
Design User Authentication
```

**Task Labels (Methodology):**
```
["type:design", "phase:design", "feature:user-auth"]
```

**Agent Instructions (Methodology + AI):**
```
## Design Task: User Authentication

### What to Build
Users must be able to register, log in, and log out of the application.

### Design Approach (Marcus Methodology)
As a DESIGN task, you should:
1. Create authentication flow diagrams for:
   - User registration process
   - Login flow with credential validation
   - Logout and session cleanup

2. Define API specifications:
   - POST /api/register (email, password) → user token
   - POST /api/login (email, password) → session token
   - POST /api/logout (token) → success response

3. Document security approach:
   - Password hashing strategy
   - Session/token management
   - Token expiration policies

### Deliverables (Design Phase)
- [ ] Authentication flow diagrams
- [ ] API endpoint specifications
- [ ] Security documentation
- [ ] User data model definition

### Next Phase
After design is complete and approved, this will move to:
→ Implement User Authentication (uses your API specs)
→ Test User Authentication (validates your requirements)
```

**Result:**
- ✅ Description is clean, AI-generated, prominent
- ✅ Methodology preserved in name, labels, instructions
- ✅ Instructions are AI-customized for this specific task
- ✅ Design → Implement → Test flow is clear
- ✅ No template noise in description

---

## Summary

### Current State:
- **Task descriptions:** 80% template, 20% AI content
- **Instructions:** AI-guided by templates (good!) OR hardcoded templates (bad)

### Your Concern:
"Instructions look templated" - **You're absolutely right!**

### The Fix:
1. **Remove templates from task descriptions** - Let AI descriptions shine
2. **Keep AI-guided templates in instructions** - Preserve methodology
3. **Enhance AI prompt** - Make it more task-specific

### Methodology Preserved By:
- Task naming convention ("Design", "Implement", "Test")
- Task labels ("type:design", etc.)
- AI instruction prompt (guides AI to follow methodology)
- Phase enforcement in Marcus coordination

You can have BOTH:
- ✅ Clean, AI-generated task descriptions
- ✅ Structured Design/Implement/Test methodology
