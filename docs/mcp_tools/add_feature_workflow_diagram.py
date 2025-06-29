#!/usr/bin/env python3
"""
Generate a workflow diagram for the add_feature tool showing the decision tree
and fallback mechanisms.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch
import matplotlib.lines as mlines

# Create figure and axis
fig, ax = plt.subplots(1, 1, figsize=(16, 20))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis('off')

# Define colors
color_input = '#E8F4FD'
color_ai = '#B8E0D2'
color_fallback = '#FFDAB9'
color_process = '#D6E4F0'
color_output = '#C7E9B4'
color_error = '#FFB6C1'

# Helper function to create boxes
def create_box(ax, x, y, width, height, text, color, style='round'):
    if style == 'round':
        box = FancyBboxPatch((x, y), width, height,
                           boxstyle="round,pad=0.5",
                           facecolor=color,
                           edgecolor='black',
                           linewidth=2)
    else:
        box = Rectangle((x, y), width, height,
                       facecolor=color,
                       edgecolor='black',
                       linewidth=2)
    ax.add_patch(box)
    ax.text(x + width/2, y + height/2, text,
           ha='center', va='center', fontsize=10, fontweight='bold',
           wrap=True)

# Helper function to create arrows
def create_arrow(ax, x1, y1, x2, y2, text='', curved=False):
    if curved:
        arrow = FancyArrowPatch((x1, y1), (x2, y2),
                              connectionstyle="arc3,rad=.3",
                              arrowstyle='-|>',
                              mutation_scale=20,
                              linewidth=2,
                              color='black')
    else:
        arrow = FancyArrowPatch((x1, y1), (x2, y2),
                              arrowstyle='-|>',
                              mutation_scale=20,
                              linewidth=2,
                              color='black')
    ax.add_patch(arrow)
    if text:
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        ax.text(mid_x, mid_y, text, ha='center', va='bottom', fontsize=8)

# Title
ax.text(50, 95, 'Marcus add_feature Tool Workflow & Decision Tree', 
        ha='center', va='center', fontsize=16, fontweight='bold')

# 1. Input
create_box(ax, 35, 87, 30, 5, 'User Input:\n"Add user profile feature"', color_input)

# 2. Validation
create_box(ax, 35, 79, 30, 5, 'Validate Input\n(not empty, project exists)', color_process)
create_arrow(ax, 50, 87, 50, 84)

# 3. Parse Feature to Tasks
create_box(ax, 15, 70, 25, 6, 'AI Engine Available?\n(analyze_feature_request)', color_process)
create_arrow(ax, 50, 79, 27.5, 76)

# 3a. AI Path
create_box(ax, 5, 60, 20, 5, 'Call Claude API\nfor Task Analysis', color_ai)
create_arrow(ax, 20, 70, 15, 65, 'Yes')

# 3b. Fallback Path
create_box(ax, 30, 60, 25, 5, 'Keyword Analysis\n(API, UI, Auth, Data)', color_fallback)
create_arrow(ax, 30, 70, 42.5, 65, 'No/Error')

# 4. Task Generation Results
create_box(ax, 15, 50, 30, 5, 'Generated Tasks:\n• Design • Backend • Test • Docs', color_process)
create_arrow(ax, 15, 60, 22.5, 55)
create_arrow(ax, 42.5, 60, 37.5, 55)

# 5. Task Enrichment
create_box(ax, 15, 42, 30, 5, 'Enrich Tasks\n(BasicEnricher)', color_process)
create_arrow(ax, 30, 50, 30, 47)

# 6. Integration Detection
create_box(ax, 55, 70, 30, 6, 'Detect Integration Points\n(analyze_integration_points)', color_process)
create_arrow(ax, 50, 79, 70, 76, curved=True)

# 6a. AI Integration Analysis
create_box(ax, 50, 60, 20, 5, 'Claude Analyzes\nDependencies', color_ai)
create_arrow(ax, 65, 70, 60, 65, 'AI Available')

# 6b. Fallback Integration
create_box(ax, 75, 60, 20, 5, 'Label Matching &\nPhase Detection', color_fallback)
create_arrow(ax, 75, 70, 85, 65, 'Fallback')

# 7. Integration Results
create_box(ax, 55, 50, 30, 5, 'Dependencies & Phase\nIdentified', color_process)
create_arrow(ax, 60, 60, 65, 55)
create_arrow(ax, 85, 60, 80, 55)

# 8. Create Tasks on Board
create_box(ax, 35, 33, 30, 5, 'Create Tasks on\nKanban Board', color_process)
create_arrow(ax, 30, 42, 40, 38)
create_arrow(ax, 70, 50, 60, 38, curved=True)

# 9. Success Response
create_box(ax, 35, 25, 30, 5, 'Return Success\nwith Task IDs', color_output)
create_arrow(ax, 50, 33, 50, 30)

# Agent Retrieval Flow (right side)
ax.text(85, 87, 'When Agent Requests Task:', ha='center', va='center', 
        fontsize=12, fontweight='bold')

# 10. Agent requests task
create_box(ax, 70, 80, 30, 4, 'Agent Requests Task', color_input)

# 11. Task Assignment
create_box(ax, 70, 73, 30, 4, 'Marcus Assigns\n"Implement backend for..."', color_process)
create_arrow(ax, 85, 80, 85, 77)

# 12. Generate Instructions
create_box(ax, 70, 66, 30, 4, 'Generate Instructions\n(AI or Fallback)', color_process)
create_arrow(ax, 85, 73, 85, 70)

# 13. Agent receives task
create_box(ax, 70, 59, 30, 4, 'Agent Receives Task\nwith Instructions', color_process)
create_arrow(ax, 85, 66, 85, 63)

# 14. Decision point
create_box(ax, 70, 50, 30, 5, 'Task Clear?', color_process, style='diamond')
create_arrow(ax, 85, 59, 85, 55)

# 15a. Proceed with task
create_box(ax, 55, 41, 20, 4, 'Agent Works\non Task', color_output)
create_arrow(ax, 75, 52, 65, 45, 'Yes')

# 15b. Report blocker
create_box(ax, 80, 41, 20, 4, 'Report Blocker:\n"Unclear Requirements"', color_error)
create_arrow(ax, 90, 50, 90, 45, 'No')

# 16. Blocker resolution
create_box(ax, 80, 33, 20, 4, 'AI Suggests:\n• Ask PM • Check Docs', color_ai)
create_arrow(ax, 90, 41, 90, 37)

# Legend
legend_y = 15
ax.text(10, legend_y + 5, 'Legend:', fontweight='bold', fontsize=10)
legend_items = [
    (color_input, 'Input/Request'),
    (color_ai, 'AI-Powered'),
    (color_fallback, 'Fallback Logic'),
    (color_process, 'Process/Decision'),
    (color_output, 'Success Output'),
    (color_error, 'Error/Blocker')
]

for i, (color, label) in enumerate(legend_items):
    x = 10 + (i % 3) * 30
    y = legend_y - (i // 3) * 3
    ax.add_patch(Rectangle((x, y), 3, 2, facecolor=color, edgecolor='black'))
    ax.text(x + 4, y + 1, label, va='center', fontsize=9)

# Key Points Box
key_points_text = """Key Points:
• AI engine is always available but may lack API key
• Multiple fallback layers ensure tasks are always created
• Keyword analysis provides intelligent task generation
• Agents can report blockers for unclear tasks
• System maintains workflow continuity"""

ax.text(75, 25, key_points_text, fontsize=9, 
        bbox=dict(boxstyle="round,pad=0.5", facecolor='white', edgecolor='black'))

# Save the diagram
plt.tight_layout()
plt.savefig('/Users/lwgray/dev/marcus/docs/add_feature_workflow_diagram.png', 
            dpi=300, bbox_inches='tight', facecolor='white')
plt.savefig('/Users/lwgray/dev/marcus/docs/add_feature_workflow_diagram.pdf', 
            bbox_inches='tight', facecolor='white')

print("Workflow diagram saved as:")
print("- docs/add_feature_workflow_diagram.png")
print("- docs/add_feature_workflow_diagram.pdf")