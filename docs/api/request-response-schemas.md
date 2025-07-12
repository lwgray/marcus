# Request/Response Schemas

## Authentication Schemas

### Register Request
```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe"
}
```

### Register Response
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "email": "user@example.com",
      "username": "johndoe",
      "first_name": "John",
      "last_name": "Doe",
      "created_at": "2025-07-07T12:00:00Z"
    },
    "tokens": {
      "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
      "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
      "expires_in": 3600
    }
  }
}
```

### Login Request
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

## Recipe Schemas

### Create Recipe Request
```json
{
  "title": "Spaghetti Carbonara",
  "description": "Classic Italian pasta dish with eggs, cheese, and guanciale",
  "instructions": [
    {
      "step": 1,
      "text": "Bring a large pot of salted water to boil",
      "time_minutes": 5
    },
    {
      "step": 2,
      "text": "Cook guanciale until crispy",
      "time_minutes": 8
    }
  ],
  "prep_time": 10,
  "cook_time": 20,
  "servings": 4,
  "difficulty": "medium",
  "cuisine": "italian",
  "course": "main",
  "ingredients": [
    {
      "ingredient_id": "456e7890-e89b-12d3-a456-426614174000",
      "quantity": 400,
      "unit": "g",
      "notes": "spaghetti or rigatoni"
    },
    {
      "ingredient_id": "789e0123-e89b-12d3-a456-426614174000",
      "quantity": 200,
      "unit": "g",
      "notes": "or pancetta"
    }
  ],
  "nutrition": {
    "calories": 550,
    "protein_g": 25,
    "carbs_g": 65,
    "fat_g": 20
  },
  "tags": ["pasta", "italian", "quick-meal"],
  "categories": ["main-course", "italian-cuisine"],
  "is_public": true
}
```

### Recipe Response
```json
{
  "success": true,
  "data": {
    "id": "abc12345-e89b-12d3-a456-426614174000",
    "title": "Spaghetti Carbonara",
    "description": "Classic Italian pasta dish with eggs, cheese, and guanciale",
    "author": {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "username": "johndoe",
      "avatar_url": "https://api.smartrecipe.com/avatars/johndoe.jpg"
    },
    "instructions": [
      {
        "step": 1,
        "text": "Bring a large pot of salted water to boil",
        "time_minutes": 5
      }
    ],
    "prep_time": 10,
    "cook_time": 20,
    "total_time": 30,
    "servings": 4,
    "difficulty": "medium",
    "cuisine": "italian",
    "course": "main",
    "image_url": "https://api.smartrecipe.com/images/carbonara.jpg",
    "ingredients": [
      {
        "ingredient": {
          "id": "456e7890-e89b-12d3-a456-426614174000",
          "name": "Spaghetti",
          "category": "pasta"
        },
        "quantity": 400,
        "unit": "g",
        "notes": "spaghetti or rigatoni"
      }
    ],
    "nutrition": {
      "calories": 550,
      "protein_g": 25,
      "carbs_g": 65,
      "fat_g": 20,
      "fiber_g": 2,
      "sugar_g": 3,
      "sodium_mg": 450
    },
    "tags": [
      {"id": "tag1", "name": "pasta", "slug": "pasta"},
      {"id": "tag2", "name": "italian", "slug": "italian"}
    ],
    "categories": [
      {"id": "cat1", "name": "Main Course", "slug": "main-course"}
    ],
    "rating": {
      "average": 4.5,
      "count": 127
    },
    "stats": {
      "view_count": 3456,
      "fork_count": 23,
      "favorite_count": 89
    },
    "is_public": true,
    "is_favorite": false,
    "user_rating": null,
    "created_at": "2025-07-07T14:30:00Z",
    "updated_at": "2025-07-07T14:30:00Z"
  }
}
```

### Search Recipes Request
```json
{
  "query": "pasta",
  "filters": {
    "dietary": ["vegetarian"],
    "cuisine": ["italian"],
    "difficulty": ["easy", "medium"],
    "prep_time_max": 30,
    "ingredients_include": ["tomato", "basil"],
    "ingredients_exclude": ["nuts"]
  },
  "sort": "rating",
  "order": "desc",
  "page": 1,
  "limit": 20
}
```

### Recipe By Ingredients Request
```json
{
  "available_ingredients": [
    "456e7890-e89b-12d3-a456-426614174000",
    "789e0123-e89b-12d3-a456-426614174000"
  ],
  "match_threshold": 0.7,
  "include_partial_matches": true,
  "dietary_preferences": ["vegetarian"]
}
```

## User Preference Schemas

### Update Dietary Preferences Request
```json
{
  "dietary_preferences": ["vegetarian", "gluten-free"],
  "allergies": ["nuts", "shellfish"],
  "disliked_ingredients": ["cilantro", "olives"],
  "preferred_cuisines": ["italian", "mexican", "thai"],
  "cooking_skill": "intermediate",
  "kitchen_equipment": ["oven", "stovetop", "instant-pot"]
}
```

## Pantry Management Schemas

### Add Pantry Item Request
```json
{
  "ingredient_id": "456e7890-e89b-12d3-a456-426614174000",
  "quantity": 2,
  "unit": "kg",
  "expiration_date": "2025-07-15"
}
```

### Pantry Response
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "pantry123-e89b-12d3-a456-426614174000",
        "ingredient": {
          "id": "456e7890-e89b-12d3-a456-426614174000",
          "name": "All-purpose flour",
          "category": "baking"
        },
        "quantity": 2,
        "unit": "kg",
        "expiration_date": "2025-07-15",
        "days_until_expiry": 8,
        "added_date": "2025-06-01T10:00:00Z"
      }
    ],
    "expiring_soon": [
      {
        "ingredient_name": "Milk",
        "days_until_expiry": 2
      }
    ]
  }
}
```

