# Marcus add_feature Tool - Mermaid Diagrams

## 1. Main Workflow & Decision Tree

```mermaid
flowchart TD
    Start([User Input: add_feature]) --> Validate{Validate Input}
    
    Validate -->|Valid| FeatureAnalysis{AI Engine<br/>Available?}
    Validate -->|Invalid| Error1[Return Error:<br/>Invalid Input]
    
    FeatureAnalysis -->|Yes| AIAnalyze[Claude API<br/>Analyzes Feature]
    FeatureAnalysis -->|No/Error| FallbackAnalyze[Keyword Analysis<br/>Pattern Matching]
    
    AIAnalyze --> TaskGen[Generate Tasks:<br/>• Design<br/>• Backend<br/>• Test<br/>• Documentation]
    FallbackAnalyze --> TaskGen
    
    TaskGen --> Enrich[Enrich Tasks<br/>with BasicEnricher]
    
    Enrich --> IntegrationCheck{AI Can Analyze<br/>Integration?}
    
    IntegrationCheck -->|Yes| AIIntegration[Claude Detects:<br/>• Dependencies by ID<br/>• Project Phase<br/>• Integration Risks]
    IntegrationCheck -->|No/Error| FallbackIntegration[Label Matching:<br/>• Compare Labels<br/>• Check Status<br/>• Phase Heuristics]
    
    AIIntegration --> CreateTasks[Create Tasks<br/>on Kanban Board]
    FallbackIntegration --> CreateTasks
    
    CreateTasks --> Success[Return Success<br/>with Task IDs]
    
    %% Agent Flow
    AgentStart([Agent Requests Task]) --> Assign[Marcus Assigns:<br/>'Implement backend for...']
    Assign --> GenInstructions[Generate Instructions<br/>AI or Fallback]
    GenInstructions --> AgentReceives[Agent Receives<br/>Task + Instructions]
    AgentReceives --> Clear{Task Clear?}
    Clear -->|Yes| Work[Agent Works<br/>on Task]
    Clear -->|No| Blocker[Report Blocker:<br/>'Unclear Requirements']
    Blocker --> AIHelp[AI Suggests:<br/>• Ask PM<br/>• Check Docs]
    
    style Start fill:#E3F2FD
    style Success fill:#C8E6C9
    style Error1 fill:#FFCDD2
    style AIAnalyze fill:#A5D6A7
    style FallbackAnalyze fill:#FFCC80
    style AIIntegration fill:#A5D6A7
    style FallbackIntegration fill:#FFCC80
    style Work fill:#C8E6C9
    style Blocker fill:#FFCDD2
```

## 2. Smart Fallback Flow

```mermaid
flowchart TD
    Input[Input: 'Add foobar baz widget'<br/>Vague feature description] --> Decision1{API Key?}
    
    Decision1 -->|Yes| AI1[Feature Analysis<br/>AI tries to understand]
    Decision1 -->|No| Fallback1[Keyword Fallback<br/>Pattern matching]
    
    AI1 --> Tasks[Tasks Generated<br/>Design, Backend, Test, Docs]
    Fallback1 --> Tasks
    
    Tasks --> Decision2{AI Available?}
    
    Decision2 -->|Yes| AI2[AI Integration<br/>Analyzes dependencies]
    Decision2 -->|No| Fallback2[Label Matching<br/>Compares task labels]
    
    AI2 --> Board[Tasks Created on Board<br/>With dependencies & enrichment]
    Fallback2 --> Board
    
    Board --> Agent[Agent Gets: 'Implement backend...'<br/>Can work or report blocker]
    
    style Input fill:#E1F5FE
    style AI1 fill:#A5D6A7
    style AI2 fill:#A5D6A7
    style Fallback1 fill:#FFCC80
    style Fallback2 fill:#FFCC80
    style Board fill:#E1F5FE
    style Agent fill:#F5F5F5
```

## 3. Vague Task Lifecycle

