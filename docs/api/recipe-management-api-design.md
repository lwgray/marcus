# Recipe Management API Design

## Overview
RESTful API for the Smart Recipe Recommender system enabling users to store, search, and share recipes.

## Base URL
```
https://api.smartrecipe.com/v1
```

## Authentication
- JWT (JSON Web Tokens) for stateless authentication
- OAuth2 support for social login (Google, Facebook)
- API rate limiting: 1000 requests/hour for authenticated users

## Core API Endpoints

### Authentication Endpoints
```
POST   /auth/register          # User registration
POST   /auth/login             # User login
POST   /auth/refresh           # Refresh JWT token
POST   /auth/logout            # Logout (invalidate token)
POST   /auth/oauth/{provider}  # OAuth login
```

### User Management
```
GET    /users/me               # Get current user profile
PUT    /users/me               # Update user profile
DELETE /users/me               # Delete user account
GET    /users/{id}             # Get public user profile
PUT    /users/me/preferences   # Update dietary preferences
```

### Recipe Management
```
GET    /recipes                # List recipes (paginated)
POST   /recipes                # Create new recipe
GET    /recipes/{id}           # Get recipe details
PUT    /recipes/{id}           # Update recipe
DELETE /recipes/{id}           # Delete recipe
POST   /recipes/{id}/fork      # Fork/copy a recipe
```

### Recipe Search & Discovery
```
GET    /recipes/search         # Search recipes
GET    /recipes/trending       # Get trending recipes
GET    /recipes/recommended    # Get personalized recommendations
GET    /recipes/by-ingredients # Find recipes by available ingredients
```

### Recipe Interactions
```
POST   /recipes/{id}/rate      # Rate a recipe
GET    /recipes/{id}/ratings   # Get recipe ratings
POST   /recipes/{id}/favorite  # Add to favorites
DELETE /recipes/{id}/favorite  # Remove from favorites
POST   /recipes/{id}/comments  # Add comment
GET    /recipes/{id}/comments  # Get comments
```

### Ingredient Management
```
GET    /ingredients            # List all ingredients
GET    /ingredients/search     # Search ingredients
POST   /pantry/items           # Add to pantry
GET    /pantry/items           # Get user's pantry
PUT    /pantry/items/{id}      # Update pantry item
DELETE /pantry/items/{id}      # Remove from pantry
```

### Meal Planning
```
GET    /meal-plans             # Get user's meal plans
POST   /meal-plans             # Create meal plan
PUT    /meal-plans/{id}        # Update meal plan
DELETE /meal-plans/{id}        # Delete meal plan
POST   /meal-plans/{id}/recipes # Add recipe to plan
```

### Shopping Lists
```
GET    /shopping-lists         # Get shopping lists
POST   /shopping-lists         # Create shopping list
PUT    /shopping-lists/{id}    # Update shopping list
DELETE /shopping-lists/{id}    # Delete shopping list
POST   /shopping-lists/generate # Generate from meal plan
```

## Query Parameters

### Pagination
- `page` (default: 1)
- `limit` (default: 20, max: 100)

### Filtering
- `dietary` (vegan, vegetarian, gluten-free, keto, etc.)
- `cuisine` (italian, mexican, chinese, etc.)
- `difficulty` (easy, medium, hard)
- `prep_time_max` (in minutes)
- `cook_time_max` (in minutes)

### Sorting
- `sort` (popular, newest, rating, prep_time)
- `order` (asc, desc)

## Response Format

### Success Response
```json
{
  "success": true,
  "data": {
    // Response data
  },
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "RECIPE_NOT_FOUND",
    "message": "Recipe with ID 123 not found",
    "details": {}
  }
}
```

## HTTP Status Codes
- 200: Success
- 201: Created
- 204: No Content
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 422: Unprocessable Entity
- 429: Too Many Requests
- 500: Internal Server Error
