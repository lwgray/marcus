#!/usr/bin/env python3
"""
Create all Todo App development cards.

This is the main entry point that uses the modular card creation system
with Marcus's infrastructure for error handling and logging.
"""

import asyncio
import json
import logging
import os
from datetime import datetime

from card_creator import TodoAppCardCreator
from cards.card_loader import load_card_data

# Import ENHANCED_CARDS temporarily from old file
# TODO: Complete migration of card definitions to modular structure
import sys
sys.path.append(os.path.dirname(__file__))
from create_all_todo_app_cards import ENHANCED_CARDS

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_all_cards():
    """
    Create all Todo App development cards.
    
    This function orchestrates the entire card creation process using
    Marcus's infrastructure for reliability and monitoring.
    """
    
    # Set environment variables for Planka
    os.environ["PLANKA_BASE_URL"] = os.environ.get("PLANKA_BASE_URL", "http://localhost:3333")
    os.environ["PLANKA_AGENT_EMAIL"] = os.environ.get("PLANKA_AGENT_EMAIL", "demo@demo.demo")
    os.environ["PLANKA_AGENT_PASSWORD"] = os.environ.get("PLANKA_AGENT_PASSWORD", "demo")
    
    logger.info("🚀 Creating all Todo App development cards...")
    logger.info(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize card creator
    creator = TodoAppCardCreator()
    
    # Initialize MCP session
    session = await creator.initialize_session()
    
    try:
        # Find the Task Master Test project
        if not await creator.find_project(session, "Task Master Test"):
            logger.error("❌ Task Master Test project not found!")
            return
        
        # Clear existing cards
        await creator.clear_existing_cards(session)
        
        # Get the backlog list
        backlog_list = await creator.get_backlog_list(session)
        if not backlog_list:
            logger.error("❌ No Backlog list found!")
            return
        
        # Create labels
        await creator.create_labels(session)
        
        # Load card data
        todo_app_data = load_card_data()
        
        # Create all cards
        logger.info("\n📝 Creating cards...")
        created_count = 0
        card_id_map = {}
        
        for i, card_data in enumerate(todo_app_data["cards"][:17], 1):
            logger.info(f"\n[{i}/17] Creating: {card_data['title']}")
            
            # Get enhanced data
            enhanced = ENHANCED_CARDS.get(card_data["id"], {})
            
            # Create the card
            card_id = await creator.create_card(
                session,
                backlog_list["id"],
                card_data,
                enhanced,
            )
            
            if card_id:
                card_id_map[card_data["title"]] = card_id
                created_count += 1
                
                # Log progress
                creator.conversation_logger.log_progress_update(
                    task_id="todo_app_creation",
                    worker_id="todo_app_creator",
                    progress_percentage=int((i / 17) * 100),
                    status="in_progress",
                    message=f"Created {i}/17 cards",
                )
        
        # Log completion
        creator.conversation_logger.log_system_state(
            active_workers=0,
            tasks_in_progress=0,
            tasks_completed=created_count,
            system_metrics={
                "cards_created": created_count,
                "labels_created": len(creator.label_ids),
            }
        )
        
        # Print summary
        logger.info(f"\n✅ Successfully created {created_count}/17 cards!")
        logger.info("\n📊 Summary:")
        logger.info(f"  - Cards created: {created_count}")
        logger.info(f"  - Labels created: {len(creator.label_ids)}")
        logger.info(f"  - All cards in Backlog list")
        logger.info(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("\n✨ Todo App project board is ready!")
        
    except Exception as e:
        logger.error(f"❌ Error during card creation: {e}")
        
        # Log blocker
        creator.conversation_logger.log_blocker(
            task_id="todo_app_creation",
            worker_id="todo_app_creator",
            blocker_description=str(e),
            blocker_type="system",
            severity="high",
        )
        raise
    
    finally:
        # Clean up session
        await session.shutdown()


if __name__ == "__main__":
    asyncio.run(create_all_cards())