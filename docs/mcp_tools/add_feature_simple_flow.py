#!/usr/bin/env python3
"""
Generate a simple, clean flow diagram for the add_feature tool focusing on the fallback mechanism.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle

# Create figure
fig, ax = plt.subplots(1, 1, figsize=(10, 8))
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis('off')

# Title
ax.text(5, 9.5, 'Smart Fallback Flow in add_feature Tool',
       ha='center', fontsize=14, fontweight='bold')

# Colors
ai_color = '#A5D6A7'      # Green
fallback_color = '#FFCC80' # Orange
process_color = '#E1F5FE'  # Light blue

def create_flow_box(x, y, w, h, title, details, color):
    """Create a flow box with title and details"""
    # Main box
    box = FancyBboxPatch((x-w/2, y-h/2), w, h,
                        boxstyle="round,pad=0.1",
                        facecolor=color,
                        edgecolor='#444',
                        linewidth=2)
    ax.add_patch(box)
    
    # Title (bold)
    ax.text(x, y + h/2 - 0.3, title,
           ha='center', va='center',
           fontsize=11, fontweight='bold')
    
    # Details
    ax.text(x, y - 0.1, details,
           ha='center', va='center',
           fontsize=9, style='italic')

def create_arrow(x1, y1, x2, y2, label='', style='solid'):
    """Create an arrow with optional label"""
    if style == 'solid':
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                   arrowprops=dict(arrowstyle='->', lw=2, color='#444'))
    else:
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                   arrowprops=dict(arrowstyle='->', lw=2, 
                                 color='#888', linestyle='dashed'))
    
    if label:
        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mid_x, mid_y + 0.2, label, ha='center', fontsize=9,
               bbox=dict(boxstyle="round,pad=0.3",
                        facecolor='white', edgecolor='none'))

# Flow elements
# 1. Input
create_flow_box(5, 8.5, 4, 0.8,
               'Input: "Add foobar baz widget"',
               'Vague feature description',
               process_color)

# 2. Feature Analysis
create_flow_box(3, 7, 3.5, 1,
               'Feature Analysis',
               'AI tries to understand',
               ai_color)

create_flow_box(7, 7, 3.5, 1,
               'Keyword Fallback',
               'Pattern matching',
               fallback_color)

create_arrow(5, 8.1, 3, 7.5, 'API Key?')
create_arrow(5, 8.1, 7, 7.5, 'No API Key', 'dashed')

# 3. Task Generation
create_flow_box(5, 5.5, 4.5, 1,
               'Tasks Generated',
               'Design, Backend, Test, Docs',
               process_color)

create_arrow(3, 6.5, 5, 6)
create_arrow(7, 6.5, 5, 6)

# 4. Integration Analysis
create_flow_box(3, 4, 3.5, 1,
               'AI Integration',
               'Analyzes dependencies',
               ai_color)

create_flow_box(7, 4, 3.5, 1,
               'Label Matching',
               'Compares task labels',
               fallback_color)

create_arrow(4.5, 5, 3, 4.5)
create_arrow(5.5, 5, 7, 4.5, style='dashed')

# 5. Result
create_flow_box(5, 2.5, 5, 1,
               'Tasks Created on Board',
               'With dependencies & enrichment',
               process_color)

create_arrow(3, 3.5, 5, 3)
create_arrow(7, 3.5, 5, 3)

# 6. Agent receives
create_flow_box(5, 1, 5, 0.8,
               'Agent Gets: "Implement backend..."',
               'Can work or report blocker',
               '#F5F5F5')

create_arrow(5, 2, 5, 1.4)

# Examples sidebar
examples = """Fallback Intelligence Examples:

"Add user auth" → Detects 'auth'
  → Security tasks added
  → Links to existing auth

"Add API endpoint" → Detects 'API'
  → Backend tasks added
  → REST conventions applied

"Add foobar widget" → No keywords
  → Default backend tasks
  → Generic implementation"""

ax.text(0.5, 4, examples, fontsize=8,
       bbox=dict(boxstyle="round,pad=0.5",
                facecolor='#FFF9C4',
                edgecolor='#444'))

# Results sidebar
results = """Fallback Ensures:

✓ Tasks always created
✓ Logical structure maintained
✓ Dependencies detected
✓ Workflow continues
✓ Clarification possible"""

ax.text(9.5, 4, results, fontsize=8, ha='right',
       bbox=dict(boxstyle="round,pad=0.5",
                facecolor='#E8F5E9',
                edgecolor='#444'))

# Legend
ax.text(5, 0.3, 'Green = AI-powered  |  Orange = Smart fallback  |  Blue = Process',
       ha='center', fontsize=9, style='italic')

# Save
plt.tight_layout()
plt.savefig('/Users/lwgray/dev/marcus/docs/add_feature_simple_flow.png',
           dpi=300, bbox_inches='tight', facecolor='white')
plt.savefig('/Users/lwgray/dev/marcus/docs/add_feature_simple_flow.pdf',
           bbox_inches='tight', facecolor='white')

print("Simple flow diagram saved as:")
print("- docs/add_feature_simple_flow.png")
print("- docs/add_feature_simple_flow.pdf")