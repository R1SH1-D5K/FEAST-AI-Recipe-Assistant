"""
Spoonacular API Integration
Handles recipe searches and retrievals via Spoonacular API
"""

import httpx
import asyncio
import json
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

from config import SPOONACULAR_API_KEY, SPOONACULAR_BASE_URL
from core.models import Recipe, Ingredient, Nutrition


# Compatibility stub to keep API surface stable; no quota tracking is performed.
def get_remaining_quota() -> int:
    return 999


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class RecipePreview:
    """Lightweight recipe preview for card display - NO full details"""
    id: str
    title: str
    image_url: str
    cuisine: str
    ready_in_minutes: int
    servings: int
    ingredients_preview: list[str]  # First 5-7 ingredient names only
    missing_ingredients: list[str]
    used_ingredients: list[str]
    difficulty: str  # easy, medium, hard based on time/steps
    tags: list[str]
    match_score: float
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "image_url": self.image_url,
            "cuisine": self.cuisine,
            "ready_in_minutes": self.ready_in_minutes,
            "servings": self.servings,
            "ingredients_preview": self.ingredients_preview,
            "missing_ingredients": self.missing_ingredients,
            "used_ingredients": self.used_ingredients,
            "difficulty": self.difficulty,
            "tags": self.tags,
            "match_score": self.match_score,
            "is_preview": True
        }


@dataclass  
class ScoredRecipe:
    """Full recipe with relevance score - for expanded view"""
    recipe: Recipe
    score: float
    ingredient_matches: list[str]
    missing_ingredients: list[str]
    
    def to_dict(self) -> dict:
        return {
            "recipe": self.recipe.to_dict(),
            "score": self.score,
            "ingredient_matches": self.ingredient_matches,
            "missing_ingredients": self.missing_ingredients,
            "is_preview": False
        }


# ============================================================================
# SPOONACULAR API CLIENT
# ============================================================================

