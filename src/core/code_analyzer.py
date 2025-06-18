"""
Code Analyzer for GitHub Integration

This module analyzes code changes, PRs, and repository state to provide
context-aware information to workers about implemented features.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import re
import json

from src.core.models import Task, WorkerStatus


class CodeAnalyzer:
    """Analyzes code changes and provides insights for task coordination"""
    
    def __init__(self, mcp_caller=None):
        """
        Initialize the code analyzer
        
        Args:
            mcp_caller: Function to call GitHub MCP tools
        """
        self.mcp_caller = mcp_caller
        self.endpoint_patterns = [
            # FastAPI/Flask style
            r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']\)',
            r'@router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']\)',
            # Express.js style
            r'app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']\)',
            r'router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']\)',
            # Django style
            r'path\(["\']([^"\']+)["\']\s*,',
            # Spring Boot style
            r'@(Get|Post|Put|Delete|Patch)Mapping\(["\']([^"\']+)["\']\)',
        ]
        
    async def analyze_task_completion(
        self, 
        task: Task, 
        worker: WorkerStatus,
        owner: str,
        repo: str
    ) -> Dict[str, Any]:
        """
        Analyze what was accomplished when a task is completed
        
        Args:
            task: The completed task
            worker: The worker who completed it
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Analysis of the completed work
        """
        analysis = {
            "task_id": task.id,
            "task_name": task.name,
            "worker_id": worker.agent_id,
            "findings": {},
            "recommendations": []
        }
        
        # Check for recent commits by the worker
        commits = await self._get_recent_commits(owner, repo, worker.agent_id)
        if commits:
            analysis["findings"]["commits"] = commits
            
        # Check for PRs
        prs = await self._get_worker_prs(owner, repo, worker.agent_id)
        if prs:
            analysis["findings"]["pull_requests"] = prs
            
            # Analyze PR changes for specific implementations
            for pr in prs:
                pr_analysis = await self._analyze_pr_changes(owner, repo, pr["number"])
                if pr_analysis:
                    analysis["findings"]["implementations"] = pr_analysis
                    
        # Generate recommendations based on findings
        analysis["recommendations"] = self._generate_recommendations(
            task, 
            analysis["findings"]
        )
        
        return analysis
        
    async def get_implementation_details(
        self,
        owner: str,
        repo: str,
        feature_type: str
    ) -> Dict[str, Any]:
        """
        Get details about existing implementations
        
        Args:
            owner: Repository owner
            repo: Repository name
            feature_type: Type of feature to look for (e.g., "endpoints", "models")
            
        Returns:
            Details about existing implementations
        """
        details = {
            "feature_type": feature_type,
            "implementations": []
        }
        
        if feature_type == "endpoints":
            details["implementations"] = await self._find_endpoints(owner, repo)
        elif feature_type == "models":
            details["implementations"] = await self._find_models(owner, repo)
        elif feature_type == "schemas":
            details["implementations"] = await self._find_schemas(owner, repo)
            
        return details
        
    async def _get_recent_commits(
        self, 
        owner: str, 
        repo: str, 
        author: str
    ) -> List[Dict[str, Any]]:
        """Get recent commits by a specific author"""
        if not self.mcp_caller:
            return []
            
        try:
            result = await self.mcp_caller('github.list_commits', {
                "owner": owner,
                "repo": repo,
                "perPage": 10
            })
            
            commits = []
            if result.get('commits'):
                for commit in result['commits']:
                    # Check if commit author matches worker
                    if author.lower() in str(commit.get('author', {})).lower():
                        commits.append({
                            "sha": commit.get('sha'),
                            "message": commit.get('commit', {}).get('message', ''),
                            "date": commit.get('commit', {}).get('author', {}).get('date', ''),
                            "files_changed": len(commit.get('files', []))
                        })
                        
            return commits
        except Exception as e:
            print(f"Error getting commits: {e}")
            return []
            
    async def _get_worker_prs(
        self, 
        owner: str, 
        repo: str, 
        author: str
    ) -> List[Dict[str, Any]]:
        """Get PRs created by a worker"""
        if not self.mcp_caller:
            return []
            
        try:
            result = await self.mcp_caller('github.list_pull_requests', {
                "owner": owner,
                "repo": repo,
                "state": "all",
                "perPage": 10
            })
            
            prs = []
            if result.get('pull_requests'):
                for pr in result['pull_requests']:
                    # Check if PR author matches worker
                    if author.lower() in str(pr.get('user', {})).lower():
                        prs.append({
                            "number": pr.get('number'),
                            "title": pr.get('title'),
                            "state": pr.get('state'),
                            "merged": pr.get('merged', False),
                            "branch": pr.get('head', {}).get('ref', ''),
                            "created_at": pr.get('created_at')
                        })
                        
            return prs
        except Exception as e:
            print(f"Error getting PRs: {e}")
            return []
            
    async def _analyze_pr_changes(
        self, 
        owner: str, 
        repo: str, 
        pr_number: int
    ) -> Dict[str, Any]:
        """Analyze changes in a PR to understand implementations"""
        if not self.mcp_caller:
            return {}
            
        try:
            # Get PR files
            result = await self.mcp_caller('github.get_pull_request_files', {
                "owner": owner,
                "repo": repo,
                "pullNumber": pr_number
            })
            
            analysis = {
                "endpoints": [],
                "models": [],
                "configurations": [],
                "tests": []
            }
            
            if result.get('files'):
                for file in result['files']:
                    filename = file.get('filename', '')
                    patch = file.get('patch', '')
                    
                    # Analyze based on file type and changes
                    if self._is_api_file(filename):
                        endpoints = self._extract_endpoints(patch)
                        if endpoints:
                            analysis["endpoints"].extend(endpoints)
                            
                    elif self._is_model_file(filename):
                        models = self._extract_models(patch)
                        if models:
                            analysis["models"].extend(models)
                            
                    elif self._is_config_file(filename):
                        analysis["configurations"].append({
                            "file": filename,
                            "changes": self._summarize_config_changes(patch)
                        })
                        
                    elif self._is_test_file(filename):
                        analysis["tests"].append({
                            "file": filename,
                            "type": "unit" if "unit" in filename else "integration"
                        })
                        
            return analysis
            
        except Exception as e:
            print(f"Error analyzing PR: {e}")
            return {}
            
    async def _find_endpoints(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Find API endpoints in the repository"""
        if not self.mcp_caller:
            return []
            
        try:
            # Search for common API file patterns
            search_queries = [
                f"repo:{owner}/{repo} path:api extension:py",
                f"repo:{owner}/{repo} path:routes extension:js",
                f"repo:{owner}/{repo} path:controllers extension:java"
            ]
            
            endpoints = []
            for query in search_queries:
                result = await self.mcp_caller('github.search_code', {
                    "query": query,
                    "perPage": 20
                })
                
                if result.get('items'):
                    for item in result['items']:
                        # Get file content to extract endpoints
                        file_result = await self.mcp_caller('github.get_file_contents', {
                            "owner": owner,
                            "repo": repo,
                            "path": item.get('path')
                        })
                        
                        if file_result.get('content'):
                            content = self._decode_content(file_result['content'])
                            found_endpoints = self._extract_endpoints(content)
                            endpoints.extend(found_endpoints)
                            
            return endpoints
            
        except Exception as e:
            print(f"Error finding endpoints: {e}")
            return []
            
    def _extract_endpoints(self, content: str) -> List[Dict[str, Any]]:
        """Extract API endpoints from code content"""
        endpoints = []
        
        for pattern in self.endpoint_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple):
                    method = match[0].upper()
                    path = match[1] if len(match) > 1 else match[0]
                else:
                    method = "GET"  # Default
                    path = match
                    
                endpoints.append({
                    "method": method,
                    "path": path,
                    "implementation": self._extract_function_name(content, path)
                })
                
        return endpoints
        
    def _extract_models(self, content: str) -> List[Dict[str, Any]]:
        """Extract data models from code"""
        models = []
        
        # Python/SQLAlchemy models
        python_model_pattern = r'class\s+(\w+)\s*\([^)]*(?:Model|Base|BaseModel)[^)]*\):'
        matches = re.findall(python_model_pattern, content)
        for match in matches:
            models.append({
                "name": match,
                "type": "database_model",
                "language": "python"
            })
            
        # TypeScript/JavaScript interfaces
        ts_interface_pattern = r'(?:export\s+)?interface\s+(\w+)\s*{'
        matches = re.findall(ts_interface_pattern, content)
        for match in matches:
            models.append({
                "name": match,
                "type": "interface",
                "language": "typescript"
            })
            
        return models
        
    def _generate_recommendations(
        self, 
        task: Task, 
        findings: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations for next workers based on findings"""
        recommendations = []
        
        # If endpoints were created
        if findings.get("implementations", {}).get("endpoints"):
            endpoints = findings["implementations"]["endpoints"]
            rec = "The following API endpoints were implemented:\n"
            for ep in endpoints:
                rec += f"  - {ep['method']} {ep['path']}\n"
            recommendations.append(rec)
            
        # If models were created
        if findings.get("implementations", {}).get("models"):
            models = findings["implementations"]["models"]
            rec = "The following data models were created:\n"
            for model in models:
                rec += f"  - {model['name']} ({model['type']})\n"
            recommendations.append(rec)
            
        # If tests were added
        if findings.get("implementations", {}).get("tests"):
            tests = findings["implementations"]["tests"]
            rec = f"Tests were added in {len(tests)} files. Ensure new features include tests."
            recommendations.append(rec)
            
        # Based on task type
        if "api" in task.name.lower() or "endpoint" in task.name.lower():
            recommendations.append(
                "Frontend developers should use the implemented endpoints. "
                "Check the PR for request/response formats."
            )
            
        if "model" in task.name.lower() or "schema" in task.name.lower():
            recommendations.append(
                "Database migrations may be needed. "
                "API developers should use these models for consistency."
            )
            
        return recommendations
        
    def _is_api_file(self, filename: str) -> bool:
        """Check if file is likely an API file"""
        api_indicators = ['api', 'route', 'controller', 'endpoint', 'view']
        return any(indicator in filename.lower() for indicator in api_indicators)
        
    def _is_model_file(self, filename: str) -> bool:
        """Check if file is likely a model file"""
        model_indicators = ['model', 'schema', 'entity', 'domain']
        return any(indicator in filename.lower() for indicator in model_indicators)
        
    def _is_config_file(self, filename: str) -> bool:
        """Check if file is a configuration file"""
        config_extensions = ['.json', '.yaml', '.yml', '.env', '.config']
        return any(filename.endswith(ext) for ext in config_extensions)
        
    def _is_test_file(self, filename: str) -> bool:
        """Check if file is a test file"""
        return 'test' in filename.lower() or 'spec' in filename.lower()
        
    def _extract_function_name(self, content: str, path: str) -> Optional[str]:
        """Try to extract the function name handling an endpoint"""
        # Look for function definition near the path
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if path in line:
                # Check next few lines for function definition
                for j in range(max(0, i-5), min(len(lines), i+5)):
                    func_match = re.search(r'def\s+(\w+)\s*\(', lines[j])
                    if func_match:
                        return func_match.group(1)
        return None
        
    def _decode_content(self, content: str) -> str:
        """Decode base64 content from GitHub API"""
        import base64
        try:
            return base64.b64decode(content).decode('utf-8')
        except:
            return content
            
    def _summarize_config_changes(self, patch: str) -> str:
        """Summarize configuration changes from a patch"""
        added = len(re.findall(r'^\+[^+]', patch, re.MULTILINE))
        removed = len(re.findall(r'^-[^-]', patch, re.MULTILINE))
        return f"{added} additions, {removed} deletions"