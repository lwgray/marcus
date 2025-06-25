# PM Agent Documentation Guide

This directory contains the documentation for PM Agent, including API references, guides, and Sphinx documentation source.

## Structure

```
docs/
├── sphinx/                  # Sphinx documentation source
│   ├── source/             # RST and Markdown source files
│   │   ├── api/           # Auto-generated API documentation
│   │   ├── user_guide/    # User guides and how-tos
│   │   ├── tutorials/     # Step-by-step tutorials
│   │   ├── templates/     # Project templates for users
│   │   ├── developer/     # Developer documentation
│   │   ├── reference/     # Reference documentation
│   │   ├── conf.py        # Sphinx configuration
│   │   └── index.rst      # Main documentation index
│   ├── build/             # Built documentation (git-ignored)
│   └── Makefile           # Build commands
├── internal/               # Internal developer documentation
│   ├── planning/          # Product planning documents
│   ├── implementation/    # Technical implementation details
│   └── archive/           # Historical documents
├── *.md                    # Legacy documentation (being migrated)
└── build_docs.sh          # Local documentation build script
```

## Building Documentation Locally

### Prerequisites

```bash
pip install sphinx sphinx-rtd-theme
```

### Build HTML Documentation

```bash
# From the docs directory
./build_docs.sh

# Or manually
cd sphinx
make clean
make html
```

The built documentation will be available at `docs/sphinx/build/html/index.html`.

## GitHub Pages Deployment

Documentation is automatically built and deployed to GitHub Pages when changes are pushed to the main branch.

The GitHub Actions workflow (`.github/workflows/docs.yml`) handles:
1. Installing dependencies
2. Building Sphinx documentation
3. Deploying to GitHub Pages

### Viewing Online Documentation

Once deployed, the documentation is available at:
https://lwgray.github.io/pm-agent/

## Writing Documentation

### Adding New Pages

1. Create a new `.rst` file in `docs/sphinx/source/`
2. Add it to the appropriate `toctree` in `index.rst`
3. Use reStructuredText format for content

### API Documentation

API documentation is automatically generated from Python docstrings using Sphinx autodoc. We use NumPy-style docstrings throughout the codebase.

Example:
```python
def my_function(param1: str, param2: int) -> bool:
    """
    Brief description of the function.
    
    Parameters
    ----------
    param1 : str
        Description of param1
    param2 : int
        Description of param2
    
    Returns
    -------
    bool
        Description of return value
    
    Examples
    --------
    >>> my_function("hello", 42)
    True
    """
```

### Updating API Reference

The API reference in `API_REFERENCE.md` should be updated manually when:
- New MCP tools are added
- Tool parameters change
- Response formats are modified
- New classes or methods are exposed

## Documentation Standards

1. **Clarity**: Write for developers who are new to PM Agent
2. **Examples**: Include code examples for all tools and methods
3. **Completeness**: Document all parameters, returns, and exceptions
4. **Consistency**: Follow the established format and style
5. **Accuracy**: Keep documentation in sync with code changes

## Contributing

When contributing to PM Agent:
1. Update relevant documentation with your changes
2. Add docstrings to new functions/classes
3. Update API_REFERENCE.md if adding/modifying MCP tools
4. Test that documentation builds without warnings