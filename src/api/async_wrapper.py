"""
Async wrapper for Flask routes to handle async functions properly.
"""

import asyncio
from functools import wraps
from flask import jsonify


def async_route(f):
    """
    Decorator to handle async routes in Flask.
    
    Wraps async functions to run in the event loop properly.
    """
    @wraps(f)
    def wrapped(*args, **kwargs):
        try:
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Event loop is closed")
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the async function
            result = loop.run_until_complete(f(*args, **kwargs))
            return result
            
        except Exception as e:
            # Return error as JSON
            return jsonify({
                "success": False,
                "error": str(e),
                "type": type(e).__name__
            }), 500
            
    return wrapped