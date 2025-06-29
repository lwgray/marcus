#!/usr/bin/env python3
"""
Generate a clean, well-organized workflow diagram for the add_feature tool.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle
import matplotlib.lines as mlines

# Create figure with better proportions
fig, ax = plt.subplots(1, 1, figsize=(12, 10))
ax.set_xlim(0, 12)
ax.set_ylim(0, 10)
ax.axis('off')

# Colors
colors = {
    'input': '#E3F2FD',      # Light blue
    'process': '#F5F5F5',    # Light gray
    'ai': '#C8E6C9',         # Light green
    'fallback': '#FFE0B2',   # Light orange
    'output': '#E1F5FE',     # Light cyan
    'error': '#FFCDD2',      # Light red
}

# Helper functions
def box(ax, x, y, w, h, text, color, style='box'):
    """Create a box with text"""
    if style == 'rounded':
        patch = FancyBboxPatch((x, y), w, h,
                              boxstyle="round,pad=0.1",
                              facecolor=color,
                              edgecolor='#333',
                              linewidth=1.5)
    else:
        patch = Rectangle((x, y), w, h,
                         facecolor=color,
                         edgecolor='#333',
                         linewidth=1.5)
    ax.add_patch(patch)
    
    # Add text centered in box
    ax.text(x + w/2, y + h/2, text,
           ha='center', va='center',
           fontsize=9, fontweight='normal',
           wrap=True)

def arrow(ax, x1, y1, x2, y2, text=''):
    """Draw arrow between boxes"""
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
               arrowprops=dict(arrowstyle='->', lw=1.5, color='#333'))
    if text:
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        ax.text(mid_x, mid_y, text, ha='center', va='center',
               fontsize=8, bbox=dict(boxstyle="round,pad=0.3",
                                   facecolor='white', edgecolor='none'))

def diamond(ax, x, y, w, h, text, color):
    """Create a diamond decision shape"""
    # Create diamond points
    points = [(x + w/2, y + h),    # top
              (x + w, y + h/2),     # right
              (x + w/2, y),         # bottom
              (x, y + h/2)]         # left
    
    patch = patches.Polygon(points, facecolor=color, 
                          edgecolor='#333', linewidth=1.5)
    ax.add_patch(patch)
    
    ax.text(x + w/2, y + h/2, text,
           ha='center', va='center',
           fontsize=9, fontweight='normal')

# Title
ax.text(6, 9.5, 'Marcus add_feature Tool Workflow',
       ha='center', fontsize=14, fontweight='bold')

# Main Flow - Left Side
y_start = 8.5

# 1. User Input
box(ax, 1, y_start, 3, 0.8, 'User calls:\nadd_feature("Add user profile")', 
    colors['input'], 'rounded')

# 2. Validation
box(ax, 1, y_start - 1.5, 3, 0.8, 'Validate input &\ncheck prerequisites', 
    colors['process'])
arrow(ax, 2.5, y_start, 2.5, y_start - 0.7)

# 3. Feature Analysis Decision
diamond(ax, 1, y_start - 3.5, 3, 1.2, 'AI available?', colors['process'])
arrow(ax, 2.5, y_start - 2.3, 2.5, y_start - 2.5)

# 4a. AI Path
box(ax, 0, y_start - 5.5, 2, 0.8, 'Claude API\nanalyzes', colors['ai'])
arrow(ax, 1.5, y_start - 3.5, 1, y_start - 4.7, 'Yes')

# 4b. Fallback Path  
box(ax, 2.5, y_start - 5.5, 2, 0.8, 'Keyword\nanalysis', colors['fallback'])
arrow(ax, 3, y_start - 3.5, 3.5, y_start - 4.7, 'No')

# 5. Task Generation
box(ax, 1, y_start - 7, 3, 0.8, 'Generate tasks:\nDesign, Backend, Test, Docs', 
    colors['process'])
arrow(ax, 1, y_start - 5.5, 2, y_start - 6.2)
arrow(ax, 3.5, y_start - 5.5, 2.5, y_start - 6.2)

# 6. Create on Board
box(ax, 1, y_start - 8.5, 3, 0.8, 'Create tasks on\nKanban board', 
    colors['output'], 'rounded')
arrow(ax, 2.5, y_start - 7, 2.5, y_start - 7.7)

# Integration Flow - Middle
# 7. Integration Analysis
diamond(ax, 5, y_start - 3.5, 3, 1.2, 'AI can analyze\nintegration?', colors['process'])
arrow(ax, 4.5, y_start - 3, 5, y_start - 3)

# 8a. AI Integration
box(ax, 4.5, y_start - 5.5, 2, 0.8, 'Claude finds\ndependencies', colors['ai'])
arrow(ax, 6, y_start - 3.5, 5.5, y_start - 4.7, 'Yes')

# 8b. Fallback Integration
box(ax, 7, y_start - 5.5, 2, 0.8, 'Label\nmatching', colors['fallback'])
arrow(ax, 7, y_start - 3.5, 8, y_start - 4.7, 'No')

# 9. Dependencies Found
box(ax, 5, y_start - 7, 3, 0.8, 'Dependencies &\nphase detected', colors['process'])
arrow(ax, 5.5, y_start - 5.5, 6, y_start - 6.2)
arrow(ax, 8, y_start - 5.5, 7.5, y_start - 6.2)

# Connect to task creation
arrow(ax, 6.5, y_start - 7, 4, y_start - 8.1)

# Agent Flow - Right Side
ax.text(10, y_start + 0.3, 'Agent Workflow', 
       ha='center', fontsize=11, fontweight='bold')

# 10. Agent requests
box(ax, 8.5, y_start - 1, 3, 0.8, 'Agent requests\nnext task', colors['input'])

# 11. Task assigned
box(ax, 8.5, y_start - 2.5, 3, 0.8, 'Gets: "Implement\nbackend for..."', colors['process'])
arrow(ax, 10, y_start - 1, 10, y_start - 1.7)

# 12. Instructions generated
box(ax, 8.5, y_start - 4, 3, 0.8, 'AI generates\ninstructions', colors['ai'])
arrow(ax, 10, y_start - 2.5, 10, y_start - 3.2)

# 13. Decision
diamond(ax, 8.5, y_start - 6, 3, 1.2, 'Task clear?', colors['process'])
arrow(ax, 10, y_start - 4, 10, y_start - 4.8)

# 14a. Work on task
box(ax, 7, y_start - 8, 2, 0.8, 'Agent works\non task', colors['output'])
arrow(ax, 9, y_start - 6, 8, y_start - 7.2, 'Yes')

# 14b. Report blocker
box(ax, 10, y_start - 8, 2, 0.8, 'Report\nblocker', colors['error'])
arrow(ax, 10.5, y_start - 6, 11, y_start - 7.2, 'No')

# Legend
legend_y = 0.5
legend_items = [
    (colors['input'], 'Input/Request'),
    (colors['ai'], 'AI-Powered'),
    (colors['fallback'], 'Fallback Logic'),
    (colors['process'], 'Process/Decision'),
    (colors['output'], 'Output/Success'),
    (colors['error'], 'Error/Blocker')
]

ax.text(1, legend_y + 0.8, 'Legend:', fontsize=10, fontweight='bold')
for i, (color, label) in enumerate(legend_items):
    x = 1 + (i % 3) * 3.5
    y = legend_y + 0.3 - (i // 3) * 0.4
    box(ax, x, y, 0.3, 0.3, '', color)
    ax.text(x + 0.5, y + 0.15, label, va='center', fontsize=9)

# Key Points
points_text = """Key Features:
• AI always available but may lack API key
• Smart fallbacks at each decision point
• Tasks always created, never fails silently
• Agents can report blockers for clarity"""

ax.text(7.5, 1.2, points_text, fontsize=9,
       bbox=dict(boxstyle="round,pad=0.4",
                facecolor='#FFFEF0', edgecolor='#333'))

# Save
plt.tight_layout()
plt.savefig('/Users/lwgray/dev/marcus/docs/add_feature_clean_workflow.png',
           dpi=300, bbox_inches='tight', facecolor='white', pad_inches=0.3)
plt.savefig('/Users/lwgray/dev/marcus/docs/add_feature_clean_workflow.pdf',
           bbox_inches='tight', facecolor='white', pad_inches=0.3)

print("Clean workflow diagram saved as:")
print("- docs/add_feature_clean_workflow.png")
print("- docs/add_feature_clean_workflow.pdf")