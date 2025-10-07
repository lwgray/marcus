# Test Results: Detail Preservation in Task Descriptions

## Test Setup

**Detailed User Input:**
```
Build a todo application with specific features:

1. Authentication: JWT tokens with 24-hour expiration, email verification,
   remember me checkbox
2. Todo CRUD: Title, description, due date, priority (low/medium/high),
   archive after 30 days
3. UI: Dark mode toggle, drag-and-drop reordering, keyboard shortcuts
   (Ctrl+N for new todo)
```

---

## Results

### Details Preserved: 7/10 (70%)

✅ **PRESERVED:**
- JWT tokens
- 24-hour expiration
- Email verification
- Remember me checkbox
- Dark mode toggle
- Drag-and-drop reordering
- Keyboard shortcuts (general)

❌ **LOST:**
- Priority levels (low/medium/high)
- Archive after 30 days
- Specific shortcuts (Ctrl+N)

---

## Where Details End Up

### Example: "Implement User Authentication" Task

**Full Description:**
```
Develop responsive UI components for frontend application. Create reusable
component library, implement state management, handle user interactions, and
ensure accessibility compliance. Using: Use modern web technologies (e.g.,
React, Node.js), Ensure cross-browser compatibility, Support multiple devices
and screen sizes. Include loading states, error boundaries, and responsive
design.

Addresses requirement: Implement JWT token-based authentication with 24-hour
expiration, email verification, and remember m...
```

### Structure:

```
[80% Generic Template]
Develop responsive UI components for frontend application...
Create reusable component library...
implement state management...
handle user interactions...
ensure accessibility compliance...
Using: modern web technologies...
cross-browser compatibility...
multiple devices and screen sizes...
loading states...
error boundaries...
responsive design...

[20% Your Specific Details - TRUNCATED]
Addresses requirement: JWT token-based authentication with 24-hour
expiration, email verification, and remember m...
                                                          ^^^^ CUT OFF!
```

---

## The Problem Visualized

### Ratio Analysis

For a typical task description:

```
Total Length: ~500 characters

Template boilerplate:     400 chars (80%)
├─ "Develop responsive UI components"
├─ "Create reusable component library"
├─ "implement state management"
├─ "handle user interactions"
├─ "ensure accessibility compliance"
├─ "Using: modern web technologies"
├─ "cross-browser compatibility"
└─ "Include loading states, error boundaries..."

Your specific details:   100 chars (20%)
└─ "JWT token-based authentication with 24-hour
    expiration, email verification, remember m..."
                                               ^^^^ TRUNCATED
```

---

## What Users See in Planka

When you open a task in Planka, you see:

### First 200 Characters (What's Visible):
```
Develop responsive UI components for frontend application. Create reusable
component library, implement state management, handle user interactions, and
ensure accessibility compliance...
```

**Your details:** Buried 400+ characters in, possibly truncated

---

## Detailed Test: All Tasks

### Test Input:
```
Very detailed description with:
- JWT token-based authentication with 24-hour expiration
- Email/password registration with email verification
- Login with remember me functionality
- Password reset via email
- Refresh tokens stored securely
- Create todos with title, description, due date, priority (low/medium/high)
- Edit any field of existing todos
- Delete todos with confirmation dialog
- Mark todos as complete/incomplete with timestamp tracking
- Archive completed todos older than 30 days
- Filter by status: all, active, completed, archived
- Search todos by title or description text
- Sort by due date, priority, or creation date
- Organize todos into user-defined categories
- Add multiple tags to each todo
- Color-code categories
- Responsive design for mobile, tablet, and desktop
- Dark mode toggle with user preference saved
- Drag-and-drop to reorder todos
- Keyboard shortcuts for common actions
```

### Results: 11 Tasks Created

**Tasks with specific details:** 3/11 (27%)
**Tasks with only generic templates:** 8/11 (73%)

### Detail Breakdown

