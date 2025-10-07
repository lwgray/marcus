"""
Consistent response formatting for the Task Management API.

This module implements standardized response formats that improve
usability by providing predictable, well-structured API responses
with helpful metadata and navigation links (HATEOAS).
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationLinks(BaseModel):
    """
    HATEOAS links for pagination navigation.

    Attributes
    ----------
    self : str
        Link to current page
    first : str
        Link to first page
    last : str
        Link to last page
    next : str, optional
        Link to next page (if available)
    prev : str, optional
        Link to previous page (if available)
    """

    self: str = Field(..., description="Link to the current page")
    first: str = Field(..., description="Link to the first page")
    last: str = Field(..., description="Link to the last page")
    next: Optional[str] = Field(None, description="Link to the next page")
    prev: Optional[str] = Field(None, description="Link to the previous page")

    class Config:
        schema_extra = {
            "example": {
                "self": "/api/v1/tasks?page=2&limit=20",
                "first": "/api/v1/tasks?page=1&limit=20",
                "last": "/api/v1/tasks?page=5&limit=20",
                "next": "/api/v1/tasks?page=3&limit=20",
                "prev": "/api/v1/tasks?page=1&limit=20",
            }
        }


class ResourceLinks(BaseModel):
    """
    HATEOAS links for resource navigation.

    Attributes
    ----------
    self : str
        Link to this resource
    related : Dict[str, str], optional
        Links to related resources
    """

    self: str = Field(..., description="Link to this resource")
    related: Optional[Dict[str, str]] = Field(
        None,
        description="Links to related resources",
    )

    class Config:
        schema_extra = {
            "example": {
                "self": "/api/v1/tasks/abc123",
                "related": {
                    "subtasks": "/api/v1/tasks/abc123/subtasks",
                    "time_entries": "/api/v1/time/entries?task_id=abc123",
                    "project": "/api/v1/projects/xyz789",
                },
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standardized paginated response format.

    This format provides clear pagination information and navigation
    links to improve usability when working with lists of resources.

    Attributes
    ----------
    items : List[T]
        List of items for current page
    total : int
        Total number of items across all pages
    page : int
        Current page number (1-indexed)
    limit : int
        Number of items per page
    total_pages : int
        Total number of pages
    _links : PaginationLinks
        Navigation links for pagination

    Examples
    --------
    >>> response = PaginatedResponse(
    ...     items=[task1, task2],
    ...     total=45,
    ...     page=1,
    ...     limit=20
    ... )
    >>> response.total_pages
    3
    """

    items: List[T] = Field(..., description="Items for the current page")
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(..., ge=1, le=100, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    _links: PaginationLinks = Field(..., description="Pagination links")

    class Config:
        schema_extra = {
            "example": {
                "items": [],
                "total": 45,
                "page": 1,
                "limit": 20,
                "total_pages": 3,
                "_links": {
                    "self": "/api/v1/tasks?page=1&limit=20",
                    "first": "/api/v1/tasks?page=1&limit=20",
                    "last": "/api/v1/tasks?page=3&limit=20",
                    "next": "/api/v1/tasks?page=2&limit=20",
                    "prev": None,
                },
            }
        }


class SingleResourceResponse(BaseModel, Generic[T]):
    """
    Standardized single resource response format.

    Attributes
    ----------
    data : T
        The resource data
    _links : ResourceLinks
        Navigation links for the resource
    """

    data: T = Field(..., description="The resource data")
    _links: ResourceLinks = Field(..., description="Resource navigation links")


class SuccessResponse(BaseModel):
    """
    Standardized success response for operations without resource data.

    Attributes
    ----------
    success : bool
        Always True for success responses
    message : str
        User-friendly success message
    request_id : str
        Unique request identifier
    timestamp : str
        ISO 8601 timestamp
    """

    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="User-friendly success message")
    request_id: str = Field(..., description="Unique request identifier")
    timestamp: str = Field(..., description="ISO 8601 timestamp")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Task deleted successfully",
                "request_id": "req_abc123xyz",
                "timestamp": "2025-10-06T14:30:00Z",
            }
        }


class CreatedResponse(BaseModel, Generic[T]):
    """
    Standardized response for resource creation.

    Attributes
    ----------
    success : bool
        Always True for success
    message : str
        User-friendly success message
    data : T
        The created resource
    _links : ResourceLinks
        Links to the new resource
    """

    success: bool = Field(True, description="Creation success status")
    message: str = Field(..., description="User-friendly success message")
    data: T = Field(..., description="The created resource")
    _links: ResourceLinks = Field(..., description="Resource links")


