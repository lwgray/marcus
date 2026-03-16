# Snake Game Development Task

You are tasked with building a complete snake game web application.

## Project Specification

Build a simple snake game web app with basic features.

## Tasks to Complete

### 1. Design Game Mechanics
**Description:** Design the architecture for the Game Mechanics which encompasses the following features:

1. START GAME
   Allow the user to start a new game of snake. The game should initialize the game board, the snake, and the food.

2. CONTROL SNAKE
   Allow the user to control the movement of the snake using the arrow keys or WASD keys. The snake should move in the direction the user inputs.

Your design should define:
- Component boundaries (what components exist and their responsibilities)
- Data flows (how data moves between components)
- Integration points (how components communicate)
- Shared data models (schemas, entities, etc.)

Create design artifacts such as:
- Architecture diagrams (component relationships, data flow)
- API contracts (endpoint definitions, request/response schemas)
- Data models (database schemas, entity relationships)
- Integration specifications (how components communicate)

### 2. Implement Start Game
**Description:** IMPLEMENT: Implement the "Start Game" feature to allow the user to start a new game of snake. The feature should:
1. Initialize the game board, creating a grid of cells.
2. Spawn the snake at a starting position on the game board.
3. Spawn food at a random position on the game board.
4. Provide controls for the user to move the snake (e.g., arrow keys or WASD).
5. Handle the game logic, such as growing the snake when it eats the food and ending the game when the snake collides with the game board edges or itself.

### 3. Implement Control Snake
**Description:** Implement the functionality to control the snake's movement using the arrow keys or WASD keys. The snake should move in the direction the user inputs by updating the snake's position and rendering the updated snake on the game canvas.