| Detail | Found in Tasks | Status |
|--------|---------------|--------|
| JWT tokens | 5 tasks | ✅ Preserved |
| 24-hour expiration | 5 tasks | ✅ Preserved |
| Email verification | 5 tasks | ✅ Preserved |
| Remember me | 4 tasks | ✅ Preserved |
| Refresh tokens | 2 tasks | ✅ Preserved |
| Priority levels (low/medium/high) | 0 tasks | ❌ Lost |
| Archive after 30 days | 0 tasks | ❌ Lost |
| Confirmation dialog | 0 tasks | ❌ Lost |
| Timestamp tracking | 0 tasks | ❌ Lost |
| Dark mode | 3 tasks | ✅ Preserved |
| Drag-and-drop | 3 tasks | ✅ Preserved |
| Keyboard shortcuts | 3 tasks | ✅ Preserved |
| Specific shortcuts (Ctrl+N) | 0 tasks | ❌ Lost |
| Categories | 0 tasks | ❌ Lost |
| Tags | 0 tasks | ❌ Lost |
| Color-code | 0 tasks | ❌ Lost |

**Preservation Rate:** ~40% of specific details

---

## Why Some Details Are Lost

### 1. AI Groups Details by Feature

Your detailed list gets analyzed and **grouped** into functional requirements:

**Input Details:**
```
- JWT with 24-hour expiration
- Email verification
- Remember me
- Refresh tokens
- Password reset
```

**AI Groups As:**
```
Functional Requirement: "User Authentication"
Description: "Implement email/password registration with email verification,
login with remember me, password reset, JWT tokens with 24-hour expiration,
and secure refresh token storage."
```

### 2. Templates Use First Requirement

When creating "Design User Authentication" task:
- Template sees: "User Authentication" requirement
- Adds: First 100 characters of requirement description
- **Truncates** the rest

**Result:**
```
Template: "Design authentication architecture..."
+
Requirement snippet: "Implement email/password registration with email
verification, login with remember m..."
                                                   ^^^^ Cut off
```

### 3. Some Requirements Get Generic Labels

**Input:**
```
- Filter by status: all, active, completed, archived
- Sort by due date, priority, creation date
```

**AI Analysis:**
```
Requirement: "Filtering and Search"
Description: "Allow users to filter todos by status..."
```

**Template:**
```
"Create UI components for frontend application..."
+ "Addresses requirement: Allow users to filter todos by status..."
```

But **not** which specific statuses (all, active, completed, archived)

---

## Comparison: Short vs Detailed Input

### Short Input
```
Input: "Build a todo app with authentication"
AI Analysis: Expands to ~100 words
Templates: Add ~400 words
Your Details: 20% of final description
```

### Detailed Input
```
Input: "Build todo app with JWT 24-hour tokens, email verification,
        dark mode, drag-and-drop, archive after 30 days..."
AI Analysis: Extracts ~150 words
Templates: Still add ~400 words
Your Details: 30% of final description (better, but still buried)
```

---

## Conclusion

### What Gets Preserved?

✅ **High-level features** (JWT, email verification, dark mode)
✅ **Technical terms** (tokens, authentication, expiration)
✅ **Major concepts** (drag-and-drop, keyboard shortcuts)

### What Gets Lost?

❌ **Specific values** (24-hour → lost in truncation)
❌ **Business rules** (archive after 30 days → not in description)
❌ **Detailed specs** (low/medium/high priorities → generic "priority")
❌ **User flows** (confirmation dialog → missing)
❌ **Specific shortcuts** (Ctrl+N → generic "keyboard shortcuts")

---

## Recommendation

Based on testing, **even detailed descriptions lose 60% of specifics** to:
1. Template boilerplate (80% of description)
2. Truncation of AI requirement text
3. Grouping/summarization in AI analysis

**Solution:** Don't fight the templates in descriptions. Instead:

1. **Use AI descriptions directly** (no templates in task.description)
2. **Move templates to agent instructions** (where they add value)
3. **Let details be visible** (not buried after 400 chars of boilerplate)

**Result:**
```
Current:  [Template: 400 chars] + [Details: 100 chars, truncated]
Proposed: [Details: 100 chars, prominent] + [Instructions add structure]
```

User sees details FIRST, not buried after generic boilerplate.
