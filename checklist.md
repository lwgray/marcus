# Marcus Development Checklist

## 🔴 Critical Issues

- [ ] [get_task_context MCP tool exceeds token limit (2.3M tokens)](https://github.com/lwgray/marcus/issues/59) (#59) - Tool returns responses exceeding 25K token limit, blocking agents from accessing task context

## 🐛 Known Bugs

- [ ] [Task execution order not respecting dependencies](https://github.com/lwgray/marcus/issues/7) (#7) - Tests assigned before Implementation
- [ ] [KanbanInterface.update_task() None returns not handled](https://github.com/lwgray/marcus/issues/50) (#50) - Potential for silent failures
- [ ] [Improve Planka Board Handling in Multi-Project Mode](https://github.com/lwgray/marcus/issues/11) (#11)

## 🚀 Enhancements In Progress

- [ ] [Implement hybrid artifact filtering](https://github.com/lwgray/marcus/issues/40) (#40) - Optimize context retrieval
- [ ] [Remove template boilerplate from task descriptions](https://github.com/lwgray/marcus/issues/57) (#57)
- [ ] [Artifact discovery needs session/project isolation](https://github.com/lwgray/marcus/issues/39) (#39)

## ✅ Testing & Quality

- [ ] [All Tests Must Pass - 80% Coverage Target](https://github.com/lwgray/marcus/issues/44) (#44)
- [ ] [Comprehensive Test Coverage Analysis](https://github.com/lwgray/marcus/issues/54) (#54)
- [ ] [Implement tests for 14 new test directories](https://github.com/lwgray/marcus/issues/53) (#53)
- [ ] [Improve test organization](https://github.com/lwgray/marcus/issues/46) (#46)
- [ ] [Implement Comprehensive Testing Strategy](https://github.com/lwgray/marcus/issues/23) (#23)

## 📚 Documentation

- [ ] [Document MCP Integration for Various Platforms](https://github.com/lwgray/marcus/issues/26) (#26)
- [ ] [Reorganize and Complete Documentation](https://github.com/lwgray/marcus/issues/24) (#24)

## 🔧 Refactoring

- [ ] [Refactor handlers.py: Implement tool registry pattern](https://github.com/lwgray/marcus/issues/15) (#15)
- [ ] [Refactor server.py: Split monolith into modular architecture](https://github.com/lwgray/marcus/issues/12) (#12)
- [ ] [Refactor ai_analysis_engine.py: Separate providers](https://github.com/lwgray/marcus/issues/16) (#16)
- [ ] [Refactor advanced_parser.py: Decompose parser monolith](https://github.com/lwgray/marcus/issues/13) (#13)
- [ ] [Create Comprehensive Refactoring Documentation](https://github.com/lwgray/marcus/issues/17) (#17)

## 🎯 Future Features

- [ ] [Make GitHub Projects the Default Kanban Provider](https://github.com/lwgray/marcus/issues/28) (#28)
- [ ] [Complete Seneca Integration](https://github.com/lwgray/marcus/issues/31) (#31)
- [ ] [Build Epictetus Observability Layer](https://github.com/lwgray/marcus/issues/30) (#30)
- [ ] [Achieve SOTA on Multi-Agent Development Benchmarks](https://github.com/lwgray/marcus/issues/32) (#32)

## 📹 Release Tasks

- [ ] [Create Time-lapse Demo Video for Marcus 0.1 Release](https://github.com/lwgray/marcus/issues/55) (#55)

---

*This checklist tracks active development tasks and issues for the Marcus project. Update as issues are resolved or new ones are created.*
