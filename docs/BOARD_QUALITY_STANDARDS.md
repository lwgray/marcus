# Marcus Board Quality Standards

## Overview

Marcus evaluates board quality using a comprehensive scoring system that measures task completeness, organization, and metadata richness. A well-structured board enables better AI assistance, clearer project understanding, and more efficient task assignment.

## Board Quality Score (0-1 scale)

Marcus assigns boards a structure score:

- **0.0-0.3**: 🔴 **Chaotic** - Just task titles, minimal organization
- **0.3-0.6**: 🟡 **Basic** - Some organization, missing key metadata
- **0.6-0.8**: 🟢 **Good** - Clear structure, most metadata present
- **0.8-1.0**: 🌟 **Excellent** - Full metadata, well-organized

## Essential Task Properties

### 1. **Descriptions** (25% weight)
**Standard**: Every task must have a meaningful description
- ✅ Good: > 50 characters with context and details
- ✅ Includes: What, why, and acceptance criteria
- ❌ Bad: Empty or vague like "Fix bug"

**Example**:
```
Title: Implement user authentication
Description: Create JWT-based authentication system for user login/logout. 
Should support email/password login, token refresh, and secure password 
storage using bcrypt. Include rate limiting for login attempts.
```

### 2. **Labels** (20% weight)
**Standard**: Tasks should have 2+ labels for proper categorization
- **Phase labels**: `phase:planning`, `phase:development`, `phase:testing`
- **Component labels**: `component:frontend`, `component:backend`, `component:database`
- **Type labels**: `type:feature`, `type:bugfix`, `type:refactor`
- **Priority labels**: `priority:high`, `priority:medium`, `priority:low`
- **Skill labels**: `skill:react`, `skill:python`, `skill:devops`
- **Complexity labels**: `complexity:simple`, `complexity:moderate`, `complexity:complex`

**Example**: A task might have: `[component:backend, type:feature, priority:high, skill:nodejs]`

### 3. **Time Estimates** (25% weight)
**Standard**: All tasks must have realistic time estimates
- ✅ Include `estimated_hours` field
- ✅ Based on complexity and scope
- ✅ Account for testing and review time
- ❌ Avoid: No estimate or unrealistic values

**Guidelines**:
- Simple tasks: 1-4 hours
- Moderate tasks: 4-16 hours (0.5-2 days)
- Complex tasks: 16-40 hours (2-5 days)
- Epic tasks: Should be broken down

### 4. **Priority** (15% weight)
**Standard**: Use priority levels to guide task order
- **Urgent**: Blocking other work or critical path
- **High**: Important for current sprint/milestone
- **Medium**: Standard development tasks
- **Low**: Nice-to-have or future improvements

**Distribution**: A healthy board has varied priorities, not everything "high"

### 5. **Dependencies** (15% weight)
**Standard**: Map task relationships explicitly
- ✅ Use `dependencies` field with task IDs
- ✅ Identify blocking relationships
- ✅ Consider both technical and logical dependencies
- ❌ Avoid: Implicit dependencies only in description

**Example**:
```json
{
  "id": "task-5",
  "title": "Deploy authentication service",
  "dependencies": ["task-1", "task-3", "task-4"]
}
```

## Additional Quality Indicators

### Acceptance Criteria
Well-defined success conditions for each task:

**Backend Task Example**:
```
Acceptance Criteria:
- [ ] API endpoint returns correct status codes
- [ ] Input validation prevents invalid data
- [ ] Unit tests achieve 80% coverage
- [ ] API documentation updated
```

**Frontend Task Example**:
```
Acceptance Criteria:
- [ ] UI matches design mockups
- [ ] Responsive on mobile/tablet/desktop
- [ ] Accessibility score > 90
- [ ] Loading states implemented
```

### Sub-tasks
Break down complex work into manageable pieces:
- Parent tasks for epics/features
- Child tasks for specific implementation steps
- Clear parent-child relationships

### Comments
Track progress and decisions:
- Progress updates
- Blocker descriptions
- Design decisions
- Links to relevant discussions

### Attachments
Supporting materials:
- Design mockups
- Architecture diagrams
- API specifications
- Test results

