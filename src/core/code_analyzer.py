"""
Code Analyzer for GitHub Integration

This module analyzes code changes, PRs, and repository state to provide
context-aware information to workers about implemented features.
"""

import json
import re
import sys
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from src.core.models import Task, WorkerStatus


class CodeAnalyzer:
    """
    Analyzes code changes and provides insights for task coordination.

    This class provides functionality to analyze GitHub repositories, PRs,
    and code changes to help coordinate tasks between workers by understanding
    what features have been implemented.

    Attributes
    ----------
    mcp_caller : Optional[callable]
        Function to call GitHub MCP tools for API interactions
    endpoint_patterns : List[str]
        Regular expression patterns for detecting API endpoints

    Examples
    --------
    >>> analyzer = CodeAnalyzer(mcp_caller=github_client)
    >>> details = await analyzer.get_implementation_details(
    ...     "owner", "repo", "endpoints"
    ... )
    """

    def __init__(self, mcp_caller: Optional[Callable[..., Any]] = None) -> None:
        """
        Initialize the code analyzer.

        Parameters
        ----------
        mcp_caller : Optional[callable], default=None
            Function to call GitHub MCP tools. Should accept tool name
            and parameters dict.
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
        self, task: Task, worker: WorkerStatus, owner: str, repo: str
    ) -> Dict[str, Any]:
        """
        Analyze what was accomplished when a task is completed.

        Examines commits, PRs, and code changes to understand what was
        implemented and generate recommendations for subsequent workers.

        Parameters
        ----------
        task : Task
            The completed task to analyze
        worker : WorkerStatus
            The worker who completed the task
        owner : str
            GitHub repository owner username or organization
        repo : str
            GitHub repository name

        Returns
        -------
        Dict[str, Any]
            Analysis containing:
            - task_id: ID of the analyzed task
            - task_name: Name of the task
            - worker_id: ID of the worker
            - findings: Dict with commits, PRs, and implementations
            - recommendations: List of recommendations for next workers

        Examples
        --------
        >>> analysis = await analyzer.analyze_task_completion(
        ...     task, worker, "myorg", "myrepo"
        ... )
        >>> print(analysis["recommendations"])
        """
        analysis: Dict[str, Any] = {
            "task_id": task.id,
            "task_name": task.name,
            "worker_id": worker.worker_id,
            "findings": {},
            "recommendations": [],
        }

        # Check for recent commits by the worker
        commits = await self._get_recent_commits(owner, repo, worker.worker_id)
        if commits:
            analysis["findings"]["commits"] = commits

        # Check for PRs
        prs = await self._get_worker_prs(owner, repo, worker.worker_id)
        if prs:
            analysis["findings"]["pull_requests"] = prs

            # Analyze PR changes for specific implementations
            for pr in prs:
                pr_analysis = await self._analyze_pr_changes(owner, repo, pr["number"])
                if pr_analysis:
                    analysis["findings"]["implementations"] = pr_analysis

        # Generate recommendations based on findings
        analysis["recommendations"] = self._generate_recommendations(
            task, analysis["findings"]
        )

        return analysis

    async def get_implementation_details(
        self, owner: str, repo: str, feature_type: str
    ) -> Dict[str, Any]:
        """
        Get details about existing implementations in the repository.

        Searches for and analyzes specific types of implementations
        to help workers understand the current codebase state.

        Parameters
        ----------
        owner : str
            GitHub repository owner
        repo : str
            GitHub repository name
        feature_type : str
            Type of feature to search for. Supported values:
            - "endpoints": API endpoints
            - "models": Data models/schemas
            - "schemas": Database schemas

        Returns
        -------
        Dict[str, Any]
            Dictionary containing:
            - feature_type: The requested feature type
            - implementations: List of found implementations

        Examples
        --------
        >>> details = await analyzer.get_implementation_details(
        ...     "owner", "repo", "endpoints"
        ... )
        >>> for endpoint in details["implementations"]:
        ...     print(f"{endpoint['method']} {endpoint['path']}")
        """
        details: Dict[str, Any] = {"feature_type": feature_type, "implementations": []}

        if feature_type == "endpoints":
            details["implementations"] = await self._find_endpoints(owner, repo)
        elif feature_type == "models":
            details["implementations"] = await self._find_models(owner, repo)
        elif feature_type == "schemas":
            details["implementations"] = await self._find_schemas(owner, repo)

        return details

    async def _get_recent_commits(
        self, owner: str, repo: str, author: str
    ) -> List[Dict[str, Any]]:
        """
        Get recent commits by a specific author.

        Parameters
        ----------
        owner : str
            Repository owner
        repo : str
            Repository name
        author : str
            Author name to filter commits

        Returns
        -------
        List[Dict[str, Any]]
            List of commit dictionaries containing:
            - sha: Commit SHA
            - message: Commit message
            - date: Commit date
            - files_changed: Number of files changed
        """
        if not self.mcp_caller:
            return []

        try:
            result = await self.mcp_caller(
                "github.list_commits", {"owner": owner, "repo": repo, "perPage": 10}
            )

            commits = []
            if result.get("commits"):
                for commit in result["commits"]:
                    # Check if commit author matches worker
                    if author.lower() in str(commit.get("author", {})).lower():
                        commits.append(
                            {
                                "sha": commit.get("sha"),
                                "message": commit.get("commit", {}).get("message", ""),
                                "date": commit.get("commit", {})
                                .get("author", {})
                                .get("date", ""),
                                "files_changed": len(commit.get("files", [])),
                            }
                        )

            return commits
        except Exception as e:
            print(f"Error getting commits: {e}", file=sys.stderr)
            return []

    async def _get_worker_prs(
        self, owner: str, repo: str, author: str
    ) -> List[Dict[str, Any]]:
        """
        Get pull requests created by a specific worker.

        Parameters
        ----------
        owner : str
            Repository owner
        repo : str
            Repository name
        author : str
            PR author name to filter

        Returns
        -------
        List[Dict[str, Any]]
            List of PR dictionaries containing:
            - number: PR number
            - title: PR title
            - state: PR state (open/closed)
            - merged: Whether PR was merged
            - branch: Source branch name
            - created_at: Creation timestamp
        """
        if not self.mcp_caller:
            return []

        try:
            result = await self.mcp_caller(
                "github.list_pull_requests",
                {"owner": owner, "repo": repo, "state": "all", "perPage": 10},
            )

            prs = []
            if result.get("pull_requests"):
                for pr in result["pull_requests"]:
                    # Check if PR author matches worker
                    if author.lower() in str(pr.get("user", {})).lower():
                        prs.append(
                            {
                                "number": pr.get("number"),
                                "title": pr.get("title"),
                                "state": pr.get("state"),
                                "merged": pr.get("merged", False),
                                "branch": pr.get("head", {}).get("ref", ""),
                                "created_at": pr.get("created_at"),
                            }
                        )

            return prs
        except Exception as e:
            print(f"Error getting PRs: {e}", file=sys.stderr)
            return []

    async def _analyze_pr_changes(
        self, owner: str, repo: str, pr_number: int
    ) -> Dict[str, Any]:
        """
        Analyze changes in a PR to understand implementations.

        Examines files changed in a PR to extract information about
        endpoints, models, configurations, and tests that were added.

        Parameters
        ----------
        owner : str
            Repository owner
        repo : str
            Repository name
        pr_number : int
            Pull request number to analyze

        Returns
        -------
        Dict[str, Any]
            Analysis results containing:
            - endpoints: List of API endpoints found
            - models: List of data models found
            - configurations: List of config changes
            - tests: List of test files added
        """
        if not self.mcp_caller:
            return {}

        try:
            # Get PR files
            result = await self.mcp_caller(
                "github.get_pull_request_files",
                {"owner": owner, "repo": repo, "pullNumber": pr_number},
            )

            analysis: Dict[str, Any] = {
                "endpoints": [],
                "models": [],
                "configurations": [],
                "tests": [],
            }

            if result.get("files"):
                for file in result["files"]:
                    filename = file.get("filename", "")
                    patch = file.get("patch", "")

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
                        analysis["configurations"].append(
                            {
                                "file": filename,
                                "changes": self._summarize_config_changes(patch),
                            }
                        )

                    elif self._is_test_file(filename):
                        analysis["tests"].append(
                            {
                                "file": filename,
                                "type": "unit" if "unit" in filename else "integration",
                            }
                        )

            return analysis

        except Exception as e:
            print(f"Error analyzing PR: {e}", file=sys.stderr)
            return {}

    async def _find_endpoints(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """
        Find API endpoints in the repository.

        Searches common API file patterns and extracts endpoint definitions
        using regex patterns.

        Parameters
        ----------
        owner : str
            Repository owner
        repo : str
            Repository name

        Returns
        -------
        List[Dict[str, Any]]
            List of endpoint dictionaries with method, path, and implementation
        """
        if not self.mcp_caller:
            return []

        try:
            # Search for common API file patterns
            search_queries = [
                f"repo:{owner}/{repo} path:api extension:py",
                f"repo:{owner}/{repo} path:routes extension:js",
                f"repo:{owner}/{repo} path:controllers extension:java",
            ]

            endpoints = []
            for query in search_queries:
                result = await self.mcp_caller(
                    "github.search_code", {"query": query, "perPage": 20}
                )

                if result.get("items"):
                    for item in result["items"]:
                        # Get file content to extract endpoints
                        file_result = await self.mcp_caller(
                            "github.get_file_contents",
                            {"owner": owner, "repo": repo, "path": item.get("path")},
                        )

                        if file_result.get("content"):
                            content = self._decode_content(file_result["content"])
                            found_endpoints = self._extract_endpoints(content)
                            endpoints.extend(found_endpoints)

            return endpoints

        except Exception as e:
            print(f"Error finding endpoints: {e}", file=sys.stderr)
            return []

    def _extract_endpoints(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract API endpoints from code content.

        Uses regex patterns to find endpoint definitions in various
        web framework formats.

        Parameters
        ----------
        content : str
            Source code content to analyze

        Returns
        -------
        List[Dict[str, Any]]
            List of endpoints with:
            - method: HTTP method (GET, POST, etc.)
            - path: Endpoint path
            - implementation: Function name if found
        """
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

                endpoints.append(
                    {
                        "method": method,
                        "path": path,
                        "implementation": self._extract_function_name(content, path),
                    }
                )

        return endpoints

    def _extract_models(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract data models from code.

        Identifies database models, interfaces, and schema definitions
        in Python and TypeScript/JavaScript code.

        Parameters
        ----------
        content : str
            Source code content to analyze

        Returns
        -------
        List[Dict[str, Any]]
            List of models with:
            - name: Model/interface name
            - type: Type of model (database_model, interface)
            - language: Programming language
        """
        models = []

        # Python/SQLAlchemy models
        python_model_pattern = (
            r"class\s+(\w+)\s*\([^)]*(?:Model|Base|BaseModel)[^)]*\):"
        )
        matches = re.findall(python_model_pattern, content)
        for match in matches:
            models.append(
                {"name": match, "type": "database_model", "language": "python"}
            )

        # TypeScript/JavaScript interfaces
        ts_interface_pattern = r"(?:export\s+)?interface\s+(\w+)\s*{"
        matches = re.findall(ts_interface_pattern, content)
        for match in matches:
            models.append(
                {"name": match, "type": "interface", "language": "typescript"}
            )

        return models

    def _generate_recommendations(
        self, task: Task, findings: Dict[str, Any]
    ) -> List[str]:
        """
        Generate recommendations for next workers based on findings.

        Creates actionable recommendations based on what was implemented
        to help subsequent workers understand dependencies.

        Parameters
        ----------
        task : Task
            The completed task
        findings : Dict[str, Any]
            Analysis findings from commits and PRs

        Returns
        -------
        List[str]
            List of recommendation strings for next workers
        """
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
        """
        Check if file is likely an API file.

        Parameters
        ----------
        filename : str
            File path to check

        Returns
        -------
        bool
            True if filename contains API-related keywords
        """
        api_indicators = ["api", "route", "controller", "endpoint", "view"]
        return any(indicator in filename.lower() for indicator in api_indicators)

    def _is_model_file(self, filename: str) -> bool:
        """
        Check if file is likely a model file.

        Parameters
        ----------
        filename : str
            File path to check

        Returns
        -------
        bool
            True if filename contains model-related keywords
        """
        model_indicators = ["model", "schema", "entity", "domain"]
        return any(indicator in filename.lower() for indicator in model_indicators)

    def _is_config_file(self, filename: str) -> bool:
        """
        Check if file is a configuration file.

        Parameters
        ----------
        filename : str
            File path to check

        Returns
        -------
        bool
            True if filename has config-related extension
        """
        config_extensions = [".json", ".yaml", ".yml", ".env", ".config"]
        return any(filename.endswith(ext) for ext in config_extensions)

    def _is_test_file(self, filename: str) -> bool:
        """
        Check if file is a test file.

        Parameters
        ----------
        filename : str
            File path to check

        Returns
        -------
        bool
            True if filename contains 'test' or 'spec'
        """
        return "test" in filename.lower() or "spec" in filename.lower()

    def _extract_function_name(self, content: str, path: str) -> Optional[str]:
        """
        Try to extract the function name handling an endpoint.

        Searches for function definitions near endpoint declarations.

        Parameters
        ----------
        content : str
            Source code content
        path : str
            Endpoint path to search near

        Returns
        -------
        Optional[str]
            Function name if found, None otherwise
        """
        # Look for function definition near the path
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if path in line:
                # Check next few lines for function definition
                for j in range(max(0, i - 5), min(len(lines), i + 5)):
                    func_match = re.search(r"def\s+(\w+)\s*\(", lines[j])
                    if func_match:
                        return func_match.group(1)
        return None

    def _decode_content(self, content: str) -> str:
        """
        Decode base64 content from GitHub API.

        Parameters
        ----------
        content : str
            Base64 encoded content from GitHub

        Returns
        -------
        str
            Decoded UTF-8 string content
        """
        import base64

        try:
            return base64.b64decode(content).decode("utf-8")
        except:
            return content

    def _summarize_config_changes(self, patch: str) -> str:
        """
        Summarize configuration changes from a patch.

        Counts additions and deletions in a diff patch.

        Parameters
        ----------
        patch : str
            Git diff patch content

        Returns
        -------
        str
            Summary string like "5 additions, 3 deletions"
        """
        added = len(re.findall(r"^\+[^+]", patch, re.MULTILINE))
        removed = len(re.findall(r"^-[^-]", patch, re.MULTILINE))
        return f"{added} additions, {removed} deletions"

    async def _find_models(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Find data models in the repository."""
        # TODO: Implement model finding logic
        return []

    async def _find_schemas(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Find data schemas in the repository."""
        # TODO: Implement schema finding logic
        return []
