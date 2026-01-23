"""
FEAST Backend - FastAPI Application
Main entry point for the recipe assistant API
Now powered by Spoonacular API for recipe retrieval
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from config import CORS_ORIGINS
from core.conversation import (
    process_conversation,
    ConversationContext,
)
from core.llm import LLMError
from core.spoonacular import (
    spoonacular_api,
    search_spoonacular_recipes,
    get_recipe_by_id as spoonacular_get_recipe,
    get_random_recipes,
    get_full_recipe,
    get_remaining_quota
)


# Initialize FastAPI app
app = FastAPI(
    title="FEAST API",
    description="AI Recipe Assistant Backend - Powered by Spoonacular API",
    version="3.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS + ["*"],  # Allow all in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class ChatRequest(BaseModel):
    message: str
    conversation_history: list[dict] = []
    context: Optional[dict] = None  # Conversation context from frontend


class ChatResponse(BaseModel):
    message: str
    recipes: list[dict] = []  # Can return multiple recipe suggestions
    context: dict = {}  # Updated context to store on frontend
    error: Optional[str] = None
    quota_remaining: int = 150  # Track API quota


class HealthResponse(BaseModel):
    status: str
    recipe_count: int
    quota_remaining: int = 150


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "FEAST API is running", 
        "version": "3.1.0", 
        "backend": "Spoonacular",
        "quota_remaining": get_remaining_quota()
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Get remaining quota without making an API call
        quota = get_remaining_quota()
        status = "healthy" if quota > 10 else "low_quota" if quota > 0 else "quota_exhausted"
        return HealthResponse(
            status=status,
            recipe_count=-1,  # Spoonacular has millions, we don't track count
            quota_remaining=quota
        )
    except Exception as e:
        print(f"Health check error: {e}")
        return HealthResponse(
            status="unhealthy",
            recipe_count=0,
            quota_remaining=0
        )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint - conversation-first approach.
    The LLM drives the conversation and decides when to search for recipes.
    """
    try:
        # Restore context from request or create new
        if request.context:
            context = ConversationContext(
                ingredients=request.context.get("ingredients", []),
                allergies=request.context.get("allergies", []),
                cuisine_preference=request.context.get("cuisine_preference", ""),
                dietary_restrictions=request.context.get("dietary_restrictions", []),
                meal_type=request.context.get("meal_type", ""),
                cooking_time=request.context.get("cooking_time", ""),
                skill_level=request.context.get("skill_level", ""),
                servings=request.context.get("servings", 0),
                flavor_preferences=request.context.get("flavor_preferences", []),
                dislikes=request.context.get("dislikes", []),
                last_recommended_recipes=request.context.get("last_recommended_recipes", [])
            )
        else:
            context = ConversationContext()
        
        # Process the conversation
        response_text, recipes, updated_context = await process_conversation(
            user_message=request.message,
            conversation_history=request.conversation_history,
            context=context
        )
        
        # Format recipes for response
        recipe_dicts = []
        if recipes:
            for scored_recipe in recipes:
                recipe_dict = scored_recipe.recipe.to_dict()
                recipe_dict["match_score"] = scored_recipe.score
                recipe_dict["matched_ingredients"] = scored_recipe.ingredient_matches
                recipe_dict["missing_ingredients"] = scored_recipe.missing_ingredients
                recipe_dicts.append(recipe_dict)
        
        # Serialize context for frontend storage
        context_dict = {
            "ingredients": updated_context.ingredients,
            "allergies": updated_context.allergies,
            "cuisine_preference": updated_context.cuisine_preference,
            "dietary_restrictions": updated_context.dietary_restrictions,
            "meal_type": updated_context.meal_type,
            "cooking_time": updated_context.cooking_time,
            "skill_level": updated_context.skill_level,
            "servings": updated_context.servings,
            "flavor_preferences": updated_context.flavor_preferences,
            "dislikes": updated_context.dislikes,
            "last_recommended_recipes": [r.recipe.id for r in recipes] if recipes else []
        }
        
        # Enforce RESPONSE-only output at API boundary
        from core.conversation import strip_structured_tags
        safe_message = strip_structured_tags(response_text)
        return ChatResponse(
            message=safe_message,
            recipes=recipe_dicts,
            context=context_dict,
            error=None,
            quota_remaining=get_remaining_quota()
        )
        
    except LLMError as e:
        return ChatResponse(
            message="I'm having trouble connecting right now. Please try again in a moment.",
            recipes=[],
            context={},
            error=str(e),
            quota_remaining=get_remaining_quota()
        )
    except Exception as e:
        print(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recipe/{recipe_id}")
async def get_recipe(recipe_id: str):
    """Get a specific recipe by ID from Spoonacular"""
    recipe = await spoonacular_get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe.to_dict()


@app.get("/recipe/{recipe_id}/expand")
async def expand_recipe(recipe_id: str):
    """
    Get full recipe details when user clicks 'View Full Recipe' on a preview.
    This is the main quota-consuming call - only happens when user selects a recipe.
    """
    try:
        result = await get_full_recipe(recipe_id)
        if not result:
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        recipe_dict = result.recipe.to_dict()
        recipe_dict["match_score"] = result.score
        recipe_dict["matched_ingredients"] = result.ingredient_matches
        recipe_dict["missing_ingredients"] = result.missing_ingredients
        recipe_dict["quota_remaining"] = get_remaining_quota()
        
        return recipe_dict
    except Exception as e:
        print(f"Expand recipe error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/quota")
async def get_quota():
    """Get current API quota status"""
    return {
        "remaining": get_remaining_quota(),
        "daily_limit": 150,
        "status": "ok" if get_remaining_quota() > 10 else "low"
    }


@app.get("/recipes/random")
async def random_recipes(count: int = 5, tags: str = ""):
    """Get random recipes from Spoonacular"""
    try:
        recipes = await get_random_recipes(number=count, tags=tags)
        return [r.to_dict() for r in recipes]
    except Exception as e:
        print(f"Random recipes error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recipes/search")
async def search_recipes(
    query: str = "",
    cuisine: str = "",
    diet: str = "",
    intolerances: str = "",
    ingredients: str = "",
    maxTime: int = None,
    limit: int = 10
):
    """Search recipes via Spoonacular API"""
    try:
        ingredient_list = [i.strip() for i in ingredients.split(",")] if ingredients else None
        allergy_list = [i.strip() for i in intolerances.split(",")] if intolerances else None
        diet_list = [diet] if diet else None
        
        results = await search_spoonacular_recipes(
            query=query,
            ingredients=ingredient_list,
            cuisine=cuisine,
            allergies=allergy_list,
            dietary_restrictions=diet_list,
            max_time=maxTime,
            limit=limit
        )
        
        return [r.to_dict() for r in results]
    except Exception as e:
        print(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    print("🍳 FEAST Backend v3.0 started - Powered by Spoonacular API")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
