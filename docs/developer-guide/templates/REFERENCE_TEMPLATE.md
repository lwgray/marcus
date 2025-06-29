# [Feature/API/Component Name] Reference

> **Type**: API | Configuration | CLI | Component  
> **Version**: [Applicable versions]  
> **Last Updated**: [Date]

## Overview

[Brief description of what this reference covers]

## Synopsis

```
[Usage pattern or syntax]
```

## Description

[Detailed explanation of the feature/API/component]

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `param1` | string | Yes | - | [What it does] |
| `param2` | boolean | No | `false` | [What it does] |
| `param3` | integer | No | `10` | [What it does] |

### Parameter Details

#### `param1`
[Detailed explanation of this parameter, valid values, constraints]

#### `param2`
[Detailed explanation including when to use different values]

## Return Values

### Success Response
```json
{
  "status": "success",
  "data": {
    "field1": "value",
    "field2": 123
  }
}
```

### Error Response
```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message"
  }
}
```

## Examples

### Basic Example
```python
# Simple usage
result = pm_agent.api_call(param1="value")
```

### Advanced Example
```python
# With all parameters
result = pm_agent.api_call(
    param1="value",
    param2=True,
    param3=20
)
```

### Real-World Example
```python
# Practical scenario
try:
    result = pm_agent.api_call(param1="production-task")
    print(f"Success: {result['data']}")
except PMAgentError as e:
    print(f"Error: {e.message}")
```

## Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| `INVALID_PARAM` | Parameter validation failed | Check parameter types and values |
| `NOT_FOUND` | Resource not found | Verify the resource exists |
| `UNAUTHORIZED` | Authentication failed | Check API credentials |

## Notes

- [Important considerations]
- [Performance implications]
- [Security considerations]

## Version History

| Version | Changes |
|---------|---------|
| 1.2.0 | Added `param3` option |
| 1.1.0 | Made `param2` optional |
| 1.0.0 | Initial release |

## See Also

- [Related API](/reference/api/related)
- [Configuration Guide](/reference/configuration/related)
- [How-To Guide](/how-to/using-this-feature)