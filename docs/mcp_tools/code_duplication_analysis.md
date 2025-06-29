# Code Duplication Analysis: create_project vs add_feature

## Overview
Both `create_project` and `add_feature` are natural language processing tools that convert descriptions into tasks and add them to the kanban board. They share significant similarities but also have key differences.

## Shared Code/Logic

### 1. **Duplicate Task Creation Logic** 
Both classes have identical code for creating tasks on the kanban board:

```python
# Exact same code in both classes (lines 81-99 and 240-258)
if hasattr(self.kanban_client, 'create_task'):
    for task in safe_tasks:
        kanban_task = await self.kanban_client.create_task({
            "name": task.name,
            "description": task.description,
            "priority": task.priority.value,
            "labels": task.labels,
            "estimated_hours": task.estimated_hours,
            "dependencies": task.dependencies
        })
        created_tasks.append(kanban_task)
```

### 2. **Duplicate Safety Check Logic**
Both implement safety checks but with slight variations:

**NaturalLanguageProjectCreator** has:
- `_apply_safety_checks()` (lines 144-163)
- `_is_deployment_task()` (lines 165-169)
- `_is_implementation_task()` (lines 171-175)
- `_is_testing_task()` (lines 177-181)

**NaturalLanguageFeatureAdder** has:
- `_apply_feature_safety_checks()` (lines 491-511)
- Inline checking without separate methods
- Less sophisticated keyword matching

### 3. **Shared Dependencies**
Both use the same core components:
- `kanban_client` for board operations
- `ai_engine` for AI processing
- Task enrichment patterns
- Similar error handling

### 4. **Common Patterns**
- Parse natural language → Generate tasks → Apply safety → Create on board
- Both return similar result structures with success status
- Both handle kanban client compatibility checks

## Key Differences

### 1. **Context Awareness**
- **create_project**: Assumes empty board, uses Creator Mode
- **add_feature**: Works with existing tasks, uses Adaptive Mode

### 2. **Dependency Handling**
- **create_project**: Creates internal dependencies between new tasks
- **add_feature**: Maps dependencies to existing project tasks

### 3. **AI Components**
- **create_project**: Uses `AdvancedPRDParser` for full PRD parsing
- **add_feature**: Uses simpler parsing, focuses on integration

### 4. **Initialization**
- **create_project**: Takes kanban_client and ai_engine
- **add_feature**: Also requires existing project_tasks

## Refactoring Opportunities

### 1. **Extract Common Base Class**
```python
class NaturalLanguageTaskCreator:
    """Base class for natural language task creation"""
    
    def __init__(self, kanban_client, ai_engine):
        self.kanban_client = kanban_client
        self.ai_engine = ai_engine
    
    async def create_tasks_on_board(self, tasks: List[Task]) -> List[Task]:
        """Common task creation logic"""
        created_tasks = []
        if hasattr(self.kanban_client, 'create_task'):
            for task in tasks:
                kanban_task = await self.kanban_client.create_task({
                    "name": task.name,
                    "description": task.description,
                    "priority": task.priority.value,
                    "labels": task.labels,
                    "estimated_hours": task.estimated_hours,
                    "dependencies": task.dependencies
                })
                created_tasks.append(kanban_task)
        return created_tasks
    
    def is_deployment_task(self, task: Task) -> bool:
        """Check if task is deployment-related"""
        keywords = ["deploy", "release", "production", "launch"]
        return any(keyword in task.name.lower() for keyword in keywords)
    
    def is_implementation_task(self, task: Task) -> bool:
        """Check if task is implementation-related"""
        keywords = ["implement", "build", "create", "develop", "code"]
        return any(keyword in task.name.lower() for keyword in keywords)
    
    def is_testing_task(self, task: Task) -> bool:
        """Check if task is testing-related"""
        keywords = ["test", "qa", "quality", "verify"]
        return any(keyword in task.name.lower() for keyword in keywords)
    
    async def apply_safety_checks(self, tasks: List[Task]) -> List[Task]:
        """Apply common safety checks"""
        deployment_tasks = [t for t in tasks if self.is_deployment_task(t)]
        
        for deploy_task in deployment_tasks:
            impl_tasks = [t for t in tasks if self.is_implementation_task(t)]
            test_tasks = [t for t in tasks if self.is_testing_task(t)]
            
            for impl_task in impl_tasks:
                if impl_task.id not in deploy_task.dependencies:
                    deploy_task.dependencies.append(impl_task.id)
            
            for test_task in test_tasks:
                if test_task.id not in deploy_task.dependencies:
                    deploy_task.dependencies.append(test_task.id)
        
        return tasks
```

### 2. **Extract Task Classification**
```python
class TaskClassifier:
    """Classify tasks by type"""
    
    DEPLOYMENT_KEYWORDS = ["deploy", "release", "production", "launch"]
    IMPLEMENTATION_KEYWORDS = ["implement", "build", "create", "develop", "code"]
    TESTING_KEYWORDS = ["test", "qa", "quality", "verify"]
    
    @classmethod
    def classify(cls, task: Task) -> TaskType:
        task_lower = task.name.lower()
        
        if any(kw in task_lower for kw in cls.DEPLOYMENT_KEYWORDS):
            return TaskType.DEPLOYMENT
        elif any(kw in task_lower for kw in cls.IMPLEMENTATION_KEYWORDS):
            return TaskType.IMPLEMENTATION
        elif any(kw in task_lower for kw in cls.TESTING_KEYWORDS):
            return TaskType.TESTING
        else:
            return TaskType.OTHER
```

### 3. **Shared Task Builder**
```python
class TaskBuilder:
    """Build task dictionaries for kanban creation"""
    
    @staticmethod
    def build_task_data(task: Task) -> Dict[str, Any]:
        return {
            "name": task.name,
            "description": task.description,
            "priority": task.priority.value,
            "labels": task.labels,
            "estimated_hours": task.estimated_hours,
            "dependencies": task.dependencies
        }
```

## Current Code Quality Assessment

**Duplication Level: MEDIUM-HIGH**

The code has significant duplication that should be addressed:
- Identical task creation logic (20+ lines duplicated)
- Similar safety check implementations
- Repeated task classification logic
- Common patterns not abstracted

## Recommendations

1. **Immediate**: Extract the common task creation logic into a shared method
2. **Short-term**: Create a base class for shared functionality
3. **Long-term**: Consider a more unified architecture where both tools use the same core engine with different configurations

## Impact of Refactoring

### Benefits:
- Reduce code duplication by ~40%
- Easier maintenance and bug fixes
- Consistent behavior across both tools
- Better testability

### Risks:
- May introduce bugs if not carefully tested
- Need to ensure both tools still work independently
- Backward compatibility considerations