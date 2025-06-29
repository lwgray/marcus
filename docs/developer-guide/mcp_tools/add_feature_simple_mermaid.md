# Simple Mermaid Diagram - add_feature Smart Fallbacks

## Core Decision Flow

```mermaid
flowchart TD
    Start[add_feature<br/>'Add foobar baz widget'] --> Check1{AI Available?}
    
    Check1 -->|✓ API Key| Path1A[Claude Understands Context]
    Check1 -->|✗ No Key| Path1B[Keyword Analysis:<br/>No match → Default tasks]
    
    Path1A --> Tasks[Tasks Generated:<br/>Design, Backend, Test, Docs]
    Path1B --> Tasks
    
    Tasks --> Check2{Integration AI?}
    
    Check2 -->|✓ Available| Path2A[AI Finds Dependencies]
    Check2 -->|✗ Fallback| Path2B[Label Matching:<br/>Compares existing tasks]
    
    Path2A --> Result[Tasks Created with:<br/>• Smart dependencies<br/>• Correct phase<br/>• Priority set]
    Path2B --> Result
    
    Result --> Agent[Agent receives:<br/>'Implement backend for<br/>Add foobar baz widget']
    
    Agent --> Options{Clear task?}
    Options -->|Yes| Work[Works on task]
    Options -->|No| Block[Reports blocker →<br/>Gets AI help]
    
    style Start fill:#E8F4FD
    style Path1A fill:#C8E6C9
    style Path2A fill:#C8E6C9
    style Path1B fill:#FFCC80
    style Path2B fill:#FFCC80
    style Work fill:#90EE90
    style Block fill:#FFB6C1
```

## Key Points Visualization

```mermaid
graph LR
    subgraph "Fallback Ensures"
        F1[Tasks Always Created]
        F2[Structure Maintained]
        F3[Dependencies Detected]
        F4[Workflow Continues]
        F5[Clarification Available]
    end
    
    subgraph "Intelligence Layers"
        L1[Keyword Detection]
        L2[Pattern Matching]
        L3[Label Analysis]
        L4[Phase Detection]
        L5[Priority Adjustment]
    end
    
    L1 --> F1
    L2 --> F2
    L3 --> F3
    L4 --> F4
    L5 --> F5
```

## Example: Vague Input Processing

```mermaid
stateDiagram-v2
    [*] --> Input: "Add foobar widget"
    Input --> NoKeywords: No keywords match
    NoKeywords --> DefaultLogic: Apply defaults
    DefaultLogic --> GenerateTasks: Create standard tasks
    GenerateTasks --> EnrichTasks: Add estimates & labels
    EnrichTasks --> CreateOnBoard: Post to Kanban
    CreateOnBoard --> AgentAssignment: Assign to developer
    AgentAssignment --> Decision: Agent evaluates
    Decision --> Work: Understands enough
    Decision --> Blocker: Needs clarification
    Blocker --> Resolution: Human/AI helps
    Work --> [*]: Task completed
    Resolution --> Work: Clarified
```

This simplified Mermaid diagram can be embedded directly in:
- GitHub README files
- Confluence pages  
- Any markdown documentation
- Issue descriptions
- Pull request descriptions