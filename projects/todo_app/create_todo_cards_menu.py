#!/usr/bin/env python3
"""
Menu to create Todo App cards with different levels of detail
"""

import asyncio
import os
import subprocess
import sys

from clear_board import clear_board_silent


def display_menu():
    """Display the menu options"""
    print("\n" + "=" * 60)
    print("📋 TODO APP CARD CREATOR")
    print("=" * 60)
    print("\nSelect an option:\n")
    print("1. 📚 COMPREHENSIVE - Full documentation, 12-16 subtasks per card")
    print("   • 2000+ word descriptions")
    print("   • Detailed technical requirements")
    print("   • Multiple labels and dependencies")
    print("   • Time estimates and due dates")
    print()
    print("2. 📝 MODERATE - Practical detail, 4-6 subtasks per card")
    print("   • Focused descriptions with key points")
    print("   • Essential technical details")
    print("   • Relevant labels")
    print("   • Due dates")
    print()
    print("3. ✏️  MINIMAL - Just the basics, 1-2 subtasks per card")
    print("   • One-line descriptions")
    print("   • Only high priority labels")
    print("   • Basic subtasks")
    print()
    print("4. 🧹 CLEAR BOARD - Remove all cards from the board")
    print("   • Deletes all cards from Task Master Test board")
    print("   • Keeps lists intact")
    print("   • Useful before creating new cards")
    print()
    print("5. ❌ EXIT")
    print("\n" + "=" * 60)


def run_script(script_name):
    """Run the selected script"""
    try:
        print(f"\n🚀 Running {script_name}...\n")
        script_path = os.path.join(os.path.dirname(__file__), script_name)
        subprocess.run([sys.executable, script_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error running script: {e}")
    except FileNotFoundError:
        print(f"\n❌ Script not found: {script_name}")


def main():
    """Main menu loop"""
    while True:
        display_menu()
        choice = input("\nEnter your choice (1-5): ").strip()

        if choice == "1":
            print("\n📚 Creating COMPREHENSIVE Todo App cards...")
            print("This will create detailed cards with full documentation.")

            # Ask if they want to clear the board first
            clear_first = input("Clear board first? (y/n): ").strip().lower()
            if clear_first == "y":
                print("\n🔄 Clearing board...")
                try:
                    success, message = asyncio.run(clear_board_silent())
                    if success:
                        print(f"✅ {message}")
                    else:
                        print(f"❌ Error: {message}")
                        continue
                except Exception as e:
                    print(f"❌ Error clearing board: {str(e)}")
                    continue

            confirm = input("\nCreate cards now? (y/n): ").strip().lower()
            if confirm == "y":
                run_script("create_all_todo_app_cards.py")
            else:
                print("Cancelled.")

        elif choice == "2":
            print("\n📝 Creating MODERATE Todo App cards...")
            print("This will create cards with practical, focused detail.")

            # Ask if they want to clear the board first
            clear_first = input("Clear board first? (y/n): ").strip().lower()
            if clear_first == "y":
                print("\n🔄 Clearing board...")
                try:
                    success, message = asyncio.run(clear_board_silent())
                    if success:
                        print(f"✅ {message}")
                    else:
                        print(f"❌ Error: {message}")
                        continue
                except Exception as e:
                    print(f"❌ Error clearing board: {str(e)}")
                    continue

            confirm = input("\nCreate cards now? (y/n): ").strip().lower()
            if confirm == "y":
                run_script("create_moderate_todo_cards.py")
            else:
                print("Cancelled.")

        elif choice == "3":
            print("\n✏️  Creating MINIMAL Todo App cards...")
            print("This will create cards with just the essential information.")

            # Ask if they want to clear the board first
            clear_first = input("Clear board first? (y/n): ").strip().lower()
            if clear_first == "y":
                print("\n🔄 Clearing board...")
                try:
                    success, message = asyncio.run(clear_board_silent())
                    if success:
                        print(f"✅ {message}")
                    else:
                        print(f"❌ Error: {message}")
                        continue
                except Exception as e:
                    print(f"❌ Error clearing board: {str(e)}")
                    continue

            confirm = input("\nCreate cards now? (y/n): ").strip().lower()
            if confirm == "y":
                run_script("create_minimal_todo_cards.py")
            else:
                print("Cancelled.")

        elif choice == "4":
            print("\n🧹 Clearing the board...")
            print("This will remove all cards from the Task Master Test board.")
            confirm = input("Continue? (y/n): ").strip().lower()
            if confirm == "y":
                print("\n🔄 Connecting to board...")
                try:
                    success, message = asyncio.run(clear_board_silent())
                    if success:
                        print(f"✅ {message}")
                    else:
                        print(f"❌ Error: {message}")
                except Exception as e:
                    print(f"❌ Error clearing board: {str(e)}")
            else:
                print("Cancelled.")

        elif choice == "5":
            print("\n👋 Goodbye!")
            break

        else:
            print("\n⚠️  Invalid choice. Please enter 1-5.")

        if choice in ["1", "2", "3", "4"]:
            input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
