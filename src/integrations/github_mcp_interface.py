"""
GitHub MCP Interface

Wrapper for GitHub MCP tools to provide a clean interface for the quality assessor
and other components that need GitHub data.
"""

from typing import Any, Callable, Dict, List, Optional


class GitHubMCPInterface:
    """
    Interface for GitHub MCP operations.

    Provides a clean API for components that need to interact with GitHub
    through the MCP server, abstracting away the specific tool calls.
    """

    def __init__(self, mcp_caller: Callable[..., Any]) -> None:
        """
        Initialize the GitHub MCP interface.

        Parameters
        ----------
        mcp_caller : Callable
            Function to call MCP tools (e.g., from kanban_client)
        """
        self.mcp_caller = mcp_caller

    async def list_commits(
        self,
        owner: str,
        repo: str,
        since: Optional[str] = None,
        until: Optional[str] = None,
        author: Optional[str] = None,
        path: Optional[str] = None,
        per_page: int = 100,
    ) -> Dict[str, Any]:
        """
        List commits for a repository.

        Parameters
        ----------
        owner : str
            Repository owner
        repo : str
            Repository name
        since : Optional[str]
            Only commits after this date (ISO 8601 format)
        until : Optional[str]
            Only commits before this date (ISO 8601 format)
        author : Optional[str]
            GitHub username or email
        path : Optional[str]
            Only commits touching this path
        per_page : int
            Results per page (max 100)

        Returns
        -------
        Dict[str, Any]
            Response with commits list
        """
        params = {
            "owner": owner,
            "repo": repo,
            "perPage": per_page,
        }

        if since:
            params["since"] = since
        if until:
            params["until"] = until
        if author:
            params["author"] = author
        if path:
            params["path"] = path

        result = await self.mcp_caller("github.list_commits", params)
        return {"commits": result.get("commits", [])}

    async def search_issues(
        self,
        query: str,
        sort: Optional[str] = None,
        order: Optional[str] = None,
        per_page: int = 100,
    ) -> Dict[str, Any]:
        """
        Search for issues and pull requests.

        Parameters
        ----------
        query : str
            Search query using GitHub's search syntax
        sort : Optional[str]
            Sort field (comments, reactions, reactions-+1, etc.)
        order : Optional[str]
            Sort order (asc or desc)
        per_page : int
            Results per page (max 100)

        Returns
        -------
        Dict[str, Any]
            Response with items list
        """
        params = {
            "query": query,
            "perPage": per_page,
        }

        if sort:
            params["sort"] = sort
        if order:
            params["order"] = order

        result = await self.mcp_caller("github.search_issues", params)
        return {"items": result.get("items", [])}

    async def list_pr_reviews(
        self, owner: str, repo: str, pr_number: int, per_page: int = 100
    ) -> Dict[str, Any]:
        """
        List reviews for a pull request.

        Parameters
        ----------
        owner : str
            Repository owner
        repo : str
            Repository name
        pr_number : int
            Pull request number
        per_page : int
            Results per page (max 100)

        Returns
        -------
        Dict[str, Any]
            Response with reviews list
        """
        params = {
            "owner": owner,
            "repo": repo,
            "pull_number": pr_number,
            "perPage": per_page,
        }

        result = await self.mcp_caller("github.list_pr_reviews", params)
        return {"reviews": result.get("reviews", [])}

    async def get_repository_content(
        self, owner: str, repo: str, path: str = "", ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get repository content at a specific path.

        Parameters
        ----------
        owner : str
            Repository owner
        repo : str
            Repository name
        path : str
            Path to file or directory
        ref : Optional[str]
            Branch, tag, or commit SHA

        Returns
        -------
        Dict[str, Any]
            Response with content data
        """
        params = {
            "owner": owner,
            "repo": repo,
            "path": path,
        }

        if ref:
            params["ref"] = ref

        result = await self.mcp_caller("github.get_file_contents", params)
        return result  # type: ignore[no-any-return]

    async def get_pull_request(
        self, owner: str, repo: str, pr_number: int
    ) -> Dict[str, Any]:
        """
        Get a specific pull request.

        Parameters
        ----------
        owner : str
            Repository owner
        repo : str
            Repository name
        pr_number : int
            Pull request number

        Returns
        -------
        Dict[str, Any]
            Pull request data
        """
        params = {
            "owner": owner,
            "repo": repo,
            "pull_number": pr_number,
        }

        result = await self.mcp_caller("github.get_pr", params)
        return result  # type: ignore[no-any-return]

    async def list_pr_commits(
        self, owner: str, repo: str, pr_number: int, per_page: int = 100
    ) -> Dict[str, Any]:
        """
        List commits for a pull request.

        Parameters
        ----------
        owner : str
            Repository owner
        repo : str
            Repository name
        pr_number : int
            Pull request number
        per_page : int
            Results per page (max 100)

        Returns
        -------
        Dict[str, Any]
            Response with commits list
        """
        params = {
            "owner": owner,
            "repo": repo,
            "pull_number": pr_number,
            "perPage": per_page,
        }

        result = await self.mcp_caller("github.list_pr_commits", params)
        return {"commits": result.get("commits", [])}

    async def get_repository_stats(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        Get repository statistics.

        Parameters
        ----------
        owner : str
            Repository owner
        repo : str
            Repository name

        Returns
        -------
        Dict[str, Any]
            Repository statistics
        """
        # Get repository info
        params = {
            "owner": owner,
            "repo": repo,
        }

        result = await self.mcp_caller("github.get_repo", params)

        # Extract useful stats
        stats = {
            "stars": result.get("stargazers_count", 0),
            "forks": result.get("forks_count", 0),
            "open_issues": result.get("open_issues_count", 0),
            "size": result.get("size", 0),
            "language": result.get("language", ""),
            "default_branch": result.get("default_branch", "main"),
            "created_at": result.get("created_at", ""),
            "updated_at": result.get("updated_at", ""),
        }

        return stats
