#!/usr/bin/env python3
"""
Run the Marcus Visualization API server.

Usage:
    python viz_backend/run_server.py
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "viz_backend.api:app",
        host="0.0.0.0",  # nosec B104
        port=8000,
        reload=True,  # Enable auto-reload during development
        log_level="info",
    )
