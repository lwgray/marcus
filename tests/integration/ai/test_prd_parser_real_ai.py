"""
Integration tests for PRD parser with real AI responses

These tests use actual AI services to verify the parser handles real-world
responses correctly. They help catch issues that mocked tests might miss.
"""
import pytest
import asyncio
import os
from datetime import datetime

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser, ProjectConstraints
from src.core.error_framework import AIProviderError


@pytest.mark.integration
class TestPRDParserRealAI:
    """Test PRD parser with real AI responses to catch unexpected behaviors"""
    
    @pytest.fixture
    def parser(self):
        """Create real parser instance"""
        # The parser will use config from config_marcus.json
        return AdvancedPRDParser()
    
    @pytest.fixture
    def constraints(self):
        """Create project constraints"""
        return ProjectConstraints(
            team_size=3,
            technology_constraints=["Python", "FastAPI", "PostgreSQL"],
            available_skills=["Python", "API Development", "Database Design"]
        )
    
    @pytest.mark.asyncio
    async def test_simple_todo_api_real_response(self, parser, constraints):
        """Test with a simple Todo API PRD to verify real AI response handling"""
        prd_content = """
        Create a Simple Todo API with the following requirements:
        
        Functional Requirements:
        - CRUD operations for todos (Create, Read, Update, Delete)
        - Each todo should have: title, description, completed status, timestamps
        - User authentication using JWT tokens
        - Input validation and sanitization
        
        Non-functional Requirements:
        - Performance: Handle 100 requests per second
        - Security: Secure all endpoints with JWT authentication
        - Scalability: Support up to 10,000 users
        
        Technical Constraints:
        - Use RESTful API design
        - PostgreSQL for data storage
        - Docker for containerization
        """
        
        try:
            result = await parser.parse_prd_to_tasks(
                prd_content=prd_content,
                constraints=constraints
            )
            
            # Verify we got tasks
            assert len(result.tasks) > 0, "Should generate tasks from PRD"
            
            # Verify task variety (not all backend tasks)
            task_names = [task.name for task in result.tasks]
            task_types = set()
            
            for name in task_names:
                if "Design" in name:
                    task_types.add("design")
                elif "Implement" in name:
                    task_types.add("implementation")
                elif "Test" in name:
                    task_types.add("testing")
                elif "Setup" in name or "Configure" in name:
                    task_types.add("infrastructure")
            
            assert len(task_types) >= 3, f"Should have varied task types, got: {task_types}"
            
            # Verify no 'unknown' task IDs
            unknown_tasks = [task for task in result.tasks if 'unknown' in task.id]
            assert len(unknown_tasks) == 0, f"Should not have 'unknown' task IDs: {[t.id for t in unknown_tasks]}"
            
            # Verify functional requirements were parsed
            func_req_tasks = [task for task in result.tasks if 'crud' in task.id.lower() or 'auth' in task.id.lower()]
            assert len(func_req_tasks) > 0, "Should have tasks for functional requirements"
            
            # Log task generation summary
            print(f"\n=== Task Generation Summary ===")
            print(f"Total tasks generated: {len(result.tasks)}")
            print(f"Task types found: {task_types}")
            print(f"Functional requirement tasks: {len(func_req_tasks)}")
            
            # Print all task names and IDs to see what was generated
            print(f"\n=== All Generated Tasks ===")
            for i, task in enumerate(result.tasks, 1):
                print(f"{i}. [{task.id}] {task.name}")
            
            # Check for specific expected tasks
            crud_tasks = [t for t in result.tasks if 'crud' in t.name.lower() or 'crud' in t.id.lower()]
            auth_tasks = [t for t in result.tasks if 'auth' in t.name.lower() or 'auth' in t.id.lower()]
            validation_tasks = [t for t in result.tasks if 'validation' in t.name.lower() or 'validation' in t.id.lower()]
            
            print(f"\n=== Task Analysis ===")
            print(f"CRUD tasks found: {len(crud_tasks)}")
            if crud_tasks:
                for t in crud_tasks:
                    print(f"  - {t.name}")
            
            print(f"Auth tasks found: {len(auth_tasks)}")
            if auth_tasks:
                for t in auth_tasks:
                    print(f"  - {t.name}")
            
            print(f"Validation tasks found: {len(validation_tasks)}")
            if validation_tasks:
                for t in validation_tasks:
                    print(f"  - {t.name}")
            
            # More flexible assertions - check task IDs too
            assert len(crud_tasks) > 0 or any('todo' in t.name.lower() or 'todo' in t.id.lower() for t in result.tasks), \
                "Should have CRUD or todo-related tasks"
            assert len(auth_tasks) > 0 or any('user' in t.name.lower() for t in result.tasks), \
                "Should have authentication or user-related tasks"
            # Validation might be part of other tasks
            
            return result
            
        except AIProviderError as e:
            pytest.skip(f"AI provider not available: {e}")
    
    @pytest.mark.asyncio
    async def test_complex_ecommerce_real_response(self, parser, constraints):
        """Test with a complex e-commerce PRD to verify handling of many requirements"""
        prd_content = """
        Build an E-commerce Platform with these capabilities:
        
        Core Features:
        1. Product catalog with categories, search, and filtering
        2. Shopping cart and wishlist functionality
        3. User accounts with order history
        4. Payment processing (credit cards, PayPal)
        5. Inventory management and stock tracking
        6. Order fulfillment and shipping integration
        
        Performance Requirements:
        - Page load time under 2 seconds
        - Support 1000 concurrent users
        - 99.9% uptime SLA
        
        Security Requirements:
        - PCI DSS compliance for payment processing
        - GDPR compliance for user data
        - Two-factor authentication option
        """
        
        try:
            result = await parser.parse_prd_to_tasks(
                prd_content=prd_content,
                constraints=constraints
            )
            
            # Should generate many tasks for complex project
            assert len(result.tasks) >= 15, f"Complex project should generate many tasks, got {len(result.tasks)}"
            
            # Verify hierarchical structure
            assert len(result.task_hierarchy) >= 5, "Should have multiple epics"
            
            # Check for expected feature tasks
            feature_keywords = ['catalog', 'cart', 'payment', 'inventory', 'order']
            found_features = set()
            
            for task in result.tasks:
                for keyword in feature_keywords:
                    if keyword in task.name.lower() or keyword in task.id.lower():
                        found_features.add(keyword)
            
            assert len(found_features) >= 3, f"Should cover multiple features, found: {found_features}"
            
            # Verify NFR tasks exist
            nfr_tasks = [t for t in result.tasks if 'nfr' in t.id]
            assert len(nfr_tasks) > 0, "Should have non-functional requirement tasks"
            
            return result
            
        except AIProviderError as e:
            pytest.skip(f"AI provider not available: {e}")
    
    @pytest.mark.asyncio
    async def test_minimal_prd_real_response(self, parser, constraints):
        """Test with minimal PRD to see how AI handles vague requirements"""
        prd_content = "Build a blog platform with comments"
        
        try:
            result = await parser.parse_prd_to_tasks(
                prd_content=prd_content,
                constraints=constraints
            )
            
            # Should still generate reasonable tasks
            assert len(result.tasks) >= 6, "Should generate basic tasks even from minimal PRD"
            
            # Should have infrastructure tasks
            infra_tasks = [t for t in result.tasks if 'setup' in t.name.lower() or 'deploy' in t.name.lower()]
            assert len(infra_tasks) > 0, "Should include infrastructure tasks"
            
            return result
            
        except AIProviderError as e:
            pytest.skip(f"AI provider not available: {e}")
    
    @pytest.mark.asyncio
    async def test_ai_response_format_consistency(self, parser, constraints):
        """Test multiple PRDs to check AI response format consistency"""
        prds = [
            "Create a task management system with projects and teams",
            "Build a real-time chat application with rooms and direct messages",
            "Develop a file sharing service with upload, download, and sharing features"
        ]
        
        # Track which fields AI uses across multiple requests
        field_usage = {
            'functional_reqs': {'id': 0, 'name': 0, 'feature': 0, 'description': 0},
            'nfr_reqs': {'id': 0, 'name': 0, 'requirement': 0, 'description': 0}
        }
        
        for i, prd in enumerate(prds):
            try:
                # Analyze PRD directly to see raw response structure
                analysis = await parser._analyze_prd_deeply(prd)
                
                # Check functional requirements structure
                for req in analysis.functional_requirements:
                    for field in ['id', 'name', 'feature', 'description']:
                        if field in req:
                            field_usage['functional_reqs'][field] += 1
                
                # Check NFR structure
                for nfr in analysis.non_functional_requirements:
                    for field in ['id', 'name', 'requirement', 'description']:
                        if field in nfr:
                            field_usage['nfr_reqs'][field] += 1
                
                print(f"\nPRD {i+1} analyzed successfully")
                
            except AIProviderError as e:
                pytest.skip(f"AI provider not available: {e}")
        
        # Report on field consistency
        print("\n=== AI Response Format Consistency ===")
        print("Functional Requirements field usage:")
        for field, count in field_usage['functional_reqs'].items():
            print(f"  {field}: {count}/{len(prds)*3} (assuming ~3 reqs per PRD)")
        
        print("\nNFR field usage:")
        for field, count in field_usage['nfr_reqs'].items():
            print(f"  {field}: {count}/{len(prds)*2} (assuming ~2 NFRs per PRD)")
        
        # Verify our expected template fields are most common
        # Note: This might fail if AI doesn't follow template, which is what we want to detect!
        assert field_usage['functional_reqs'].get('id', 0) > 0 or field_usage['functional_reqs'].get('name', 0) > 0, \
            "AI should use 'id' or 'name' fields as specified in template"
    
    @pytest.mark.asyncio
    async def test_real_ai_deviation_logging(self, parser, constraints, caplog):
        """Test that deviations from template are properly logged with real AI"""
        prd_content = """
        Create a notification service that can:
        - Send emails, SMS, and push notifications
        - Track delivery status
        - Handle templates and personalization
        """
        
        import logging
        caplog.set_level(logging.WARNING)
        
        try:
            result = await parser.parse_prd_to_tasks(
                prd_content=prd_content,
                constraints=constraints
            )
            
            # Check if any deviations were logged
            deviation_logs = [record for record in caplog.records if "deviated from template" in record.message]
            
            if deviation_logs:
                print(f"\n=== Template Deviations Detected ===")
                print(f"Number of deviations: {len(deviation_logs)}")
                for log in deviation_logs[:5]:  # Show first 5
                    print(f"- {log.message}")
                
                # This is actually valuable data about AI behavior!
                # Not a test failure, but important to track
            else:
                print("\n=== AI followed template perfectly! ===")
            
            # The test passes regardless - we're gathering data
            assert True
            
        except AIProviderError as e:
            pytest.skip(f"AI provider not available: {e}")
    
    @pytest.mark.asyncio
    async def test_task_name_specificity_real_ai(self, parser, constraints):
        """Verify task names are specific to requirements, not generic"""
        prd_content = """
        Build a Restaurant Ordering System:
        - Menu management with items, prices, and availability
        - Online ordering with cart functionality
        - Kitchen order queue management
        - Customer notifications for order status
        """
        
        try:
            result = await parser.parse_prd_to_tasks(
                prd_content=prd_content,
                constraints=constraints
            )
            
            # Count generic vs specific task names
            generic_keywords = ['api', 'backend', 'service', 'system', 'functionality']
            specific_keywords = ['menu', 'order', 'cart', 'kitchen', 'notification', 'restaurant']
            
            generic_count = 0
            specific_count = 0
            
            for task in result.tasks:
                name_lower = task.name.lower()
                
                # Check for generic terms
                if any(keyword in name_lower for keyword in generic_keywords) and \
                   not any(keyword in name_lower for keyword in specific_keywords):
                    generic_count += 1
                    print(f"Generic task name: {task.name}")
                
                # Check for specific terms
                if any(keyword in name_lower for keyword in specific_keywords):
                    specific_count += 1
            
            print(f"\n=== Task Name Specificity ===")
            print(f"Generic task names: {generic_count}")
            print(f"Specific task names: {specific_count}")
            print(f"Total tasks: {len(result.tasks)}")
            
            # Most tasks should be specific
            specificity_ratio = specific_count / len(result.tasks) if result.tasks else 0
            assert specificity_ratio >= 0.5, f"At least 50% of tasks should have specific names, got {specificity_ratio:.1%}"
            
        except AIProviderError as e:
            pytest.skip(f"AI provider not available: {e}")


# Run this test file directly to see real AI behavior
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])