def create_pagination_links(
    base_url: str,
    page: int,
    limit: int,
    total_pages: int,
    query_params: Optional[Dict[str, Any]] = None,
) -> PaginationLinks:
    """
    Generate pagination links for a response.

    Parameters
    ----------
    base_url : str
        Base URL for the endpoint
    page : int
        Current page number
    limit : int
        Items per page
    total_pages : int
        Total number of pages
    query_params : Dict[str, Any], optional
        Additional query parameters to include

    Returns
    -------
    PaginationLinks
        Generated pagination links

    Examples
    --------
    >>> links = create_pagination_links(
    ...     "/api/v1/tasks",
    ...     page=2,
    ...     limit=20,
    ...     total_pages=5,
    ...     query_params={"status": "TODO"}
    ... )
    >>> links.next
    '/api/v1/tasks?page=3&limit=20&status=TODO'
    """

    def build_url(page_num: int) -> str:
        """Build URL with page and query params."""
        params = {"page": page_num, "limit": limit}
        if query_params:
            params.update(query_params)

        param_str = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{base_url}?{param_str}"

    return PaginationLinks(
        self=build_url(page),
        first=build_url(1),
        last=build_url(total_pages),
        next=build_url(page + 1) if page < total_pages else None,
        prev=build_url(page - 1) if page > 1 else None,
    )


def create_resource_links(
    resource_url: str,
    related_resources: Optional[Dict[str, str]] = None,
) -> ResourceLinks:
    """
    Generate resource navigation links.

    Parameters
    ----------
    resource_url : str
        URL to the resource
    related_resources : Dict[str, str], optional
        Mapping of related resource names to URLs

    Returns
    -------
    ResourceLinks
        Generated resource links

    Examples
    --------
    >>> links = create_resource_links(
    ...     "/api/v1/tasks/abc123",
    ...     {"subtasks": "/api/v1/tasks/abc123/subtasks"}
    ... )
    >>> links.related["subtasks"]
    '/api/v1/tasks/abc123/subtasks'
    """
    return ResourceLinks(
        self=resource_url,
        related=related_resources,
    )


def paginate(
    items: List[T],
    total: int,
    page: int,
    limit: int,
    base_url: str,
    query_params: Optional[Dict[str, Any]] = None,
) -> PaginatedResponse[T]:
    """
    Create a paginated response from a list of items.

    Parameters
    ----------
    items : List[T]
        Items for the current page
    total : int
        Total number of items
    page : int
        Current page number
    limit : int
        Items per page
    base_url : str
        Base URL for pagination links
    query_params : Dict[str, Any], optional
        Additional query parameters

    Returns
    -------
    PaginatedResponse[T]
        Formatted paginated response

    Examples
    --------
    >>> tasks = [task1, task2, task3]
    >>> response = paginate(
    ...     tasks,
    ...     total=45,
    ...     page=1,
    ...     limit=20,
    ...     base_url="/api/v1/tasks"
    ... )
    >>> response.total_pages
    3
    """
    total_pages = (total + limit - 1) // limit if total > 0 else 0

    links = create_pagination_links(
        base_url=base_url,
        page=page,
        limit=limit,
        total_pages=total_pages,
        query_params=query_params,
    )

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
        _links=links,
    )


def success_response(
    message: str,
    request_id: Optional[str] = None,
) -> SuccessResponse:
    """
    Create a success response for operations without resource data.

    Parameters
    ----------
    message : str
        User-friendly success message
    request_id : str, optional
        Unique request identifier

    Returns
    -------
    SuccessResponse
        Formatted success response

    Examples
    --------
    >>> response = success_response("Task deleted successfully")
    >>> response.success
    True
    """
    import uuid

    return SuccessResponse(
        success=True,
        message=message,
        request_id=request_id or str(uuid.uuid4()),
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


def created_response(
    data: T,
    message: str,
    resource_url: str,
    related_resources: Optional[Dict[str, str]] = None,
) -> CreatedResponse[T]:
    """
    Create a response for successful resource creation.

    Parameters
    ----------
    data : T
        The created resource
    message : str
        User-friendly success message
    resource_url : str
        URL to the created resource
    related_resources : Dict[str, str], optional
        URLs to related resources

    Returns
    -------
    CreatedResponse[T]
        Formatted creation response

    Examples
    --------
    >>> response = created_response(
    ...     task,
    ...     "Task created successfully",
    ...     "/api/v1/tasks/abc123"
    ... )
    >>> response.message
    'Task created successfully'
    """
    links = create_resource_links(resource_url, related_resources)

    return CreatedResponse(
        success=True,
        message=message,
        data=data,
        _links=links,
    )