## Board Organization Standards

### 1. **Phase Structure**
Organize tasks into clear development phases:
- **Phase 1**: Setup & Planning
- **Phase 2**: Core Development
- **Phase 3**: Integration & Testing
- **Phase 4**: Deployment & Documentation
- **Phase 5**: Maintenance & Optimization

### 2. **Component Grouping**
Group related tasks by system component:
- Frontend tasks together
- Backend/API tasks together
- Database/Infrastructure tasks together
- Cross-cutting concerns identified

### 3. **Workflow Patterns**
Prefer these patterns:
- ✅ **Phased**: Clear progression through stages
- ✅ **Parallel**: Multiple tracks when possible
- ⚠️ **Sequential**: When dependencies require it
- ❌ **Ad-hoc**: Avoid random task organization

## Marcus Mode Selection Based on Quality

Marcus automatically selects operation mode based on board quality:

| Board State | Structure Score | Task Count | Selected Mode | Marcus Action |
|------------|----------------|------------|---------------|---------------|
| Empty | N/A | 0 | Creator | Generate full project structure |
| Chaotic | < 0.3 | > 10 | Enricher | Add metadata, organize tasks |
| Basic | 0.3-0.6 | Any | Enricher | Enhance descriptions, add estimates |
| Good | 0.6-0.8 | Any | Adaptive | Light enhancements, focus on execution |
| Excellent | > 0.8 | Any | Adaptive | Minimal intervention, just coordinate |

## How Marcus Improves Board Quality

### Automatic Enrichment
When board quality is low, Marcus adds:
1. **Detailed descriptions** with context
2. **Semantic labels** based on content analysis
3. **Time estimates** using AI prediction
4. **Dependencies** based on logical flow
5. **Acceptance criteria** for clarity
6. **Risk assessments** for complex tasks

### Example Enhancement
**Before** (Chaotic):
```
Title: Fix login
Description: 
Labels: []
```

**After** (Enriched):
```
Title: Fix login authentication timeout issue
Description: Users report being logged out after 5 minutes of inactivity. 
Investigation shows JWT token expiry is set too short. Need to extend 
token lifetime to 24 hours and implement refresh token mechanism.

Labels: [component:backend, type:bugfix, priority:high, skill:nodejs, complexity:moderate]
Estimated Hours: 6
Dependencies: []
Acceptance Criteria:
- [ ] JWT tokens valid for 24 hours
- [ ] Refresh token implemented
- [ ] Auto-refresh before expiry
- [ ] Tests cover token lifecycle
```

## Best Practices for Teams

### 1. **Start with Structure**
- Define phases before creating tasks
- Use consistent labeling taxonomy
- Set up task templates

### 2. **Maintain Quality**
- Regular board reviews
- Update estimates based on actuals
- Keep dependencies current
- Close completed tasks promptly

### 3. **Use Marcus Effectively**
- Let Marcus enrich basic tasks
- Review AI suggestions
- Provide feedback on estimates
- Maintain human oversight

### 4. **Measure Progress**
- Track structure score over time
- Monitor metadata completeness
- Review estimation accuracy
- Analyze workflow patterns

## Quality Checklist

Before considering a board "ready for development":

- [ ] All tasks have descriptions > 50 characters
- [ ] Every task has at least 2 relevant labels  
- [ ] Time estimates present for all tasks
- [ ] Dependencies mapped between related tasks
- [ ] Priorities distributed (not all "high")
- [ ] Acceptance criteria defined for complex tasks
- [ ] Phases clearly organized
- [ ] No "orphan" tasks without context

## Future Enhancements

Potential improvements to board quality standards:

1. **Configurable Standards**: Team-specific quality thresholds
2. **Quality Reports**: Weekly board health metrics
3. **Automated Validation**: Enforce minimum standards
4. **Quality Trends**: Track improvement over time
5. **Team Templates**: Pre-defined board structures
6. **Integration**: Pull request links, CI/CD status

---

By following these standards, teams can create boards that are not only well-organized for human understanding but also optimized for AI assistance, leading to more efficient project execution and better outcomes.