class SpoonacularAPI:
    """Wrapper for Spoonacular API calls"""
    
    def __init__(self):
        self.api_key = SPOONACULAR_API_KEY
        self.base_url = SPOONACULAR_BASE_URL
        self.timeout = 30.0
        self.max_retries = 3
        self.retry_delay = 1.0
        # Simple in-memory cache
        self._cache: dict = {}
        self._cache_ttl = 300  # 5 minutes
    
    def _cache_key(self, endpoint: str, params: dict) -> str:
        """Generate cache key"""
        param_str = json.dumps(sorted(params.items()), default=str)
        return f"{endpoint}:{param_str}"
    
    def _get_cached(self, key: str) -> Optional[dict]:
        """Get cached result if valid"""
        if key in self._cache:
            result, timestamp = self._cache[key]
            if (datetime.now() - timestamp).seconds < self._cache_ttl:
                return result
            del self._cache[key]
        return None
    
    def _set_cache(self, key: str, result: dict):
        """Cache a result"""
        self._cache[key] = (result, datetime.now())
        # Limit cache size
        if len(self._cache) > 100:
            oldest = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest]
    
    def _add_api_key(self, params: dict) -> dict:
        """Add API key to request parameters"""
        params = params.copy()
        params["apiKey"] = self.api_key
        return params
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: dict = None,
        points_cost: int = 1,
        use_cache: bool = True
    ) -> Optional[dict]:
        """Make an API request with retry logic"""
        params = params or {}
        
        # Check cache first
        cache_key = self._cache_key(endpoint, params)
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached
        
        params = self._add_api_key(params)
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    if method.upper() == "GET":
                        response = await client.get(url, params=params)
                    else:
                        response = await client.post(url, params=params)
                    
                    response.raise_for_status()
                    result = response.json()
                    
                    # Cache result
                    if use_cache:
                        self._set_cache(cache_key, result)
                    
                    return result
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 402:
                    print("Spoonacular quota exceeded (402)")
                    return None
                if e.response.status_code in [429, 500, 502, 503, 522]:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                print(f"Spoonacular API error: {e.response.status_code}")
                return None
            except httpx.TimeoutException:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                print("Spoonacular API timeout")
                return None
            except Exception as e:
                print(f"Spoonacular API error: {e}")
                return None
        
        return None

    # ========================================================================
    # SEARCH ENDPOINTS
    # ========================================================================
    
    async def search_by_ingredients(
        self,
        ingredients: list[str],
        number: int = 5,
        ranking: int = 1,
        ignore_pantry: bool = True
    ) -> list[dict]:
        """
        Find recipes by ingredients - CHEAPEST option (1 point per result)
        Returns basic info + used/missing ingredients
        Best for: "What can I make with chicken, rice, and broccoli?"
        """
        params = {
            "ingredients": ",".join(ingredients),
            "number": min(number, 10),  # Limit to save quota
            "ranking": ranking,
            "ignorePantry": ignore_pantry
        }
        
        result = await self._make_request(
            "GET", 
            "/recipes/findByIngredients", 
            params,
            points_cost=number  # ~1 point per result
        )
        return result if result else []
    
    async def complex_search_preview(
        self,
        query: str = "",
        cuisine: str = "",
        diet: str = "",
        intolerances: str = "",
        meal_type: str = "",
        max_ready_time: int = None,
        number: int = 5
    ) -> list[dict]:
        """
        Complex search for PREVIEWS only - minimal data to save quota
        Does NOT include full recipe info (saves points)
        Best for: dish name, cuisine, diet, meal type searches
        """
        params = {
            "number": min(number, 10),
            "addRecipeInformation": True,  # Need basic info for previews
            "fillIngredients": False,  # Skip detailed ingredients
            "addRecipeNutrition": False,  # Skip nutrition
            "instructionsRequired": True
        }
        
        if query:
            params["query"] = query
        if cuisine:
            params["cuisine"] = cuisine
        if diet:
            params["diet"] = diet
        if intolerances:
            params["intolerances"] = intolerances
        if meal_type:
            params["type"] = meal_type
        if max_ready_time:
            params["maxReadyTime"] = max_ready_time
        
        result = await self._make_request(
            "GET",
            "/recipes/complexSearch",
            params,
            points_cost=number + 1  # Base + per result
        )
        return result.get("results", []) if result else []
    
    async def get_random_recipes(
        self,
        number: int = 3,
        tags: str = ""
    ) -> list[dict]:
        """
        Get random recipes for inspiration/discovery
        Best for: "Show me something interesting" or "I need ideas"
        """
        params = {"number": min(number, 5)}  # Limit to save quota
        if tags:
            params["tags"] = tags
        
        result = await self._make_request(
            "GET",
            "/recipes/random",
            params,
            points_cost=number
        )
        return result.get("recipes", []) if result else []

    # ========================================================================
    # DETAIL ENDPOINTS (Call only when user selects a recipe)
    # ========================================================================
    
    async def get_recipe_details(self, recipe_id: int) -> Optional[dict]:
        """
        Get FULL recipe details - call only when user wants to see a recipe
        Includes: ingredients, instructions, nutrition
        Cost: 1 point
        """
        params = {"includeNutrition": True}
        
        return await self._make_request(
            "GET",
            f"/recipes/{recipe_id}/information",
            params,
            points_cost=1
        )
    
    async def get_recipes_bulk(self, recipe_ids: list[int]) -> list[dict]:
        """
        Get multiple recipe details in one call - more efficient
        Cost: 1 point per recipe (but single HTTP call)
        """
        if not recipe_ids:
            return []
        
        # Limit to 5 recipes per bulk call
        recipe_ids = recipe_ids[:5]
        
        params = {
            "ids": ",".join(str(id) for id in recipe_ids),
            "includeNutrition": True
        }
        
        result = await self._make_request(
            "GET",
            "/recipes/informationBulk",
            params,
            points_cost=len(recipe_ids)
        )
        return result if result else []

    # ========================================================================
    # UTILITY ENDPOINTS
    # ========================================================================
    
    async def autocomplete_ingredient(self, query: str, number: int = 5) -> list[dict]:
        """Autocomplete ingredient names (cheap: ~0.5 points)"""
        params = {"query": query, "number": min(number, 5)}
        result = await self._make_request(
            "GET",
            "/food/ingredients/autocomplete",
            params,
            points_cost=1
        )
        return result if result else []
    
    async def get_ingredient_substitutes(self, ingredient: str) -> dict:
        """Get substitutes for an ingredient (1 point)"""
        params = {"ingredientName": ingredient}
        result = await self._make_request(
            "GET",
            "/food/ingredients/substitutes",
            params,
            points_cost=1
        )
        return result if result else {}


