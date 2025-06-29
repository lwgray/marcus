#!/usr/bin/env python3
"""
Generate a decision tree diagram for the add_feature tool's fallback mechanisms.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle, Polygon
import numpy as np

# Create figure
fig, ax = plt.subplots(1, 1, figsize=(14, 16))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis('off')

# Colors
color_decision = '#FFE4B5'
color_ai = '#98FB98'
color_fallback = '#FFB6C1'
color_analysis = '#B0E0E6'
color_result = '#DDA0DD'

# Title
ax.text(50, 95, 'add_feature Tool Decision Tree', 
        ha='center', va='center', fontsize=18, fontweight='bold')
ax.text(50, 91, 'Smart Fallback Mechanisms at Each Level', 
        ha='center', va='center', fontsize=12, style='italic')

# Helper functions
def diamond(x, y, size, color, text):
    """Create a diamond decision node"""
    points = np.array([
        [x, y + size],
        [x + size, y],
        [x, y - size],
        [x - size, y]
    ])
    diamond = Polygon(points, facecolor=color, edgecolor='black', linewidth=2)
    ax.add_patch(diamond)
    ax.text(x, y, text, ha='center', va='center', fontsize=9, 
            fontweight='bold', wrap=True)

def box(x, y, w, h, color, text):
    """Create a rectangular box"""
    rect = FancyBboxPatch((x-w/2, y-h/2), w, h,
                         boxstyle="round,pad=0.3",
                         facecolor=color,
                         edgecolor='black',
                         linewidth=2)
    ax.add_patch(rect)
    ax.text(x, y, text, ha='center', va='center', fontsize=9, wrap=True)

def arrow(x1, y1, x2, y2, label='', style='solid'):
    """Draw an arrow with optional label"""
    if style == 'dashed':
        ax.plot([x1, x2], [y1, y2], 'k--', linewidth=1.5)
    else:
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                   arrowprops=dict(arrowstyle='->', lw=2))
    if label:
        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mid_x, mid_y, label, ha='center', fontsize=8,
               bbox=dict(boxstyle="round,pad=0.2", facecolor='white'))

# Level 1: Feature Description Input
box(50, 85, 30, 6, color_analysis, 'Feature Description:\n"Add user profile API"')

# Level 2: AI Feature Analysis
diamond(50, 75, 5, color_decision, 'AI Engine\nHas API Key?')
arrow(50, 82, 50, 80)

# Level 2a: AI Path
box(30, 65, 20, 6, color_ai, 'Claude Analyzes:\n• Understands context\n• Generates detailed tasks')
arrow(45, 75, 35, 70, 'Yes')

# Level 2b: Fallback Path
box(70, 65, 20, 6, color_fallback, 'Keyword Analysis:\n• Detects "API"\n• Pattern matching')
arrow(55, 75, 65, 70, 'No/Error')

# Level 3: Task Generation
box(50, 55, 35, 5, color_result, 'Tasks Generated with Labels:\nDesign, Backend API, Test, Docs')
arrow(30, 62, 40, 58)
arrow(70, 62, 60, 58)

# Level 4: Integration Analysis
diamond(50, 45, 5, color_decision, 'AI Can Analyze\nIntegration?')
arrow(50, 52, 50, 50)

# Level 4a: AI Integration
box(30, 35, 20, 6, color_ai, 'Claude Detects:\n• Dependencies by ID\n• Optimal phase\n• Risks')
arrow(45, 45, 35, 40, 'Yes')

# Level 4b: Fallback Integration
box(70, 35, 20, 6, color_fallback, 'Label Matching:\n• Compare labels\n• Check task status\n• Phase heuristics')
arrow(55, 45, 65, 40, 'No/Error')

# Level 5: Enrichment
box(50, 25, 30, 5, color_analysis, 'BasicEnricher:\nAdjust priority, improve names')
arrow(30, 32, 40, 28)
arrow(70, 32, 60, 28)

# Level 6: Task Creation
box(50, 15, 25, 5, color_result, 'Tasks Created\non Kanban Board')
arrow(50, 22, 50, 18)

# Detailed Fallback Examples (right side)
ax.text(85, 85, 'Fallback Examples:', fontweight='bold', fontsize=11)

# Example 1
y_pos = 78
ax.text(85, y_pos, '1. "Add foobar widget"', fontsize=9, fontweight='bold')
ax.text(85, y_pos-2, '   • No keywords match', fontsize=8)
ax.text(85, y_pos-4, '   • Default: backend task', fontsize=8)
ax.text(85, y_pos-6, '   • Generic labels added', fontsize=8)

# Example 2
y_pos = 68
ax.text(85, y_pos, '2. "Urgent auth fix"', fontsize=9, fontweight='bold')
ax.text(85, y_pos-2, '   • Detects: auth + urgent', fontsize=8)
ax.text(85, y_pos-4, '   • Adds security tasks', fontsize=8)
ax.text(85, y_pos-6, '   • Priority → HIGH', fontsize=8)

# Example 3
y_pos = 58
ax.text(85, y_pos, '3. "UI for dashboard"', fontsize=9, fontweight='bold')
ax.text(85, y_pos-2, '   • Detects: UI keyword', fontsize=8)
ax.text(85, y_pos-4, '   • Frontend tasks only', fontsize=8)
ax.text(85, y_pos-6, '   • Links to existing UI', fontsize=8)

# Fallback Intelligence Box
fallback_text = """Fallback Intelligence:

Keyword Detection:
• API, endpoint → Backend tasks
• UI, page, screen → Frontend tasks
• auth, login → Security tasks
• database, model → Data tasks

Phase Detection:
• 0% complete → "initial"
• Testing active → "testing"  
• 80%+ complete → "maintenance"

Label Matching:
• Finds overlapping labels
• Links related features
• Maintains consistency"""

ax.text(20, 8, fallback_text, fontsize=8,
        bbox=dict(boxstyle="round,pad=0.5", facecolor='#FFFACD', 
                 edgecolor='black', linewidth=1))

# Agent Handling Box
agent_text = """When Agent Gets Vague Task:

1. AI generates instructions
   (may infer meaning)

2. Fallback gives generic
   but structured steps

3. Agent can report blocker:
   "Unclear requirements"

4. System suggests:
   • Ask for clarification
   • Check documentation
   • Make assumptions"""

ax.text(65, 8, agent_text, fontsize=8,
        bbox=dict(boxstyle="round,pad=0.5", facecolor='#E6E6FA', 
                 edgecolor='black', linewidth=1))

# Save
plt.tight_layout()
plt.savefig('/Users/lwgray/dev/marcus/docs/add_feature_decision_tree.png', 
            dpi=300, bbox_inches='tight', facecolor='white')
plt.savefig('/Users/lwgray/dev/marcus/docs/add_feature_decision_tree.pdf', 
            bbox_inches='tight', facecolor='white')

print("Decision tree diagram saved as:")
print("- docs/add_feature_decision_tree.png")
print("- docs/add_feature_decision_tree.pdf")