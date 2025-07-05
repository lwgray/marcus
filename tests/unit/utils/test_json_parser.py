"""
Unit tests for JSON parser utility
"""

import pytest
import json
from src.utils.json_parser import (
    extract_json_from_response,
    parse_json_response,
    clean_json_response,
    parse_ai_json_response,
    validate_json_structure
)


class TestExtractJsonFromResponse:
    """Test JSON extraction from various response formats"""
    
    def test_extract_plain_json_object(self):
        """Test extraction of plain JSON object"""
        response = '{"key": "value", "number": 123}'
        result = extract_json_from_response(response)
        assert result == response
    
    def test_extract_plain_json_array(self):
        """Test extraction of plain JSON array"""
        response = '[1, 2, 3, {"key": "value"}]'
        result = extract_json_from_response(response)
        assert result == response
    
    def test_extract_from_markdown_code_block(self):
        """Test extraction from markdown code block with json language"""
        response = '```json\n{"key": "value", "nested": {"item": 1}}\n```'
        result = extract_json_from_response(response)
        assert result == '{"key": "value", "nested": {"item": 1}}'
    
    def test_extract_from_plain_code_block(self):
        """Test extraction from plain markdown code block"""
        response = '```\n{"key": "value"}\n```'
        result = extract_json_from_response(response)
        assert result == '{"key": "value"}'
    
    def test_extract_from_text_with_json(self):
        """Test extraction when JSON is embedded in text"""
        response = 'Here is the response: {"status": "success", "data": [1, 2, 3]}'
        result = extract_json_from_response(response)
        assert result == '{"status": "success", "data": [1, 2, 3]}'
    
    def test_extract_nested_json(self):
        """Test extraction of deeply nested JSON"""
        response = '{"a": {"b": {"c": [1, 2, {"d": "e"}]}}}'
        result = extract_json_from_response(response)
        assert result == response
    
    def test_empty_response_raises_error(self):
        """Test that empty response raises ValueError"""
        with pytest.raises(ValueError, match="Empty response"):
            extract_json_from_response("")
    
    def test_no_json_raises_error(self):
        """Test that response with no JSON raises ValueError"""
        with pytest.raises(ValueError, match="No JSON structure"):
            extract_json_from_response("This is just plain text")


class TestParseJsonResponse:
    """Test JSON parsing with fallback options"""
    
    def test_parse_valid_json(self):
        """Test parsing valid JSON"""
        response = '{"key": "value", "number": 123}'
        result = parse_json_response(response)
        assert result == {"key": "value", "number": 123}
    
    def test_parse_markdown_wrapped_json(self):
        """Test parsing JSON wrapped in markdown"""
        response = '```json\n{"success": true, "items": [1, 2, 3]}\n```'
        result = parse_json_response(response)
        assert result == {"success": True, "items": [1, 2, 3]}
    
    def test_parse_with_default_on_error(self):
        """Test that default is returned on parse error"""
        response = "Invalid JSON"
        default = {"error": "parse_failed"}
        result = parse_json_response(response, default=default)
        assert result == default
    
    def test_parse_raises_without_default(self):
        """Test that exception is raised when no default provided"""
        response = "Invalid JSON"
        with pytest.raises(ValueError):
            parse_json_response(response)


class TestCleanJsonResponse:
    """Test JSON response cleaning"""
    
    def test_clean_markdown_wrapper(self):
        """Test cleaning markdown wrapper"""
        response = '```json\n{"key": "value"}\n```'
        result = clean_json_response(response)
        assert result == '{"key": "value"}'
    
    def test_clean_with_prefix(self):
        """Test cleaning common LLM prefixes"""
        response = 'Here is the JSON response: {"status": "ok"}'
        result = clean_json_response(response)
        assert result == '{"status": "ok"}'
    
    def test_clean_with_suffix(self):
        """Test cleaning trailing explanations"""
        response = '{"data": [1, 2, 3]} This represents the data array.'
        result = clean_json_response(response)
        assert result == '{"data": [1, 2, 3]}'
    
    def test_clean_complex_json(self):
        """Test cleaning doesn't break valid complex JSON"""
        response = '{"a": {"b": [1, 2, {"c": "d"}]}, "e": "f"}'
        result = clean_json_response(response)
        assert result == response


class TestValidateJsonStructure:
    """Test JSON structure validation"""
    
    def test_validate_dict_with_required_fields(self):
        """Test validation of dict with required fields"""
        data = {"name": "test", "value": 123, "active": True}
        assert validate_json_structure(data, ["name", "value"]) is True
    
    def test_validate_dict_missing_fields(self):
        """Test validation fails when required fields missing"""
        data = {"name": "test"}
        assert validate_json_structure(data, ["name", "value"]) is False
    
    def test_validate_without_requirements(self):
        """Test validation always passes without requirements"""
        assert validate_json_structure({"any": "data"}) is True
        assert validate_json_structure([1, 2, 3]) is True
        assert validate_json_structure("string") is True


class TestParseAiJsonResponse:
    """Test AI-specific JSON response parsing"""
    
    def test_parse_ai_response_with_markdown(self):
        """Test parsing typical AI response with markdown"""
        response = '''```json
{
    "functional_requirements": ["Feature 1", "Feature 2"],
    "technical_constraints": ["Constraint 1"],
    "business_objectives": ["Objective 1"]
}
```'''
        result = parse_ai_json_response(response)
        assert "functional_requirements" in result
        assert len(result["functional_requirements"]) == 2
    
    def test_parse_ai_response_with_validation(self):
        """Test parsing with field validation"""
        response = '{"name": "test", "type": "feature"}'
        result = parse_ai_json_response(response, required_fields=["name", "type"])
        assert result["name"] == "test"
        assert result["type"] == "feature"
    
    def test_parse_ai_response_validation_fails(self):
        """Test that validation error is raised for missing fields"""
        response = '{"name": "test"}'
        with pytest.raises(ValueError, match="Missing required fields: type"):
            parse_ai_json_response(response, required_fields=["name", "type"])
    
    def test_parse_ai_response_not_dict(self):
        """Test error when expecting dict but got array"""
        response = '[1, 2, 3]'
        with pytest.raises(ValueError, match="Expected JSON object"):
            parse_ai_json_response(response, required_fields=["field"])
    
    def test_parse_real_ai_response(self):
        """Test parsing a real-world AI response"""
        response = '''Here is the analysis:

```json
{
    "functionalRequirements": [
        {
            "id": "req_1",
            "description": "User authentication system"
        }
    ],
    "confidence": 0.95
}
```

This analysis shows the requirements extracted from the document.'''
        
        result = parse_ai_json_response(response)
        assert "functionalRequirements" in result
        assert result["confidence"] == 0.95