# Global API instance
spoonacular_api = SpoonacularAPI()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def estimate_difficulty(ready_in_minutes: int, num_ingredients: int = 0) -> str:
    """Estimate recipe difficulty based on time and ingredients"""
    if ready_in_minutes <= 20:
        return "easy"
    elif ready_in_minutes <= 45:
        return "medium"
    else:
        return "hard"


def create_recipe_preview(data: dict, used_ings: list = None, missing_ings: list = None) -> RecipePreview:
    """Create a lightweight preview from Spoonacular data"""
    # Get basic info
    ready_in = data.get("readyInMinutes", 30)
    
    # Extract ingredient names for preview (just names, not full details)
    ingredient_names = []
    if "extendedIngredients" in data:
        ingredient_names = [ing.get("name", "") for ing in data.get("extendedIngredients", [])[:7]]
    elif "usedIngredients" in data:
        # From findByIngredients response
        ingredient_names = [ing.get("name", "") for ing in data.get("usedIngredients", [])[:4]]
        ingredient_names += [ing.get("name", "") for ing in data.get("missedIngredients", [])[:3]]
    
    # Build tags
    tags = []
    tags.extend(data.get("dishTypes", [])[:3])
    tags.extend(data.get("diets", [])[:2])
    
    # Get cuisine
    cuisines = data.get("cuisines", [])
    cuisine = cuisines[0] if cuisines else ""
    
    # Calculate match score
    used_count = len(used_ings) if used_ings else data.get("usedIngredientCount", 0)
    missed_count = len(missing_ings) if missing_ings else data.get("missedIngredientCount", 0)
    total = used_count + missed_count
    match_score = round((used_count / total * 100) if total > 0 else 50, 1)
    
    return RecipePreview(
        id=f"spoonacular_{data.get('id', '')}",
        title=data.get("title", ""),
        image_url=data.get("image", ""),
        cuisine=cuisine,
        ready_in_minutes=ready_in,
        servings=data.get("servings", 4),
        ingredients_preview=ingredient_names,
        missing_ingredients=[ing.get("name", "") for ing in data.get("missedIngredients", [])] if "missedIngredients" in data else (missing_ings or []),
        used_ingredients=[ing.get("name", "") for ing in data.get("usedIngredients", [])] if "usedIngredients" in data else (used_ings or []),
        difficulty=estimate_difficulty(ready_in, len(ingredient_names)),
        tags=tags,
        match_score=match_score
    )


