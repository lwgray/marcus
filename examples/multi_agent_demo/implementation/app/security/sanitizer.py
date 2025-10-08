"""
Input sanitization utilities for preventing XSS and injection attacks.

Provides HTML sanitization and text cleaning functions to protect
against malicious user input across the application.
"""

import re
from typing import List, Optional

import bleach

# Allowed HTML tags for rich text (comments, descriptions)
ALLOWED_TAGS = [
    "p",
    "br",
    "strong",
    "em",
    "u",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "li",
    "blockquote",
    "code",
    "pre",
    "a",
    "img",
]

# Allowed HTML attributes
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
    "code": ["class"],
}

# Allowed URL protocols
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def sanitize_html(
    html_content: str,
    allowed_tags: Optional[List[str]] = None,
    allowed_attributes: Optional[dict] = None,
    strip: bool = False,
) -> str:
    """
    Sanitize HTML content to prevent XSS attacks.

    Parameters
    ----------
    html_content : str
        HTML content to sanitize
    allowed_tags : list of str, optional
        List of allowed HTML tags (default: ALLOWED_TAGS)
    allowed_attributes : dict, optional
        Dictionary of tag: [attributes] allowed (default: ALLOWED_ATTRIBUTES)
    strip : bool, optional
        If True, strip disallowed tags entirely.
        If False, escape them as text (default: False)

    Returns
    -------
    str
        Sanitized HTML content

    Examples
    --------
    >>> sanitize_html("<p>Hello</p><script>alert('xss')</script>")
    '<p>Hello</p>&lt;script&gt;alert(\'xss\')&lt;/script&gt;'

    >>> sanitize_html("<p>Hello</p><script>alert('xss')</script>", strip=True)
    '<p>Hello</p>'

    >>> # Allow only specific tags
    >>> sanitize_html("<p>Hello <strong>World</strong></p>", allowed_tags=['p'])
    '<p>Hello &lt;strong&gt;World&lt;/strong&gt;</p>'

    Notes
    -----
    - Uses bleach library for HTML sanitization
    - Removes/escapes dangerous tags like <script>, <iframe>, etc.
    - Validates URLs in href/src attributes
    - Preserves safe formatting tags for rich text
    """
    if allowed_tags is None:
        allowed_tags = ALLOWED_TAGS

    if allowed_attributes is None:
        allowed_attributes = ALLOWED_ATTRIBUTES

    # Sanitize using bleach
    clean_html = bleach.clean(
        html_content,
        tags=allowed_tags,
        attributes=allowed_attributes,
        protocols=ALLOWED_PROTOCOLS,
        strip=strip,
    )

    return clean_html


