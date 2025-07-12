# Implementation Examples

## FastAPI Implementation

### Project Structure
```
recipe-api/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── recipe.py
│   │   └── ingredient.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── recipe.py
│   │   └── ingredient.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── recipes.py
│   │   └── users.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py
│   │   ├── exceptions.py
│   │   └── cache.py
│   └── services/
│       ├── __init__.py
│       ├── recipe_service.py
│       └── recommendation_service.py
├── tests/
├── docker-compose.yml
└── requirements.txt
```

### Main Application Setup
```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, recipes, users
from app.core.exceptions import setup_exception_handlers
from app.database import init_db

app = FastAPI(
    title="Smart Recipe Recommender API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup exception handlers
setup_exception_handlers(app)

# Include routers
app.include_router(auth.router, prefix="/v1/auth", tags=["Authentication"])
app.include_router(recipes.router, prefix="/v1/recipes", tags=["Recipes"])
app.include_router(users.router, prefix="/v1/users", tags=["Users"])

@app.on_event("startup")
async def startup_event():
    await init_db()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

### Authentication Implementation
```python
# app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from app.schemas.user import UserCreate, UserLogin, AuthResponse
from app.services.auth_service import AuthService
from app.core.security import create_tokens

router = APIRouter()
auth_service = AuthService()

@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(user_data: UserCreate):
    """Register a new user"""
    user = await auth_service.create_user(user_data)
    tokens = create_tokens(user.id)

    return AuthResponse(
        success=True,
        data={
            "user": user,
            "tokens": tokens
        }
    )