def convert_to_full_recipe(data: dict) -> Recipe:
    """Convert Spoonacular API response to full Recipe model"""
    import re
    
    # Parse ingredients
    ingredients = []
    for ing in data.get("extendedIngredients", []):
        ingredients.append(Ingredient(
            name=ing.get("name", ""),
            quantity=str(ing.get("amount", "")),
            unit=ing.get("unit", ""),
            original=ing.get("original", "")
        ))
    
    # Parse instructions
    instructions = []
    analyzed = data.get("analyzedInstructions", [])
    if analyzed:
        for section in analyzed:
            for step in section.get("steps", []):
                step_text = step.get("step", "").strip()
                if step_text:
                    instructions.append(step_text)
    
    # Fallback to plain instructions
    if not instructions and data.get("instructions"):
        raw = data.get("instructions", "")
        raw = re.sub(r'<[^>]+>', '\n', raw)
        steps = re.split(r'\n+|\d+\.', raw)
        instructions = [s.strip() for s in steps if s.strip()]
    
    # Parse nutrition
    nutrition = None
    nutr_data = data.get("nutrition", {})
    if nutr_data:
        nutrients = {n.get("name", "").lower(): n.get("amount") for n in nutr_data.get("nutrients", [])}
        nutrition = Nutrition(
            calories=nutrients.get("calories"),
            protein=nutrients.get("protein"),
            carbs=nutrients.get("carbohydrates"),
            fat=nutrients.get("fat"),
            fiber=nutrients.get("fiber"),
            sugar=nutrients.get("sugar"),
            sodium=nutrients.get("sodium")
        )
    
    # Tags
    tags = []
    tags.extend(data.get("cuisines", []))
    tags.extend(data.get("diets", []))
    tags.extend(data.get("dishTypes", []))
    
    cuisines = data.get("cuisines", [])
    cuisine = cuisines[0] if cuisines else "International"
    
    dish_types = data.get("dishTypes", [])
    category = dish_types[0] if dish_types else ""
    
    return Recipe(
        id=f"spoonacular_{data.get('id', '')}",
        title=data.get("title", ""),
        ingredients=ingredients,
        instructions=instructions,
        cuisine=cuisine,
        source="Spoonacular",
        source_id=str(data.get("id", "")),
        category=category,
        tags=tags,
        image_url=data.get("image", ""),
        source_url=data.get("sourceUrl", ""),
        youtube_url="",
        nutrition=nutrition
    )


# ============================================================================
# HIGH-LEVEL SEARCH FUNCTIONS (Smart endpoint selection)
# ============================================================================

async def search_by_ingredients_smart(
    ingredients: list[str],
    allergies: list[str] = None,
    limit: int = 5
) -> list[RecipePreview]:
    """
    Search recipes by ingredients user has - returns PREVIEWS only
    Uses findByIngredients (most quota-efficient for this use case)
    """
    results = await spoonacular_api.search_by_ingredients(
        ingredients=ingredients,
        number=limit,
        ranking=1  # Maximize used ingredients
    )
    
    previews = []
    for item in results:
        preview = create_recipe_preview(item)
        previews.append(preview)
    
    return previews


async def search_recipes_smart(
    query: str = "",
    cuisine: str = "",
    diet: str = "",
    allergies: list[str] = None,
    meal_type: str = "",
    max_time: int = None,
    limit: int = 5
) -> list[RecipePreview]:
    """
    General recipe search - returns PREVIEWS only
    Uses complexSearch for queries, dish names, cuisines, etc.
    """
    # Map allergies to intolerances
    intolerance_map = {
        "dairy": "dairy", "milk": "dairy", "lactose": "dairy",
        "egg": "egg", "eggs": "egg",
        "gluten": "gluten", "wheat": "gluten",
        "peanut": "peanut", "peanuts": "peanut",
        "tree nut": "tree nut", "nuts": "tree nut",
        "shellfish": "shellfish", "shrimp": "shellfish",
        "fish": "seafood", "seafood": "seafood",
        "soy": "soy", "sesame": "sesame"
    }
    
    intolerances = ""
    if allergies:
        mapped = [intolerance_map.get(a.lower(), a.lower()) for a in allergies]
        intolerances = ",".join(set(mapped))
    
    results = await spoonacular_api.complex_search_preview(
        query=query,
        cuisine=cuisine.lower() if cuisine else "",
        diet=diet.lower() if diet else "",
        intolerances=intolerances,
        meal_type=meal_type.lower() if meal_type else "",
        max_ready_time=max_time,
        number=limit
    )
    
    previews = []
    for item in results:
        preview = create_recipe_preview(item)
        previews.append(preview)
    
    return previews


