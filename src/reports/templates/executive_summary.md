
# Executive Summary: {{ project_name }}

**Generated:** {{ generation_date }}  
**Flow ID:** {{ flow_id }}

## Key Metrics
- **Total Tasks:** {{ total_tasks }}
- **Estimated Hours:** {{ estimated_hours }}
- **Total Cost:** ${{ total_cost }}
- **Quality Score:** {{ quality_score }}%

## Key Decisions
{% for decision in key_decisions %}
1. {{ decision.decision }} ({{ decision.confidence }}% confidence)
   - Rationale: {{ decision.rationale }}
{% endfor %}

## Identified Risks
{% for risk in risks_identified %}
- {{ risk.description }} ({{ risk.severity }})
  - Mitigation: {{ risk.mitigation }}
{% endfor %}

## Recommendations
{% for rec in recommendations %}
- {{ rec }}
{% endfor %}
