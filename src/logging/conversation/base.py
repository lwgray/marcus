"""
Base logger functionality for the conversation logging system.

This module provides the common base class and utilities used by all
specialized conversation loggers.
"""

import json
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional


class ConversationLoggerBase:
    """
    Base class for all conversation loggers.

    Provides common functionality for file handling, JSON formatting,
    and timestamp management.
    """

    def __init__(self, log_dir: str = "logs/conversations") -> None:
        """
        Initialize the base logger.

        Parameters
        ----------
        log_dir : str
            Directory for storing log files
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Setup component-specific logger
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)

        # Track start time for session duration
        self.start_time = datetime.now()

        # Setup file handlers
        self._setup_file_handlers()

    def _setup_file_handlers(self) -> None:
        """Set up rotating file handlers for different log types."""
        # To be overridden by subclasses for specific file handlers
        pass

    def _create_rotating_handler(
        self,
        filename: str,
        max_bytes: int = 50 * 1024 * 1024,  # 50MB
        backup_count: int = 10,
    ) -> RotatingFileHandler:
        """
        Create a rotating file handler.

        Parameters
        ----------
        filename : str
            Name of the log file
        max_bytes : int
            Maximum size of each log file
        backup_count : int
            Number of backup files to keep
        """
        filepath = self.log_dir / filename
        handler = RotatingFileHandler(
            str(filepath), maxBytes=max_bytes, backupCount=backup_count
        )
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        return handler

    def _log_entry(self, entry: Dict[str, Any], handler_name: str) -> None:
        """
        Log an entry to the appropriate handler.

        Parameters
        ----------
        entry : dict
            Log entry data
        handler_name : str
            Name of the handler to use
        """
        # Add common fields
        entry["timestamp"] = datetime.now().isoformat()
        entry["session_id"] = str(self.start_time.timestamp())

        # Find the appropriate handler
        for handler in self.logger.handlers:
            if hasattr(handler, "name") and handler.name == handler_name:
                handler.emit(
                    logging.LogRecord(
                        name=self.logger.name,
                        level=logging.INFO,
                        pathname="",
                        lineno=0,
                        msg=json.dumps(entry),
                        args=(),
                        exc_info=None,
                    )
                )
                break

    @staticmethod
    def _calculate_duration(start_time: str, end_time: Optional[str] = None) -> float:
        """
        Calculate duration between timestamps.

        Parameters
        ----------
        start_time : str
            ISO format start timestamp
        end_time : str, optional
            ISO format end timestamp, current time if None

        Returns
        -------
        float
            Duration in seconds
        """
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time) if end_time else datetime.now()
        return (end - start).total_seconds()

    @staticmethod
    def _sanitize_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Sanitize metadata for JSON serialization.

        Parameters
        ----------
        metadata : dict, optional
            Raw metadata

        Returns
        -------
        dict
            Sanitized metadata safe for JSON
        """
        if not metadata:
            return {}

        # Convert non-serializable types
        sanitized = {}
        for key, value in metadata.items():
            if isinstance(value, (datetime,)):
                sanitized[key] = value.isoformat()
            elif hasattr(value, "__dict__"):
                sanitized[key] = str(value)
            else:
                sanitized[key] = value

        return sanitized
