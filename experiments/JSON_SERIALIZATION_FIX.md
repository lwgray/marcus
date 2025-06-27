# JSON Serialization Fix for Marcus UI

## Problem
The Marcus UI server was experiencing JSON serialization errors when trying to access the `/api/decisions/analytics` endpoint:

```
TypeError: Object of type Decision is not JSON serializable
```

This occurred because the endpoint was trying to directly return `Decision` dataclass objects in the JSON response, which are not natively JSON serializable.

## Solution
Modified the `_decision_analytics_handler` method in `/Users/lwgray/dev/marcus/src/visualization/ui_server.py` to convert Decision objects to dictionaries before returning them.

### Code Changes
```python
# Convert Decision objects to dictionaries
decisions_dict = {}
for decision_id, decision in self.decision_visualizer.decisions.items():
    decisions_dict[decision_id] = {
        'id': decision.id,
        'timestamp': decision.timestamp.isoformat(),
        'decision': decision.decision,
        'rationale': decision.rationale,
        'confidence_score': decision.confidence_score,
        'alternatives': decision.alternatives,
        'decision_factors': decision.decision_factors,
        'outcome': decision.outcome,
        'outcome_timestamp': decision.outcome_timestamp.isoformat() if decision.outcome_timestamp else None
    }
```

## Result
The endpoint now returns proper JSON data:
- ✅ All decision data is properly serialized
- ✅ Timestamps are converted to ISO format strings
- ✅ None values are handled correctly
- ✅ The UI can now fetch and display decision analytics

## Testing
Verified the fix by:
1. Restarting the UI server
2. Testing the endpoint: `curl http://localhost:8080/api/decisions/analytics`
3. Confirming proper JSON output with decision data

The Marcus UI is now fully functional at http://localhost:8080 with the decision analytics working correctly.