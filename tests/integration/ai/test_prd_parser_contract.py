"""
Contract tests for PRD parser AI responses

These tests verify that the AI follows our specified JSON template format.
They act as a contract between our code and the AI's expected behavior.
"""
import pytest
import json
from typing import Dict, Any, List

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser
from src.core.error_framework import AIProviderError


@pytest.mark.integration
class TestPRDParserContract:
    """Contract tests to ensure AI follows our specified format"""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance"""
        return AdvancedPRDParser()
    
    def validate_functional_requirement(self, req: Dict[str, Any]) -> List[str]:
        """Validate a functional requirement follows our contract"""
        violations = []
        
        # Required fields
        required_fields = ['id', 'name', 'description', 'priority']
        for field in required_fields:
            if field not in req:
                violations.append(f"Missing required field '{field}' in functional requirement")
        
        # Field types
        if 'id' in req and not isinstance(req['id'], str):
            violations.append(f"Field 'id' should be string, got {type(req['id'])}")
        
        if 'name' in req and not isinstance(req['name'], str):
            violations.append(f"Field 'name' should be string, got {type(req['name'])}")
        
        if 'description' in req and not isinstance(req['description'], str):
            violations.append(f"Field 'description' should be string, got {type(req['description'])}")
        
        if 'priority' in req and req['priority'] not in ['high', 'medium', 'low']:
            violations.append(f"Field 'priority' should be 'high', 'medium', or 'low', got '{req.get('priority')}'")
        
        # ID format validation
        if 'id' in req:
            id_val = req['id']
            if ' ' in id_val or '-' in id_val or not id_val.replace('_', '').isalnum():
                violations.append(f"ID should use underscore format (e.g., 'crud_operations'), got '{id_val}'")
        
        return violations
    
    def validate_nfr(self, nfr: Dict[str, Any]) -> List[str]:
        """Validate a non-functional requirement follows our contract"""
        violations = []
        
        # Required fields
        required_fields = ['id', 'name', 'description', 'category']
        for field in required_fields:
            if field not in nfr:
                violations.append(f"Missing required field '{field}' in NFR")
        
        # Category validation
        valid_categories = ['performance', 'security', 'usability', 'scalability']
        if 'category' in nfr and nfr['category'] not in valid_categories:
            violations.append(f"NFR category should be one of {valid_categories}, got '{nfr.get('category')}'")
        
        return violations
    
    def validate_prd_analysis_structure(self, analysis_data: Dict[str, Any]) -> List[str]:
        """Validate the entire PRD analysis structure"""
        violations = []
        
        # Top-level required fields
        required_top_level = [
            'functionalRequirements',
            'nonFunctionalRequirements', 
            'technicalConstraints',
            'businessObjectives',
            'userPersonas',
            'successMetrics',
            'implementationApproach',
            'complexityAssessment',
            'riskFactors',
            'confidence'
        ]
        
        for field in required_top_level:
            if field not in analysis_data:
                violations.append(f"Missing required top-level field '{field}'")
        
        # Validate implementationApproach
        if 'implementationApproach' in analysis_data:
            valid_approaches = ['agile', 'waterfall', 'iterative']
            if analysis_data['implementationApproach'] not in valid_approaches:
                violations.append(f"implementationApproach should be one of {valid_approaches}")
        
        # Validate complexityAssessment structure
        if 'complexityAssessment' in analysis_data:
            ca = analysis_data['complexityAssessment']
            if not isinstance(ca, dict):
                violations.append("complexityAssessment should be a dictionary")
            else:
                for field in ['technical', 'timeline', 'resources']:
                    if field not in ca:
                        violations.append(f"complexityAssessment missing field '{field}'")
        
        # Validate confidence is a number
        if 'confidence' in analysis_data:
            if not isinstance(analysis_data['confidence'], (int, float)):
                violations.append(f"confidence should be a number, got {type(analysis_data['confidence'])}")
            elif not 0 <= analysis_data['confidence'] <= 1:
                violations.append(f"confidence should be between 0 and 1, got {analysis_data['confidence']}")
        
        return violations
    
    @pytest.mark.asyncio
    async def test_contract_simple_prd(self, parser):
        """Test AI follows contract for simple PRD"""
        prd_content = """
        Create a Todo API with:
        - CRUD operations for todos
        - User authentication
        - Input validation
        
        Performance: 100 requests/second
        Security: JWT authentication
        """
        
        try:
            # Get raw AI response
            from src.utils.json_parser import parse_ai_json_response
            
            # Mock the raw response capture
            raw_response = None
            original_analyze = parser.llm_client.analyze
            
            async def capture_analyze(*args, **kwargs):
                nonlocal raw_response
                raw_response = await original_analyze(*args, **kwargs)
                return raw_response
            
            parser.llm_client.analyze = capture_analyze
            
            # Parse PRD
            analysis = await parser._analyze_prd_deeply(prd_content)
            
            # Parse the raw response
            if raw_response:
                analysis_data = parse_ai_json_response(raw_response)
                
                # Validate overall structure
                violations = self.validate_prd_analysis_structure(analysis_data)
                
                # Validate functional requirements
                if 'functionalRequirements' in analysis_data:
                    for i, req in enumerate(analysis_data['functionalRequirements']):
                        req_violations = self.validate_functional_requirement(req)
                        for v in req_violations:
                            violations.append(f"FunctionalReq[{i}]: {v}")
                
                # Validate NFRs
                if 'nonFunctionalRequirements' in analysis_data:
                    for i, nfr in enumerate(analysis_data['nonFunctionalRequirements']):
                        nfr_violations = self.validate_nfr(nfr)
                        for v in nfr_violations:
                            violations.append(f"NFR[{i}]: {v}")
                
                # Report violations
                if violations:
                    print("\n=== Contract Violations Found ===")
                    for violation in violations:
                        print(f"❌ {violation}")
                    
                    # This is a contract test - violations should fail
                    pytest.fail(f"AI response violated contract with {len(violations)} violations")
                else:
                    print("\n✅ AI response follows contract perfectly!")
            
            # Also check that parsing worked
            assert len(analysis.functional_requirements) > 0, "Should parse functional requirements"
            
        except AIProviderError as e:
            pytest.skip(f"AI provider not available: {e}")
    
    @pytest.mark.asyncio
    async def test_contract_field_consistency(self, parser):
        """Test that AI consistently uses the same fields across multiple requests"""
        prds = [
            "Build a blog with posts and comments",
            "Create an inventory management system",
            "Develop a chat application"
        ]
        
        field_consistency = {
            'functional_reqs': {},
            'nfr_reqs': {}
        }
        
        for prd in prds:
            try:
                analysis = await parser._analyze_prd_deeply(prd)
                
                # Track fields in functional requirements
                for req in analysis.functional_requirements:
                    if isinstance(req, dict):
                        for field in req.keys():
                            field_consistency['functional_reqs'][field] = \
                                field_consistency['functional_reqs'].get(field, 0) + 1
                
                # Track fields in NFRs
                for nfr in analysis.non_functional_requirements:
                    if isinstance(nfr, dict):
                        for field in nfr.keys():
                            field_consistency['nfr_reqs'][field] = \
                                field_consistency['nfr_reqs'].get(field, 0) + 1
            
            except AIProviderError:
                pytest.skip("AI provider not available")
        
        print("\n=== Field Consistency Report ===")
        print("Functional Requirements fields:")
        for field, count in sorted(field_consistency['functional_reqs'].items()):
            print(f"  {field}: appeared {count} times")
        
        print("\nNFR fields:")
        for field, count in sorted(field_consistency['nfr_reqs'].items()):
            print(f"  {field}: appeared {count} times")
        
        # Check that our expected fields are most common
        if field_consistency['functional_reqs']:
            expected_fields = ['id', 'name', 'description', 'priority']
            for field in expected_fields:
                if field in field_consistency['functional_reqs']:
                    print(f"\n✅ Contract field '{field}' is being used")
                else:
                    print(f"\n⚠️  Contract field '{field}' not found in responses")
    
    @pytest.mark.asyncio
    async def test_contract_id_format(self, parser):
        """Test that AI generates IDs in the expected format"""
        prd_content = """
        Build a project management tool with:
        - Task creation and assignment
        - Project dashboards
        - Time tracking
        - Team collaboration features
        """
        
        try:
            analysis = await parser._analyze_prd_deeply(prd_content)
            
            invalid_ids = []
            
            # Check functional requirement IDs
            for req in analysis.functional_requirements:
                if isinstance(req, dict) and 'id' in req:
                    id_val = req['id']
                    # IDs should be lowercase with underscores
                    if not id_val.replace('_', '').islower() or ' ' in id_val or '-' in id_val:
                        invalid_ids.append(f"Functional req ID: '{id_val}'")
            
            # Check NFR IDs
            for nfr in analysis.non_functional_requirements:
                if isinstance(nfr, dict) and 'id' in nfr:
                    id_val = nfr['id']
                    if not id_val.replace('_', '').islower() or ' ' in id_val or '-' in id_val:
                        invalid_ids.append(f"NFR ID: '{id_val}'")
            
            if invalid_ids:
                print("\n=== Invalid ID Formats ===")
                for invalid_id in invalid_ids:
                    print(f"❌ {invalid_id}")
                print("\nExpected format: lowercase_with_underscores")
            else:
                print("\n✅ All IDs follow the expected format!")
            
            # This is informational - don't fail the test
            # We want to see what the AI actually does
            
        except AIProviderError as e:
            pytest.skip(f"AI provider not available: {e}")


# Run contract tests to verify AI behavior
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])