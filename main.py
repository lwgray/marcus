#!/usr/bin/env python3
"""
AI Project Manager Agent - Main Entry Point
"""

import asyncio
import argparse
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path
sys.path.append(str(Path(__file__).parent))

from pm_agent_mcp_server import PMAgentServer
from src.config.settings import Settings


def setup_logging(level: str = "INFO"):
    """Configure logging"""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('pm_agent.log')
        ]
    )


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="AI Project Manager Agent - MCP Server"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="config/pm_agent_config.json",
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate configuration and exit"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Load and validate configuration
    settings = Settings(args.config)
    
    if args.validate_config:
        if settings.validate():
            logger.info("Configuration is valid")
            sys.exit(0)
        else:
            logger.error("Configuration validation failed")
            sys.exit(1)
    
    # Ensure required environment variables
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY environment variable is required")
        sys.exit(1)
    
    # Start the PM Agent server
    logger.info("Starting AI Project Manager Agent...")
    
    try:
        agent = PMAgentServer()
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()