async def get_random_inspiration(
    number: int = 3,
    tags: str = ""
) -> list[RecipePreview]:
    """
    Get random recipes for discovery - returns PREVIEWS only
    """
    results = await spoonacular_api.get_random_recipes(number=number, tags=tags)
    
    previews = []
    for item in results:
        preview = create_recipe_preview(item)
        previews.append(preview)
    
    return previews


async def get_full_recipe(recipe_id: str) -> Optional[ScoredRecipe]:
    """
    Get FULL recipe details when user selects a preview
    Only call this when user actually wants to see the full recipe
    """
    # Extract numeric ID
    numeric_id = recipe_id.replace("spoonacular_", "") if recipe_id.startswith("spoonacular_") else recipe_id
    
    try:
        numeric_id = int(numeric_id)
    except ValueError:
        return None
    
    details = await spoonacular_api.get_recipe_details(numeric_id)
    if not details:
        return None
    
    recipe = convert_to_full_recipe(details)
    
    return ScoredRecipe(
        recipe=recipe,
        score=80.0,  # Default score for direct fetch
        ingredient_matches=[],
        missing_ingredients=[]
    )


# ============================================================================
# LEGACY COMPATIBILITY FUNCTIONS
# ============================================================================

async def search_spoonacular_recipes(
    query: str = "",
    ingredients: list[str] = None,
    cuisine: str = "",
    allergies: list[str] = None,
    dietary_restrictions: list[str] = None,
    max_time: int = None,
    limit: int = 5
) -> list[ScoredRecipe]:
    """
    Legacy search function - returns PREVIEWS as ScoredRecipe for compatibility
    Does NOT fetch full details (saves quota)
    """
    # Determine best search strategy
    if ingredients and len(ingredients) > 0 and not query:
        previews = await search_by_ingredients_smart(ingredients, allergies, limit)
    else:
        diet = dietary_restrictions[0] if dietary_restrictions else ""
        previews = await search_recipes_smart(
            query=query,
            cuisine=cuisine,
            diet=diet,
            allergies=allergies,
            max_time=max_time,
            limit=limit
        )
    
    # Convert previews to ScoredRecipe format (without full details)
    scored = []
    for preview in previews:
        # Create minimal Recipe object from preview
        recipe = Recipe(
            id=preview.id,
            title=preview.title,
            ingredients=[],  # Empty - will be filled on expand
            instructions=[],  # Empty - will be filled on expand
            cuisine=preview.cuisine,
            source="Spoonacular",
            source_id=preview.id.replace("spoonacular_", ""),
            category="",
            tags=preview.tags,
            image_url=preview.image_url,
            source_url="",
            youtube_url="",
            nutrition=None
        )
        
        scored.append(ScoredRecipe(
            recipe=recipe,
            score=preview.match_score,
            ingredient_matches=preview.used_ingredients,
            missing_ingredients=preview.missing_ingredients
        ))
    
    return scored


async def get_recipe_by_id(recipe_id: str) -> Optional[Recipe]:
    """Legacy function - get full recipe by ID"""
    result = await get_full_recipe(recipe_id)
    return result.recipe if result else None


async def get_random_recipes(number: int = 3, tags: str = "") -> list[Recipe]:
    """Legacy function - get random recipes (as previews converted to Recipe)"""
    previews = await get_random_inspiration(number=number, tags=tags)
    recipes = []
    for preview in previews:
        # Create minimal Recipe from preview
        recipe = Recipe(
            id=preview.id,
            title=preview.title,
            ingredients=[],
            instructions=[],
            cuisine=preview.cuisine,
            source="Spoonacular",
            source_id=preview.id.replace("spoonacular_", ""),
            category="",
            tags=preview.tags,
            image_url=preview.image_url,
            source_url="",
            youtube_url="",
            nutrition=None
        )
        recipes.append(recipe)
    return recipes
