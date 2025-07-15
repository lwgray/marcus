# 📋 Marcus Todo App Demo

Demo project showing Marcus coordinating AI agents to build a complete todo application.

## 🚀 **Quick Start**

### **Automated Setup (Recommended)**
```bash
# From marcus root directory
python setup_marcus_demo.py
```

This automatically:
- ✅ Creates "Marcus Todo Demo" project in Planka
- ✅ Creates todo app board with proper lists
- ✅ Updates config_marcus.json with correct IDs
- ✅ Creates 17 development tasks ready for AI agents
- ✅ Provides final setup instructions

### **Manual Setup Scripts**
If you prefer manual control or want specific card sets:

```bash
# Minimal cards (17 essential tasks)
python create_minimal_todo_cards.py

# Moderate cards (more detail)
python create_moderate_todo_cards.py

# Full cards (complete specifications)
python create_all_todo_app_cards.py

# Interactive menu
python create_todo_cards_menu.py

# Clear all cards
python clear_board.py
```

---

## 📁 **Files Overview**

### **Setup Scripts**
- `setup_demo_project.py` - **Main setup script** (creates project, board, config, cards)
- `create_minimal_todo_cards.py` - Create 17 essential tasks
- `create_moderate_todo_cards.py` - More detailed task specifications
- `create_all_todo_app_cards.py` - Full detailed tasks with subtasks
- `create_todo_cards_menu.py` - Interactive menu for card creation
- `clear_board.py` - Remove all cards from board

### **Configuration**
- `todo_app_planka_cards.json` - Complete task definitions and specifications
- `docs/` - Additional documentation for the todo app project

---

## 🎯 **What This Demo Shows**

### **AI Agent Coordination**
Watch multiple AI agents automatically:
- **Pick up tasks** from the Backlog column
- **Report progress** as they work (25%, 50%, 75%, 100%)
- **Share context** between dependent tasks
- **Move cards** through workflow: Backlog → TODO → In Progress → Review → Done
- **Handle blockers** with AI-powered suggestions

### **Todo App Development**
The demo builds a complete todo application:

**Backend Tasks:**
- Project setup and database design
- Todo model with CRUD operations
- REST API endpoints with validation
- User authentication with JWT
- Error handling and testing

**Frontend Tasks:**
- React app structure with TypeScript
- Todo list and item components
- Add/edit forms with validation
- API integration and state management
- UI/UX design and responsiveness

**DevOps Tasks:**
- Testing framework setup
- Deployment configuration
- Performance optimization

---

## 🔍 **Monitoring the Demo**

### **Planka Board**
Visit [http://localhost:3333](http://localhost:3333) to watch:
- Cards moving between columns
- Agent comments and progress updates
- Task completions and context sharing

### **Expected Workflow**
1. **Agent registers** with Marcus
2. **Requests first task** (e.g., "Set up project structure")
3. **Works autonomously** on the task
4. **Reports progress** at milestones
5. **Completes task** and moves card to Done
6. **Immediately requests next task**
7. **Continues** until all 17 tasks are complete

### **Context Sharing Example**
When Agent A completes "Create User model", Agent B automatically knows:
- What database schema was created
- What API endpoints exist
- How authentication works
- Integration patterns to follow

---

## 🎬 **Demo Scenarios**

### **5-Minute Quick Demo**
```bash
python setup_marcus_demo.py
# Follow instructions, start one agent in Claude Code
# Watch 2-3 tasks get completed automatically
```

### **Full Development Simulation**
```bash
# Create all 17 tasks
python create_all_todo_app_cards.py

# Start multiple Claude Code instances with different agent IDs
# Watch full todo app get built by coordinated agents
```

### **Custom Project Demo**
```bash
# In Marcus (via Claude Code)
# Use create_project tool to generate your own project
# Watch agents build whatever you specify
```

---

## 🛠️ **Customization**

### **Modify Tasks**
Edit `todo_app_planka_cards.json` to:
- Change task descriptions
- Add/remove tasks
- Modify priorities and labels
- Update due dates

### **Different Project Types**
The same coordination works for any project:
- Web applications
- CLI tools
- Data pipelines
- Mobile apps
- AI/ML projects

### **Multiple Agents**
Run multiple Claude Code instances with different:
- Agent names (Frontend Developer, Backend Developer, etc.)
- Skill sets (React, Python, DevOps, etc.)
- Specializations (Security, Performance, Testing, etc.)

---

## 📊 **Success Metrics**

A successful demo shows:
- ✅ **Autonomous task completion** - Agents work without human intervention
- ✅ **Context sharing** - Later agents use earlier agents' work
- ✅ **Intelligent assignment** - Tasks go to appropriate agent types
- ✅ **Error recovery** - Agents overcome blockers with AI suggestions
- ✅ **Continuous progress** - No idle time between tasks

---

## 🔧 **Troubleshooting**

### **"No tasks available"**
```bash
# Recreate tasks
python setup_demo_project.py
```

### **"Task not found" errors**
```bash
# Clear and recreate
python clear_board.py
python create_minimal_todo_cards.py
```

### **Cards not moving**
- Check agent is registered with Marcus
- Verify config_marcus.json has correct board_id
- Ensure Planka connection is working

### **No progress updates**
- Verify agent is using Marcus MCP tools
- Check prompts/Agent_prompt.md is being used
- Ensure agent follows continuous work loop

---

## 💡 **Next Steps**

After the demo:
1. **Build your own project** using `create_project` MCP tool
2. **Experiment with agent specialization**
3. **Try different AI providers** (add OpenAI, local models)
4. **Extend Marcus** with custom MCP tools
5. **Integrate with GitHub Projects** or Linear

---

*This demo showcases Marcus's core value: AI agents that work together autonomously, share context intelligently, and build complete applications without human micromanagement.*
