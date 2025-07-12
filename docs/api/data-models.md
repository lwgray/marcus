# Data Models for Recipe Management System

## Core Entities

### User Model
```python
User {
  id: UUID (primary key)
  email: String (unique, required)
  username: String (unique, required)
  password_hash: String (required)
  first_name: String
  last_name: String
  avatar_url: String
  bio: Text
  is_active: Boolean (default: true)
  is_verified: Boolean (default: false)
  created_at: DateTime
  updated_at: DateTime
  last_login: DateTime

  # Relationships
  recipes: [Recipe]
  favorites: [Recipe]
  ratings: [Rating]
  comments: [Comment]
  pantry_items: [PantryItem]
  meal_plans: [MealPlan]
  dietary_preferences: [DietaryPreference]
}
```

### Recipe Model
```python
Recipe {
  id: UUID (primary key)
  title: String (required, indexed)
  description: Text
  instructions: JSON (array of steps)
  prep_time: Integer (minutes)
  cook_time: Integer (minutes)
  total_time: Integer (computed)
  servings: Integer
  difficulty: Enum (easy, medium, hard)
  cuisine: String
  course: Enum (appetizer, main, dessert, snack, drink)
  image_url: String
  video_url: String
  source_url: String
  is_public: Boolean (default: true)
  view_count: Integer (default: 0)
  fork_count: Integer (default: 0)
  created_at: DateTime
  updated_at: DateTime

  # Foreign Keys
  author_id: UUID (references User)
  forked_from_id: UUID (references Recipe, nullable)

  # Relationships
  author: User
  ingredients: [RecipeIngredient]
  nutrition: NutritionInfo
  tags: [Tag]
  ratings: [Rating]
  comments: [Comment]
  categories: [Category]
}
```

### Ingredient Model
```python
Ingredient {
  id: UUID (primary key)
  name: String (unique, required, indexed)
  description: Text
  category: String (produce, dairy, meat, etc.)
  unit_type: Enum (weight, volume, count)
  calories_per_100g: Float
  image_url: String

  # Relationships
  recipe_ingredients: [RecipeIngredient]
  substitutes: [Ingredient] (many-to-many)
}
```

### RecipeIngredient Model (Junction Table)
```python
RecipeIngredient {
  id: UUID (primary key)
  recipe_id: UUID (references Recipe)
  ingredient_id: UUID (references Ingredient)
  quantity: Float (required)
  unit: String (cup, tbsp, g, ml, etc.)
  notes: String (optional, e.g., "finely chopped")
  is_optional: Boolean (default: false)

  # Relationships
  recipe: Recipe
  ingredient: Ingredient
}
```

### NutritionInfo Model
```python
NutritionInfo {
  id: UUID (primary key)
  recipe_id: UUID (references Recipe, unique)
  calories: Float
  protein_g: Float
  carbs_g: Float
  fat_g: Float
  fiber_g: Float
  sugar_g: Float
  sodium_mg: Float
  cholesterol_mg: Float

  # Relationship
  recipe: Recipe
}
```

### Rating Model
```python
Rating {
  id: UUID (primary key)
  user_id: UUID (references User)
  recipe_id: UUID (references Recipe)
  score: Integer (1-5)
  created_at: DateTime
  updated_at: DateTime

  # Unique constraint on (user_id, recipe_id)

  # Relationships
  user: User
  recipe: Recipe
}
```

### Comment Model
```python
Comment {
  id: UUID (primary key)
  user_id: UUID (references User)
  recipe_id: UUID (references Recipe)
  content: Text (required)
  created_at: DateTime
  updated_at: DateTime

  # Relationships
  user: User
  recipe: Recipe
  parent_comment: Comment (self-reference for replies)
  replies: [Comment]
}
```

### PantryItem Model
```python
PantryItem {
  id: UUID (primary key)
  user_id: UUID (references User)
  ingredient_id: UUID (references Ingredient)
  quantity: Float
  unit: String
  expiration_date: Date
  added_date: DateTime

  # Relationships
  user: User
  ingredient: Ingredient
}
```

### MealPlan Model
```python
MealPlan {
  id: UUID (primary key)
  user_id: UUID (references User)
  name: String
  start_date: Date
  end_date: Date
  created_at: DateTime
  updated_at: DateTime

  # Relationships
  user: User
  meals: [MealPlanRecipe]
}
```

### MealPlanRecipe Model (Junction Table)
```python
MealPlanRecipe {
  id: UUID (primary key)
  meal_plan_id: UUID (references MealPlan)
  recipe_id: UUID (references Recipe)
  date: Date
  meal_type: Enum (breakfast, lunch, dinner, snack)
  servings: Integer

  # Relationships
  meal_plan: MealPlan
  recipe: Recipe
}
```

### ShoppingList Model
```python
ShoppingList {
  id: UUID (primary key)
  user_id: UUID (references User)
  name: String
  created_at: DateTime
  completed_at: DateTime (nullable)

  # Relationships
  user: User
  items: [ShoppingListItem]
}
```

### ShoppingListItem Model
```python
ShoppingListItem {
  id: UUID (primary key)
  shopping_list_id: UUID (references ShoppingList)
  ingredient_id: UUID (references Ingredient)
  quantity: Float
  unit: String
  is_purchased: Boolean (default: false)

  # Relationships
  shopping_list: ShoppingList
  ingredient: Ingredient
}
```

### Tag Model
```python
Tag {
  id: UUID (primary key)
  name: String (unique, required)
  slug: String (unique, required)

  # Relationships
  recipes: [Recipe] (many-to-many)
}
```

### Category Model
```python
Category {
  id: UUID (primary key)
  name: String (unique, required)
  slug: String (unique, required)
  description: Text
  parent_id: UUID (references Category, nullable)

  # Relationships
  parent: Category
  children: [Category]
  recipes: [Recipe] (many-to-many)
}
```

### DietaryPreference Model
```python
DietaryPreference {
  id: UUID (primary key)
  name: String (unique, required)
  code: String (unique, required)
  description: Text

  # Relationships
  users: [User] (many-to-many)
  excluded_ingredients: [Ingredient] (many-to-many)
}
```

## Database Indexes

### Performance Indexes
- User: email, username
- Recipe: title, author_id, created_at, cuisine
- Ingredient: name
- RecipeIngredient: (recipe_id, ingredient_id) - composite unique
- Rating: (user_id, recipe_id) - composite unique
- Tag: name, slug
- Category: name, slug

### Full-Text Search Indexes
- Recipe: title, description
- Ingredient: name
- Comment: content

## Relationships Summary

### One-to-Many
- User → Recipes (author)
- User → Comments
- User → Ratings
- User → PantryItems
- User → MealPlans
- User → ShoppingLists
- Recipe → RecipeIngredients
- Recipe → Comments
- Recipe → Ratings
- MealPlan → MealPlanRecipes
- ShoppingList → ShoppingListItems

### Many-to-Many
- User ↔ Recipe (favorites)
- User ↔ DietaryPreference
- Recipe ↔ Tag
- Recipe ↔ Category
- Ingredient ↔ Ingredient (substitutes)
- DietaryPreference ↔ Ingredient (excluded)

### One-to-One
- Recipe → NutritionInfo
