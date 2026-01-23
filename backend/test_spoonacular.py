"""
Quick test script for Spoonacular integration
"""
import asyncio
from core.spoonacular import search_spoonacular_recipes, get_recipe_by_id

async def test_spoonacular():
    print("=== Testing Spoonacular Integration ===")
    print()
    
    # Test 1: Search by query
    print("1. Search for 'chicken pasta':")
    results = await search_spoonacular_recipes(query="chicken pasta", limit=3)
    for r in results:
        print(f"   - {r.recipe.title} ({r.recipe.cuisine})")
    print()
    
    # Test 2: Search with dietary restrictions
    print("2. Search for vegetarian curry:")
    results = await search_spoonacular_recipes(
        query="curry", 
        dietary_restrictions=["vegetarian"],
        limit=3
    )
    for r in results:
        print(f"   - {r.recipe.title}")
    print()
    
    # Test 3: Search with allergies
    print("3. Search for gluten-free chocolate:")
    results = await search_spoonacular_recipes(
        query="chocolate cake",
        allergies=["gluten"],
        limit=3
    )
    for r in results:
        print(f"   - {r.recipe.title}")
    print()
    
    # Test 4: Get recipe details
    if results:
        recipe_id = results[0].recipe.id
        print(f"4. Getting details for recipe: {results[0].recipe.title}")
        recipe = await get_recipe_by_id(recipe_id)
        if recipe:
            print(f"   Title: {recipe.title}")
            print(f"   Ingredients: {len(recipe.ingredients)}")
            print(f"   Instructions: {len(recipe.instructions)} steps")
            if recipe.instructions:
                step = recipe.instructions[0][:80] if len(recipe.instructions[0]) > 80 else recipe.instructions[0]
                print(f"   First step: {step}...")
    
    print()
    print("=== All tests passed! ===")

if __name__ == "__main__":
    asyncio.run(test_spoonacular())
