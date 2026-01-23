"""
Full integration test for FEAST with Spoonacular
Tests the complete chat flow
"""
import asyncio
from core.conversation import process_conversation, ConversationContext

async def test_full_chat():
    print("=" * 60)
    print("FEAST Full Integration Test with Spoonacular")
    print("=" * 60)
    print()
    
    context = ConversationContext()
    history = []
    
    # Test 1: Greeting
    print("Test 1: Greeting")
    print("-" * 40)
    response, recipes, context = await process_conversation(
        "Hello!",
        history,
        context
    )
    print(f"User: Hello!")
    print(f"FEAST: {response[:200]}...")
    print()
    
    # Test 2: Simple recipe request
    print("Test 2: Simple Recipe Request")
    print("-" * 40)
    response, recipes, context = await process_conversation(
        "I want to make spaghetti carbonara",
        history,
        context
    )
    print(f"User: I want to make spaghetti carbonara")
    print(f"FEAST: {response[:300]}...")
    if recipes:
        print(f"\nRecipes found: {len(recipes)}")
        for r in recipes[:3]:
            print(f"  - {r.recipe.title} ({r.recipe.cuisine})")
    print()
    
    # Test 3: Dietary restriction
    print("Test 3: Dietary Restriction")
    print("-" * 40)
    response, recipes, context = await process_conversation(
        "Show me a vegetarian curry recipe",
        [],
        ConversationContext()
    )
    print(f"User: Show me a vegetarian curry recipe")
    print(f"FEAST: {response[:300]}...")
    if recipes:
        print(f"\nRecipes found: {len(recipes)}")
        for r in recipes[:3]:
            print(f"  - {r.recipe.title}")
    print()
    
    # Test 4: Allergy consideration
    print("Test 4: Allergy Consideration")
    print("-" * 40)
    context = ConversationContext(allergies=["gluten"])
    response, recipes, context = await process_conversation(
        "I want a chocolate dessert, I'm allergic to gluten",
        [],
        context
    )
    print(f"User: I want a chocolate dessert, I'm allergic to gluten")
    print(f"FEAST: {response[:300]}...")
    if recipes:
        print(f"\nRecipes found: {len(recipes)}")
        for r in recipes[:3]:
            print(f"  - {r.recipe.title}")
    print()
    
    # Test 5: Ingredient-based search
    print("Test 5: Ingredient-based Search")
    print("-" * 40)
    context = ConversationContext(ingredients=["chicken", "lemon", "garlic"])
    response, recipes, context = await process_conversation(
        "What can I make with chicken, lemon and garlic?",
        [],
        context
    )
    print(f"User: What can I make with chicken, lemon and garlic?")
    print(f"FEAST: {response[:300]}...")
    if recipes:
        print(f"\nRecipes found: {len(recipes)}")
        for r in recipes[:3]:
            print(f"  - {r.recipe.title}")
    print()
    
    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_full_chat())
