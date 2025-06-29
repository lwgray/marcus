#!/usr/bin/env python3
"""
Generate a diagram showing the lifecycle of a vague task from input to resolution.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, FancyArrowPatch
import matplotlib.patches as mpatches

# Create figure
fig, ax = plt.subplots(1, 1, figsize=(12, 14))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis('off')

# Title
ax.text(50, 95, 'Lifecycle of a Vague Task in Marcus', 
        ha='center', va='center', fontsize=16, fontweight='bold')
ax.text(50, 91, 'From "Add foobar baz widget" to Resolution', 
        ha='center', va='center', fontsize=12, style='italic', color='gray')

# Colors
colors = {
    'user': '#FFE4E1',
    'system': '#E0F2F7',
    'ai': '#E8F5E9',
    'fallback': '#FFF3E0',
    'agent': '#F3E5F5',
    'error': '#FFEBEE',
    'success': '#C8E6C9'
}

def create_stage(x, y, w, h, title, content, color, number):
    """Create a stage box with number"""
    # Main box
    box = FancyBboxPatch((x-w/2, y-h/2), w, h,
                        boxstyle="round,pad=0.5",
                        facecolor=color,
                        edgecolor='black',
                        linewidth=2)
    ax.add_patch(box)
    
    # Number circle
    circle = Circle((x-w/2+2, y+h/2-2), 1.5, 
                   facecolor='white', edgecolor='black', linewidth=2)
    ax.add_patch(circle)
    ax.text(x-w/2+2, y+h/2-2, str(number), ha='center', va='center', 
           fontweight='bold', fontsize=10)
    
    # Title
    ax.text(x, y+h/2-3, title, ha='center', va='center', 
           fontweight='bold', fontsize=10)
    
    # Content
    ax.text(x, y-1, content, ha='center', va='center', 
           fontsize=8, wrap=True)

def create_arrow(x1, y1, x2, y2, label=''):
    """Create arrow between stages"""
    arrow = FancyArrowPatch((x1, y1), (x2, y2),
                          arrowstyle='-|>',
                          mutation_scale=20,
                          linewidth=2,
                          color='#666666')
    ax.add_patch(arrow)
    if label:
        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mid_x, mid_y, label, ha='center', va='center',
               fontsize=8, style='italic',
               bbox=dict(boxstyle="round,pad=0.3", 
                        facecolor='white', alpha=0.8))

# Stage 1: User Input
create_stage(50, 85, 40, 8, 
            'User Input',
            'add_feature("Add foobar baz widget")',
            colors['user'], 1)

# Stage 2: Validation
create_stage(50, 73, 40, 8,
            'Input Validation',
            '✓ Not empty\n✓ Project exists\n✓ Kanban client ready',
            colors['system'], 2)
create_arrow(50, 81, 50, 77)

# Stage 3: AI Analysis Attempt
create_stage(50, 61, 40, 8,
            'AI Feature Analysis',
            'No keywords match "foobar baz"\nFallback activates',
            colors['fallback'], 3)
create_arrow(50, 69, 50, 65)

# Stage 4: Fallback Task Generation
create_stage(50, 49, 40, 8,
            'Fallback Generation',
            'Creates: Design, Backend (default),\nTest, Documentation tasks',
            colors['fallback'], 4)
create_arrow(50, 57, 50, 53)

# Stage 5: Task Creation
create_stage(50, 37, 40, 8,
            'Kanban Board Update',
            'Tasks created with generic labels:\n["feature", "backend"]',
            colors['system'], 5)
create_arrow(50, 45, 50, 41)

# Stage 6: Agent Assignment
create_stage(25, 25, 35, 8,
            'Agent Gets Task',
            '"Implement backend for\nAdd foobar baz widget"',
            colors['agent'], 6)
create_arrow(40, 33, 30, 29, 'Later...')

# Stage 7a: Agent Confusion
create_stage(10, 13, 25, 8,
            'Agent Response',
            'Reports Blocker:\n"What is a foobar\nbaz widget?"',
            colors['error'], 7)
create_arrow(20, 21, 15, 17)

# Stage 7b: Agent Assumption
create_stage(40, 13, 25, 8,
            'Alternative Response',
            'Makes assumption:\n"Generic CRUD API"',
            colors['success'], 7)
create_arrow(30, 21, 35, 17)

# Stage 8: Resolution
create_stage(75, 25, 35, 8,
            'AI Blocker Analysis',
            'Suggests:\n• Ask product owner\n• Check similar features',
            colors['ai'], 8)
create_arrow(22.5, 13, 65, 21, 'If blocked')

# Stage 9: Human Intervention
create_stage(75, 13, 35, 8,
            'Resolution',
            'Human clarifies:\n"Widget = user preference component"',
            colors['success'], 9)
create_arrow(75, 21, 75, 17)

# Side panels with details
# Left panel: Fallback Intelligence
fallback_details = """Fallback Intelligence:

Even with "foobar baz widget":
• Generates structured tasks
• Applies default patterns
• Maintains workflow

Default assumptions:
• Backend implementation
• Standard CRUD operations
• RESTful API design
• Unit testing required"""

ax.text(2, 55, fallback_details, fontsize=8,
        bbox=dict(boxstyle="round,pad=0.5", 
                 facecolor=colors['fallback'], 
                 edgecolor='black', alpha=0.7))

# Right panel: Safety Mechanisms
safety_details = """Safety Mechanisms:

1. Never fails silently
2. Always creates something
3. Blocker reporting available
4. AI assists with clarification
5. Human escalation path

Result: Workflow continues
even with ambiguous input"""

ax.text(75, 55, safety_details, fontsize=8,
        bbox=dict(boxstyle="round,pad=0.5", 
                 facecolor=colors['success'], 
                 edgecolor='black', alpha=0.7))

# Bottom summary
summary = """Key Insight: The system is designed to maintain momentum. Even completely ambiguous tasks like "foobar baz widget" 
result in assignable work items that can be clarified through the blocker resolution system."""

ax.text(50, 3, summary, ha='center', va='center', fontsize=9,
        style='italic', wrap=True,
        bbox=dict(boxstyle="round,pad=0.5", 
                 facecolor='lightyellow', 
                 edgecolor='black'))

# Legend
legend_elements = [
    mpatches.Patch(facecolor=colors['user'], edgecolor='black', label='User Action'),
    mpatches.Patch(facecolor=colors['system'], edgecolor='black', label='System Process'),
    mpatches.Patch(facecolor=colors['fallback'], edgecolor='black', label='Fallback Logic'),
    mpatches.Patch(facecolor=colors['agent'], edgecolor='black', label='Agent Action'),
    mpatches.Patch(facecolor=colors['error'], edgecolor='black', label='Blocker/Issue'),
    mpatches.Patch(facecolor=colors['success'], edgecolor='black', label='Resolution')
]
ax.legend(handles=legend_elements, loc='upper right', fontsize=8)

# Save
plt.tight_layout()
plt.savefig('/Users/lwgray/dev/marcus/docs/vague_task_lifecycle.png', 
            dpi=300, bbox_inches='tight', facecolor='white')
plt.savefig('/Users/lwgray/dev/marcus/docs/vague_task_lifecycle.pdf', 
            bbox_inches='tight', facecolor='white')

print("Vague task lifecycle diagram saved as:")
print("- docs/vague_task_lifecycle.png")
print("- docs/vague_task_lifecycle.pdf")