def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize plain text input by removing HTML and limiting length.

    Parameters
    ----------
    text : str
        Text to sanitize
    max_length : int, optional
        Maximum allowed length (truncates if exceeded)

    Returns
    -------
    str
        Sanitized text with HTML removed

    Examples
    --------
    >>> sanitize_text("Hello <script>alert('xss')</script>")
    'Hello '

    >>> sanitize_text("Very long text...", max_length=10)
    'Very long ...'

    Notes
    -----
    - Strips all HTML tags
    - Removes extra whitespace
    - Optionally truncates to max_length with ellipsis
    """
    # Strip all HTML tags
    clean_text = bleach.clean(text, tags=[], strip=True)

    # Remove extra whitespace
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    # Truncate if needed
    if max_length and len(clean_text) > max_length:
        clean_text = clean_text[: max_length - 3] + "..."

    return clean_text


def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """
    Sanitize a filename to prevent path traversal attacks.

    Parameters
    ----------
    filename : str
        Filename to sanitize
    replacement : str, optional
        Character to replace invalid characters with (default: "_")

    Returns
    -------
    str
        Sanitized filename safe for file system operations

    Examples
    --------
    >>> sanitize_filename("../../etc/passwd")
    '_etc_passwd'

    >>> sanitize_filename("file<>name.txt")
    'file__name.txt'

    >>> sanitize_filename("my file (1).txt")
    'my_file__1_.txt'

    Notes
    -----
    - Removes path separators (/ and \\)
    - Removes null bytes
    - Removes dangerous characters: < > : " | ? *
    - Preserves file extension
    - Limits length to 255 characters
    """
    # Remove path components
    filename = filename.replace("/", replacement).replace("\\", replacement)

    # Remove null bytes
    filename = filename.replace("\0", "")

    # Remove dangerous characters
    dangerous_chars = r'[<>:"|?*]'
    filename = re.sub(dangerous_chars, replacement, filename)

    # Remove leading/trailing dots and spaces
    filename = filename.strip(". ")

    # Limit length (filesystem limit is usually 255)
    if len(filename) > 255:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        max_name_len = 250 - len(ext)
        filename = name[:max_name_len] + ("." + ext if ext else "")

    # Ensure not empty
    if not filename:
        filename = "file"

    return filename


def sanitize_email(email: str) -> str:
    """
    Sanitize and validate email address format.

    Parameters
    ----------
    email : str
        Email address to sanitize

    Returns
    -------
    str
        Sanitized email address in lowercase

    Raises
    ------
    ValueError
        If email format is invalid

    Examples
    --------
    >>> sanitize_email("  User@Example.COM  ")
    'user@example.com'

    >>> sanitize_email("invalid.email")
    Traceback (most recent call last):
    ValueError: Invalid email format

    Notes
    -----
    - Converts to lowercase
    - Strips whitespace
    - Validates basic email format (contains @ and domain)
    - Does NOT perform DNS validation
    """
    # Strip and lowercase
    email = email.strip().lower()

    # Basic email validation
    email_pattern = r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$"
    if not re.match(email_pattern, email):
        raise ValueError("Invalid email format")

    return email


def sanitize_url(url: str, allowed_schemes: Optional[List[str]] = None) -> str:
    """
    Sanitize and validate URL.

    Parameters
    ----------
    url : str
        URL to sanitize
    allowed_schemes : list of str, optional
        Allowed URL schemes (default: ['http', 'https'])

    Returns
    -------
    str
        Sanitized URL

    Raises
    ------
    ValueError
        If URL scheme is not allowed or URL is invalid

    Examples
    --------
    >>> sanitize_url("https://example.com/path")
    'https://example.com/path'

    >>> sanitize_url("javascript:alert('xss')")
    Traceback (most recent call last):
    ValueError: URL scheme 'javascript' not allowed

    Notes
    -----
    - Validates URL scheme (http/https by default)
    - Prevents javascript: and data: URLs
    - Does NOT validate that URL is reachable
    """
    from urllib.parse import urlparse

    if allowed_schemes is None:
        allowed_schemes = ["http", "https"]

    # Strip whitespace
    url = url.strip()

    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception:
        raise ValueError("Invalid URL format")

    # Validate scheme
    if parsed.scheme not in allowed_schemes:
        raise ValueError(f"URL scheme '{parsed.scheme}' not allowed")

    # Ensure netloc exists (domain)
    if not parsed.netloc:
        raise ValueError("URL must include a domain")

    return url


def escape_sql_like(value: str, escape_char: str = "\\") -> str:
    """
    Escape special characters for SQL LIKE queries.

    Parameters
    ----------
    value : str
        Value to escape for LIKE query
    escape_char : str, optional
        Escape character to use (default: "\\")

    Returns
    -------
    str
        Escaped value safe for LIKE queries

    Examples
    --------
    >>> escape_sql_like("50%_discount")
    '50\\\\%\\\\_discount'

    >>> # Use in SQLAlchemy query
    >>> # User.query.filter(User.username.like(f"%{escape_sql_like(search)}%", escape="\\\\"))

    Notes
    -----
    - Escapes % and _ wildcards
    - Prevents SQL injection in LIKE queries
    - Use with parameterized queries for full protection
    """
    # Escape the escape character itself first
    value = value.replace(escape_char, escape_char + escape_char)

    # Escape SQL LIKE wildcards
    value = value.replace("%", escape_char + "%")
    value = value.replace("_", escape_char + "_")

    return value