```mermaid
flowchart TD
    UserInput[User: add_feature<br/>'Add foobar baz widget'] --> Validation[Input Validation<br/>✓ Not empty<br/>✓ Project exists]
    
    Validation --> AIAttempt[AI Feature Analysis<br/>No keywords match<br/>Fallback activates]
    
    AIAttempt --> FallbackGen[Fallback Generation<br/>• Design foobar baz widget<br/>• Implement backend default<br/>• Test & Document]
    
    FallbackGen --> CreateBoard[Kanban Board Update<br/>Tasks with generic labels:<br/>feature, backend]
    
    CreateBoard --> AgentAssign[Agent Gets Task<br/>'Implement backend for<br/>Add foobar baz widget']
    
    AgentAssign --> AgentChoice{Agent Response}
    
    AgentChoice -->|Confused| ReportBlocker[Report Blocker:<br/>'What is a foobar<br/>baz widget?']
    AgentChoice -->|Assumption| MakeAssumption[Makes Assumption:<br/>'Generic CRUD API']
    
    ReportBlocker --> AIBlocker[AI Blocker Analysis<br/>Suggests:<br/>• Ask product owner<br/>• Check similar features]
    
    AIBlocker --> Resolution[Human Clarifies:<br/>'Widget = user preference<br/>component']
    
    style UserInput fill:#FFE4E1
    style FallbackGen fill:#FFF3E0
    style CreateBoard fill:#E0F2F7
    style ReportBlocker fill:#FFEBEE
    style MakeAssumption fill:#C8E6C9
    style Resolution fill:#C8E6C9
```

## 4. Decision Tree for Fallback Mechanisms

```mermaid
graph TD
    Start[Feature Description] --> Q1{AI Engine<br/>Has API Key?}
    
    Q1 -->|Yes| AI1[Claude Analyzes Context]
    Q1 -->|No| FB1[Keyword Analysis]
    
    AI1 --> AI1Result[Detailed Tasks<br/>with Context]
    FB1 --> FB1Result[Pattern-Based Tasks]
    
    FB1 --> KW1{Contains 'API'?}
    KW1 -->|Yes| AddAPI[Add Backend Tasks]
    KW1 -->|No| KW2{Contains 'UI'?}
    
    KW2 -->|Yes| AddUI[Add Frontend Tasks]
    KW2 -->|No| KW3{Contains 'auth'?}
    
    KW3 -->|Yes| AddAuth[Add Security Tasks]
    KW3 -->|No| DefaultTasks[Add Default Backend]
    
    AI1Result --> Q2{Can Analyze<br/>Integration?}
    FB1Result --> Q2
    
    Q2 -->|Yes| AI2[Claude Detects<br/>Dependencies]
    Q2 -->|No| FB2[Label Matching]
    
    FB2 --> Phase1{Project Status?}
    Phase1 -->|0% Complete| Initial[Phase: Initial]
    Phase1 -->|Testing Active| Testing[Phase: Testing]
    Phase1 -->|80%+ Complete| Maintenance[Phase: Maintenance]
    Phase1 -->|Other| Development[Phase: Development]
    
    style AI1 fill:#98FB98
    style AI2 fill:#98FB98
    style FB1 fill:#FFB6C1
    style FB2 fill:#FFB6C1
```

## 5. Fallback Intelligence Examples

```mermaid
graph LR
    subgraph Input Examples
        E1["'Add user auth'"]
        E2["'Add API endpoint'"]
        E3["'Add foobar widget'"]
    end
    
    subgraph Detection
        D1[Detects: auth keyword]
        D2[Detects: API keyword]
        D3[No keywords match]
    end
    
    subgraph Output
        O1[Security tasks added<br/>Links to existing auth]
        O2[Backend tasks added<br/>REST conventions]
        O3[Default backend tasks<br/>Generic implementation]
    end
    
    E1 --> D1 --> O1
    E2 --> D2 --> O2
    E3 --> D3 --> O3
    
    style E1 fill:#FFF9C4
    style E2 fill:#FFF9C4
    style E3 fill:#FFF9C4
    style O1 fill:#E8F5E9
    style O2 fill:#E8F5E9
    style O3 fill:#E8F5E9
```

## Usage in Documentation

To use these diagrams in your markdown documentation:

1. Copy the mermaid code block
2. Paste into any markdown file that supports Mermaid
3. GitHub, GitLab, and many documentation tools render Mermaid automatically

For example:
- GitHub README.md files
- Docusaurus documentation
- MkDocs with mermaid plugin
- Notion pages
- Obsidian notes

## Customization

You can customize colors by modifying the style declarations:
- `fill:#COLOR` - Background color
- `stroke:#COLOR` - Border color
- `stroke-width:2px` - Border thickness

Common color codes used:
- AI/Success: `#A5D6A7` (green)
- Fallback: `#FFCC80` (orange)
- Process: `#E1F5FE` (light blue)
- Error: `#FFCDD2` (light red)
- Input: `#E3F2FD` (pale blue)