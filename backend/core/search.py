"""
Recipe Search and Filtering
Now uses Spoonacular API for recipe retrieval
"""

import json
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from config import DATA_DIR, MAX_CANDIDATES
from core.parser import ParsedInput


# Re-export from spoonacular module for backward compatibility
from core.spoonacular import (
    ScoredRecipe,
    Recipe,
    search_spoonacular_recipes,
    get_recipe_by_id as spoonacular_get_recipe
)


def load_allergens() -> dict[str, list[str]]:
    """Load allergen mappings from JSON file"""
    allergens_path = DATA_DIR / "allergens.json"
    if allergens_path.exists():
        with open(allergens_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_synonyms() -> dict[str, list[str]]:
    """Load ingredient synonyms from JSON file"""
    synonyms_path = DATA_DIR / "synonyms.json"
    if synonyms_path.exists():
        with open(synonyms_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


async def filter_recipes(
    parsed_input: ParsedInput,
    limit: int = MAX_CANDIDATES
) -> list[ScoredRecipe]:
    """
    Filter and rank recipes based on user input using Spoonacular API
    
    This is the main search function that takes parsed user input and
    returns a list of scored recipes from Spoonacular.
    """
    # Extract the main dish name from free text
    query = ""
    if parsed_input.free_text:
        # Remove common request patterns to get the dish name
        query = parsed_input.free_text
        query = re.sub(r'^(how to make|recipe for|show me|make me|cook|i want|give me)\s+', '', query, flags=re.IGNORECASE)
        query = re.sub(r'\s+(recipe|recipes|dish|dishes)$', '', query, flags=re.IGNORECASE)
        query = query.strip()
    
    # If no query from free text, try to construct from ingredients
    if not query and parsed_input.ingredients:
        query = " ".join(parsed_input.ingredients)
    
    # Search using Spoonacular
    results = await search_spoonacular_recipes(
        query=query,
        ingredients=parsed_input.ingredients if parsed_input.ingredients else None,
        cuisine=parsed_input.cuisine or "",
        allergies=parsed_input.allergies if parsed_input.allergies else None,
        dietary_restrictions=parsed_input.dietary_goals if parsed_input.dietary_goals else None,
        limit=limit
    )
    
    return results


async def search_recipes_by_name(
    dish_name: str,
    cuisine: str = "",
    limit: int = MAX_CANDIDATES
) -> list[ScoredRecipe]:
    """
    Search for recipes by dish name
    
    This is a simpler search function for when the user directly
    requests a specific dish.
    """
    results = await search_spoonacular_recipes(
        query=dish_name,
        cuisine=cuisine,
        limit=limit
    )
    return results


async def search_recipes_by_ingredients(
    ingredients: list[str],
    allergies: list[str] = None,
    dietary_restrictions: list[str] = None,
    limit: int = MAX_CANDIDATES
) -> list[ScoredRecipe]:
    """
    Search for recipes that can be made with given ingredients
    """
    results = await search_spoonacular_recipes(
        query="",
        ingredients=ingredients,
        allergies=allergies,
        dietary_restrictions=dietary_restrictions,
        limit=limit
    )
    return results


def rank_candidates(
    recipes: list[Recipe],
    parsed_input: ParsedInput
) -> list[ScoredRecipe]:
    """
    Rank a list of recipes by relevance to user input
    
    Note: This is a synchronous wrapper that converts Recipe objects
    to ScoredRecipe objects. Used for backward compatibility.
    """
    synonyms = load_synonyms()
    
    scored = []
    for recipe in recipes:
        score = 50.0  # Base score
        
        # Calculate ingredient matches
        recipe_ingredient_names = [ing.name.lower() for ing in recipe.ingredients]
        matched = []
        missing = []
        
        if parsed_input.ingredients:
            for user_ing in parsed_input.ingredients:
                user_ing_lower = user_ing.lower()
                found = False
                for recipe_ing in recipe_ingredient_names:
                    if user_ing_lower in recipe_ing or recipe_ing in user_ing_lower:
                        matched.append(user_ing)
                        found = True
                        break
            
            if parsed_input.ingredients:
                coverage = len(matched) / len(parsed_input.ingredients)
                score += coverage * 30
        
        # Boost for cuisine match
        if parsed_input.cuisine and recipe.cuisine:
            if recipe.cuisine.lower() == parsed_input.cuisine.lower():
                score += 20
        
        # Boost for having instructions
        if recipe.instructions:
            score += 10
        
        # Get missing ingredients
        if parsed_input.ingredients:
            user_ingredients_lower = [i.lower() for i in parsed_input.ingredients]
            for recipe_ing in recipe_ingredient_names:
                has_match = False
                for user_ing in user_ingredients_lower:
                    if user_ing in recipe_ing or recipe_ing in user_ing:
                        has_match = True
                        break
                if not has_match:
                    missing.append(recipe_ing)
        
        scored.append(ScoredRecipe(
            recipe=recipe,
            score=score,
            ingredient_matches=matched,
            missing_ingredients=missing[:5]
        ))
    
    scored.sort(key=lambda x: x.score, reverse=True)
    return scored