## Meal Planning Schemas

### Create Meal Plan Request
```json
{
  "name": "Weekly Healthy Meals",
  "start_date": "2025-07-08",
  "end_date": "2025-07-14",
  "meals": [
    {
      "recipe_id": "abc12345-e89b-12d3-a456-426614174000",
      "date": "2025-07-08",
      "meal_type": "dinner",
      "servings": 4
    }
  ],
  "auto_generate": {
    "enabled": true,
    "preferences": {
      "variety": "high",
      "use_pantry": true,
      "budget_per_meal": 10
    }
  }
}
```

## Shopping List Schemas

### Generate Shopping List Request
```json
{
  "meal_plan_id": "mealplan123-e89b-12d3-a456-426614174000",
  "exclude_pantry_items": true,
  "group_by_category": true,
  "include_prices": true
}
```

### Shopping List Response
```json
{
  "success": true,
  "data": {
    "id": "shop123-e89b-12d3-a456-426614174000",
    "name": "Weekly Shopping - Jul 8-14",
    "categories": {
      "produce": [
        {
          "ingredient": "Tomatoes",
          "quantity": 2,
          "unit": "kg",
          "estimated_price": 4.99,
          "recipes_needed_for": ["Pasta Sauce", "Greek Salad"]
        }
      ],
      "dairy": [
        {
          "ingredient": "Parmesan Cheese",
          "quantity": 200,
          "unit": "g",
          "estimated_price": 6.99,
          "recipes_needed_for": ["Carbonara"]
        }
      ]
    },
    "total_items": 15,
    "estimated_total": 67.45,
    "created_at": "2025-07-07T15:00:00Z"
  }
}
```

## Validation Rules

### Common Validation
- Email: Valid email format
- Username: 3-30 characters, alphanumeric + underscore
- Password: Min 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special
- Strings: Max 255 chars unless specified
- Text fields: Max 5000 chars
- URLs: Valid URL format
- Dates: ISO 8601 format
- UUIDs: Valid UUID v4 format

### Recipe Validation
- Title: Required, 3-200 characters
- Instructions: At least 1 step required
- Prep/Cook time: Non-negative integers
- Servings: 1-100
- Ingredients: At least 1 required
- Quantity: Positive number
- Rating: 1-5 integer

### File Upload Validation
- Images: JPEG, PNG, WebP only
- Max size: 10MB
- Videos: MP4, WebM only
- Max video size: 100MB