@router.post("/login", response_model=AuthResponse)
async def login(credentials: UserLogin):
    """Login user"""
    user = await auth_service.authenticate_user(
        credentials.email,
        credentials.password
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    tokens = create_tokens(user.id)

    return AuthResponse(
        success=True,
        data={
            "user": user,
            "tokens": tokens
        }
    )
```

### Recipe CRUD Implementation
```python
# app/api/recipes.py
from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from app.schemas.recipe import (
    RecipeCreate, RecipeUpdate, RecipeResponse, RecipeListResponse
)
from app.services.recipe_service import RecipeService
from app.core.security import get_current_user
from app.core.cache import cache_key_wrapper

router = APIRouter()
recipe_service = RecipeService()

@router.get("/", response_model=RecipeListResponse)
@cache_key_wrapper("recipes:list", expire=300)
async def list_recipes(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    dietary: Optional[List[str]] = Query(None),
    cuisine: Optional[str] = None,
    difficulty: Optional[str] = None,
    sort: str = Query("newest", regex="^(popular|newest|rating|prep_time)$")
):
    """List recipes with filters"""
    recipes, total = await recipe_service.list_recipes(
        page=page,
        limit=limit,
        dietary=dietary,
        cuisine=cuisine,
        difficulty=difficulty,
        sort=sort
    )

    return RecipeListResponse(
        success=True,
        data=recipes,
        meta={
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit
        }
    )

@router.post("/", response_model=RecipeResponse, status_code=201)
async def create_recipe(
    recipe_data: RecipeCreate,
    current_user = Depends(get_current_user)
):
    """Create a new recipe"""
    recipe = await recipe_service.create_recipe(
        recipe_data,
        author_id=current_user.id
    )

    return RecipeResponse(
        success=True,
        data=recipe
    )

@router.get("/{recipe_id}", response_model=RecipeResponse)
@cache_key_wrapper("recipe:{recipe_id}", expire=3600)
async def get_recipe(recipe_id: str):
    """Get recipe details"""
    recipe = await recipe_service.get_recipe(recipe_id)

    if not recipe:
        raise HTTPException(
            status_code=404,
            detail="Recipe not found"
        )

    return RecipeResponse(
        success=True,
        data=recipe
    )
```

### Caching Implementation
```python
# app/core/cache.py
import json
import hashlib
from functools import wraps
from typing import Optional
import redis.asyncio as redis

redis_client = redis.from_url("redis://localhost:6379")

def cache_key_wrapper(key_pattern: str, expire: int = 3600):
    """Decorator for caching API responses"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = generate_cache_key(key_pattern, args, kwargs)

            # Try to get from cache
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)

            # Call function and cache result
            result = await func(*args, **kwargs)
            await redis_client.setex(
                cache_key,
                expire,
                json.dumps(result, default=str)
            )

            return result
        return wrapper
    return decorator

def generate_cache_key(pattern: str, args: tuple, kwargs: dict) -> str:
    """Generate cache key from pattern and arguments"""
    # Replace placeholders with actual values
    key = pattern
    for k, v in kwargs.items():
        key = key.replace(f"{{{k}}}", str(v))

    # Add query parameters to key
    if kwargs:
        params = hashlib.md5(
            json.dumps(kwargs, sort_keys=True).encode()
        ).hexdigest()
        key = f"{key}:{params}"

    return key

async def invalidate_cache(pattern: str):
    """Invalidate cache entries matching pattern"""
    async for key in redis_client.scan_iter(match=pattern):
        await redis_client.delete(key)
```

### Database Models
```python
# app/models/recipe.py
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.database import Base

recipe_tags = Table(
    'recipe_tags',
    Base.metadata,
    Column('recipe_id', UUID(as_uuid=True), ForeignKey('recipes.id')),
    Column('tag_id', UUID(as_uuid=True), ForeignKey('tags.id'))
)

class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False, index=True)
    description = Column(String(1000))
    instructions = Column(JSON, nullable=False)
    prep_time = Column(Integer)
    cook_time = Column(Integer)
    servings = Column(Integer)
    difficulty = Column(String(20))
    cuisine = Column(String(50), index=True)
    image_url = Column(String(500))
    is_public = Column(Boolean, default=True)
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Foreign Keys
    author_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    # Relationships
    author = relationship("User", back_populates="recipes")
    ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")
    nutrition = relationship("NutritionInfo", back_populates="recipe", uselist=False, cascade="all, delete-orphan")
    ratings = relationship("Rating", back_populates="recipe", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="recipe", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=recipe_tags, back_populates="recipes")
```

### Recipe Service
```python
# app/services/recipe_service.py
from typing import List, Tuple, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.models.recipe import Recipe
from app.schemas.recipe import RecipeCreate, RecipeUpdate
from app.database import get_session
from app.core.cache import invalidate_cache

class RecipeService:
    async def list_recipes(
        self,
        page: int = 1,
        limit: int = 20,
        dietary: Optional[List[str]] = None,
        cuisine: Optional[str] = None,
        difficulty: Optional[str] = None,
        sort: str = "newest"
    ) -> Tuple[List[Recipe], int]:
        async with get_session() as session:
            query = select(Recipe).options(
                selectinload(Recipe.author),
                selectinload(Recipe.ratings)
            ).filter(Recipe.is_public == True)

            # Apply filters
            if dietary:
                # Join with dietary preferences
                pass

            if cuisine:
                query = query.filter(Recipe.cuisine == cuisine)

            if difficulty:
                query = query.filter(Recipe.difficulty == difficulty)

            # Apply sorting
            if sort == "newest":
                query = query.order_by(Recipe.created_at.desc())
            elif sort == "popular":
                query = query.order_by(Recipe.view_count.desc())
            elif sort == "rating":
                # Join with ratings and order by average
                pass
            elif sort == "prep_time":
                query = query.order_by(Recipe.prep_time)

            # Count total
            count_query = select(func.count()).select_from(query.subquery())
            total = await session.scalar(count_query)

            # Apply pagination
            query = query.offset((page - 1) * limit).limit(limit)

            result = await session.execute(query)
            recipes = result.scalars().all()

            return recipes, total

    async def create_recipe(
        self,
        recipe_data: RecipeCreate,
        author_id: str
    ) -> Recipe:
        async with get_session() as session:
            recipe = Recipe(
                **recipe_data.dict(exclude={"ingredients", "nutrition", "tags"}),
                author_id=author_id
            )

            # Add ingredients
            for ingredient_data in recipe_data.ingredients:
                recipe.ingredients.append(
                    RecipeIngredient(**ingredient_data.dict())
                )

            # Add nutrition info
            if recipe_data.nutrition:
                recipe.nutrition = NutritionInfo(
                    **recipe_data.nutrition.dict()
                )

            session.add(recipe)
            await session.commit()
            await session.refresh(recipe)

            # Invalidate cache
            await invalidate_cache("recipes:list:*")

            return recipe
```

### Docker Compose Setup
```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://recipe:password@postgres:5432/recipedb
      - REDIS_URL=redis://redis:6379
      - SECRET_KEY=your-secret-key
    depends_on:
      - postgres
      - redis
    volumes:
      - ./app:/app
    command: uvicorn app.main:app --host 0.0.0.0 --reload

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=recipe
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=recipedb
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api

volumes:
  postgres_data:
  redis_data:
```

## Testing

### Unit Test Example
```python
# tests/test_recipe_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from app.services.recipe_service import RecipeService
from app.schemas.recipe import RecipeCreate

@pytest.mark.asyncio
async def test_create_recipe():
    # Arrange
    recipe_service = RecipeService()
    recipe_data = RecipeCreate(
        title="Test Recipe",
        instructions=[{"step": 1, "text": "Test step"}],
        ingredients=[{
            "ingredient_id": "123",
            "quantity": 100,
            "unit": "g"
        }]
    )

    # Mock database session
    mock_session = AsyncMock()

    # Act
    recipe = await recipe_service.create_recipe(
        recipe_data,
        author_id="user123"
    )

    # Assert
    assert recipe.title == "Test Recipe"
    assert recipe.author_id == "user123"
```

### Integration Test Example
```python
# tests/integration/test_api.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_recipe_crud_flow():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register user
        register_response = await client.post(
            "/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "TestPass123!"
            }
        )
        assert register_response.status_code == 201
        tokens = register_response.json()["data"]["tokens"]

        # Create recipe
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        create_response = await client.post(
            "/v1/recipes",
            json={
                "title": "Test Recipe",
                "instructions": [{"step": 1, "text": "Cook"}],
                "ingredients": [{
                    "ingredient_id": "123",
                    "quantity": 100,
                    "unit": "g"
                }]
            },
            headers=headers
        )
        assert create_response.status_code == 201
        recipe_id = create_response.json()["data"]["id"]

        # Get recipe
        get_response = await client.get(f"/v1/recipes/{recipe_id}")
        assert get_response.status_code == 200
        assert get_response.json()["data"]["title"] == "Test Recipe"
```
