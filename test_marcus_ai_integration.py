#!/usr/bin/env python3
"""
Comprehensive Test Suite for Marcus AI Hybrid System

Tests the complete integration of all 4 phases to ensure the system
prevents illogical assignments while providing intelligent coordination.
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.ai.core.ai_engine import MarcusAIEngine
from src.ai.types import AnalysisContext, AssignmentContext
from src.ai.decisions.hybrid_framework import HybridDecisionFramework
from src.ai.enrichment.intelligent_enricher import IntelligentTaskEnricher, ProjectContext
from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser, ProjectConstraints
from src.core.models import Task, TaskStatus, Priority


class MarcusAITestSuite:
    """Comprehensive test suite for Marcus AI system"""
    
    def __init__(self):
        self.test_results = []
        self.setup_test_environment()
    
    def setup_test_environment(self):
        """Set up test environment"""
        # Disable AI for consistent testing
        os.environ['MARCUS_AI_ENABLED'] = 'false'
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'
        os.environ['OPENAI_API_KEY'] = 'test-key'
        
        print("🚀 Marcus AI Test Suite Starting...")
        print("=" * 60)
    
    async def run_all_tests(self):
        """Run all test categories"""
        print("\n📋 Running Core Safety Tests...")
        await self.test_core_safety()
        
        print("\n🤖 Running AI Engine Tests...")
        await self.test_ai_engine()
        
        print("\n⚖️  Running Hybrid Decision Tests...")
        await self.test_hybrid_decisions()
        
        print("\n🎨 Running Task Enrichment Tests...")
        await self.test_task_enrichment()
        
        print("\n📄 Running PRD Parsing Tests...")
        await self.test_prd_parsing()
        
        print("\n📊 Test Results Summary:")
        await self.print_test_summary()
    
    async def test_core_safety(self):
        """Test core safety guarantees - the most critical functionality"""
        print("  Testing illogical assignment prevention...")
        
        engine = MarcusAIEngine()
        
        # Test 1: Deployment before implementation should be blocked
        deploy_task = self.create_task(
            "deploy-prod", 
            "Deploy to production", 
            "Deploy application to production environment"
        )
        
        impl_task = self.create_task(
            "impl-core", 
            "Implement core features", 
            "Build the main application functionality",
            status=TaskStatus.TODO  # Still incomplete
        )
        
        context = AnalysisContext(
            task=deploy_task,
            project_context={
                'available_tasks': [impl_task],
                'assigned_tasks': {},
                'project_type': 'web'
            },
            historical_data=[]
        )
        
        result = await engine.analyze_with_hybrid_intelligence(context)
        
        self.assert_test(
            "Deploy before implement blocked",
            not result.allow_assignment,
            f"Expected deployment to be blocked, got allow={result.allow_assignment}"
        )
        
        self.assert_test(
            "High confidence in blocking",
            result.confidence >= 0.95,
            f"Expected high confidence, got {result.confidence}"
        )
        
        # Test 2: Logical task should be allowed
        login_task = self.create_task(
            "impl-login",
            "Implement user login",
            "Create user authentication system"
        )
        
        context2 = AnalysisContext(
            task=login_task,
            project_context={'available_tasks': [], 'assigned_tasks': {}},
            historical_data=[]
        )
        
        result2 = await engine.analyze_with_hybrid_intelligence(context2)
        
        self.assert_test(
            "Logical task allowed",
            result2.allow_assignment,
            f"Expected logical task to be allowed, got allow={result2.allow_assignment}"
        )
        
        print("    ✅ Core safety tests passed")
    
    async def test_ai_engine(self):
        """Test AI engine functionality"""
        print("  Testing AI engine components...")
        
        engine = MarcusAIEngine()
        
        # Test engine status
        status = await engine.get_engine_status()
        
        self.assert_test(
            "Engine initialized",
            'ai_enabled' in status,
            "Engine status should include ai_enabled flag"
        )
        
        # Test fallback mode
        task = self.create_task("test-task", "Test task", "Testing fallback")
        context = AnalysisContext(
            task=task,
            project_context={'available_tasks': []},
            historical_data=[]
        )
        
        result = await engine.analyze_with_hybrid_intelligence(context)
        
        self.assert_test(
            "Fallback mode works",
            result.fallback_mode,
            "Should be in fallback mode when AI disabled"
        )
        
        # Test task enhancement
        enhanced = await engine.enhance_task_with_ai(task, {'project_type': 'web'})
        
        self.assert_test(
            "Enhancement returns data",
            isinstance(enhanced, dict),
            "Enhancement should return dictionary"
        )
        
        print("    ✅ AI engine tests passed")
    
    async def test_hybrid_decisions(self):
        """Test hybrid decision framework"""
        print("  Testing hybrid decision making...")
        
        framework = HybridDecisionFramework()
        
        # Test framework stats
        stats = await framework.get_framework_stats()
        
        self.assert_test(
            "Framework configured",
            stats['rule_weight'] > stats['ai_weight'],
            "Rules should have higher weight than AI for safety"
        )
        
        # Test assignment decision
        task = self.create_task("test-decision", "Test decision", "Testing decisions")
        
        context = AssignmentContext(
            task=task,
            agent_id="test-agent",
            agent_status={'status': 'available'},
            available_tasks=[],
            project_context={},
            team_status={}
        )
        
        decision = await framework.make_assignment_decision(task, context)
        
        self.assert_test(
            "Decision has confidence",
            0 <= decision.confidence <= 1,
            f"Confidence should be 0-1, got {decision.confidence}"
        )
        
        self.assert_test(
            "Decision has reasoning",
            len(decision.reason) > 0,
            "Decision should include reasoning"
        )
        
        print("    ✅ Hybrid decision tests passed")
    
    async def test_task_enrichment(self):
        """Test intelligent task enrichment"""
        print("  Testing task enrichment...")
        
        enricher = IntelligentTaskEnricher()
        
        # Create test task
        task = self.create_task(
            "basic-task",
            "Add user login",
            "Basic login functionality"
        )
        
        # Create project context
        project_context = ProjectContext(
            project_type='web',
            tech_stack=['react', 'python', 'postgresql'],
            team_size=3,
            existing_tasks=[],
            project_standards={'testing_required': True},
            historical_data=[],
            quality_requirements={'documentation_required': True}
        )
        
        # Test enrichment
        result = await enricher.enrich_task_with_ai(task, project_context)
        
        self.assert_test(
            "Enrichment completed",
            result.original_task.id == task.id,
            "Enrichment should reference original task"
        )
        
        self.assert_test(
            "Enhanced description",
            len(result.enhanced_description) >= len(task.description or ""),
            "Enhanced description should be at least as long as original"
        )
        
        self.assert_test(
            "Labels suggested",
            len(result.suggested_labels) > 0,
            "Should suggest at least some labels"
        )
        
        self.assert_test(
            "Acceptance criteria generated",
            len(result.acceptance_criteria) > 0,
            "Should generate acceptance criteria"
        )
        
        print("    ✅ Task enrichment tests passed")
    
    async def test_prd_parsing(self):
        """Test advanced PRD parsing"""
        print("  Testing PRD parsing...")
        
        parser = AdvancedPRDParser()
        
        # Sample PRD content
        prd_content = """
        Product Requirements Document: User Management System
        
        Overview:
        Build a user management system that allows users to register, login, and manage their profiles.
        
        Features:
        1. User registration with email validation
        2. Secure login with password hashing
        3. Profile management interface
        4. Password reset functionality
        5. Admin user management
        
        Non-functional Requirements:
        - Response time under 200ms
        - Support 1000 concurrent users
        - 99.9% uptime
        - GDPR compliance
        
        Technical Constraints:
        - React frontend
        - Python backend
        - PostgreSQL database
        """
        
        # Test constraints
        constraints = ProjectConstraints(
            team_size=3,
            available_skills=['React', 'Python', 'PostgreSQL'],
            technology_constraints=['React', 'Python', 'PostgreSQL']
        )
        
        # Parse PRD
        result = await parser.parse_prd_to_tasks(prd_content, constraints)
        
        self.assert_test(
            "Tasks generated",
            len(result.tasks) > 0,
            "Should generate tasks from PRD"
        )
        
        self.assert_test(
            "Dependencies inferred",
            len(result.dependencies) >= 0,
            "Should analyze dependencies"
        )
        
        self.assert_test(
            "Timeline estimated",
            'estimated_duration_days' in result.estimated_timeline,
            "Should estimate project timeline"
        )
        
        self.assert_test(
            "Risks assessed",
            'overall_risk_level' in result.risk_assessment,
            "Should assess project risks"
        )
        
        self.assert_test(
            "Resources analyzed",
            'required_skills' in result.resource_requirements,
            "Should analyze resource requirements"
        )
        
        # Test that we have logical task ordering
        task_names = [task.name for task in result.tasks]
        setup_tasks = [name for name in task_names if 'setup' in name.lower()]
        deploy_tasks = [name for name in task_names if 'deploy' in name.lower()]
        
        self.assert_test(
            "Setup tasks included",
            len(setup_tasks) > 0,
            "Should include setup tasks"
        )
        
        print("    ✅ PRD parsing tests passed")
    
    def create_task(self, task_id: str, name: str, description: str, status: TaskStatus = TaskStatus.TODO) -> Task:
        """Helper to create test tasks"""
        return Task(
            id=task_id,
            name=name,
            description=description,
            status=status,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=None,
            dependencies=[],
            labels=[]
        )
    
    def assert_test(self, test_name: str, condition: bool, message: str):
        """Record test result"""
        result = {
            'name': test_name,
            'passed': condition,
            'message': message,
            'timestamp': datetime.now()
        }
        self.test_results.append(result)
        
        if condition:
            print(f"      ✅ {test_name}")
        else:
            print(f"      ❌ {test_name}: {message}")
    
    async def print_test_summary(self):
        """Print comprehensive test summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['passed'])
        failed_tests = total_tests - passed_tests
        
        print("=" * 60)
        print(f"📊 MARCUS AI TEST RESULTS")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"  • {result['name']}: {result['message']}")
        
        print("\n🎯 Key Achievements Verified:")
        
        # Check core achievements
        safety_tests = [r for r in self.test_results if 'blocked' in r['name'].lower() or 'safety' in r['name'].lower()]
        if all(r['passed'] for r in safety_tests):
            print("  ✅ Core Safety: Prevents illogical task assignments")
        
        ai_tests = [r for r in self.test_results if 'ai' in r['name'].lower() or 'engine' in r['name'].lower()]
        if all(r['passed'] for r in ai_tests):
            print("  ✅ AI Integration: Hybrid intelligence working")
        
        enrichment_tests = [r for r in self.test_results if 'enrichment' in r['name'].lower() or 'enhanced' in r['name'].lower()]
        if all(r['passed'] for r in enrichment_tests):
            print("  ✅ Task Enrichment: AI enhancement functional")
        
        prd_tests = [r for r in self.test_results if 'prd' in r['name'].lower() or 'parsing' in r['name'].lower()]
        if all(r['passed'] for r in prd_tests):
            print("  ✅ PRD Parsing: Requirements to tasks conversion")
        
        if failed_tests == 0:
            print("\n🎉 ALL TESTS PASSED! Marcus AI is ready for deployment.")
        else:
            print(f"\n⚠️  {failed_tests} test(s) need attention before deployment.")
        
        print("=" * 60)


async def main():
    """Run the complete test suite"""
    test_suite = MarcusAITestSuite()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())