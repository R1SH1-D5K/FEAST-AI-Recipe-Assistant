"""
User Input Parser
Extracts ingredients, allergies, cuisine preferences, and dietary goals from natural language
"""

import re
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from config import SUPPORTED_CUISINES, COMMON_ALLERGENS, DATA_DIR


@dataclass
class ParsedInput:
    """Structured representation of parsed user input"""
    ingredients: list[str] = field(default_factory=list)
    allergies: list[str] = field(default_factory=list)
    cuisine: Optional[str] = None
    dietary_goals: list[str] = field(default_factory=list)
    free_text: str = ""
    
    def to_dict(self) -> dict:
        return {
            "ingredients": self.ingredients,
            "allergies": self.allergies,
            "cuisine": self.cuisine,
            "dietary_goals": self.dietary_goals,
            "free_text": self.free_text
        }


# Dietary goal patterns
DIETARY_PATTERNS = {
    "high protein": ["high protein", "protein rich", "lots of protein", "more protein"],
    "low carb": ["low carb", "low carbohydrate", "fewer carbs", "no carbs", "keto"],
    "low calorie": ["low calorie", "low cal", "light", "diet", "healthy", "fewer calories"],
    "low fat": ["low fat", "less fat", "fat free", "no fat"],
    "vegetarian": ["vegetarian", "veggie", "no meat"],
    "vegan": ["vegan", "plant based", "plant-based", "no animal"],
    "keto": ["keto", "ketogenic"],
    "gluten free": ["gluten free", "gluten-free", "no gluten", "celiac"],
    "dairy free": ["dairy free", "dairy-free", "no dairy", "lactose free"],
    "quick": ["quick", "fast", "easy", "simple", "15 minute", "30 minute"],
}

# Allergy detection patterns
ALLERGY_PATTERNS = [
    r"allergic to ([\w\s,]+)",
    r"([\w\s]+) allergy",
    r"([\w\s]+) allergies",
    r"no ([\w\s]+) please",
    r"can't eat ([\w\s]+)",
    r"cannot eat ([\w\s]+)",
    r"avoid ([\w\s]+)",
    r"without ([\w\s]+)",
    r"([\w\s]+)[- ]free",
]

# Cuisine detection patterns
CUISINE_PATTERNS = [
    r"([\w]+) food",
    r"([\w]+) cuisine",
    r"([\w]+) style",
    r"([\w]+) dish",
    r"([\w]+) recipe",
    r"something ([\w]+)",
]

# Words to exclude from ingredient extraction
STOP_WORDS = {
    "i", "have", "got", "want", "need", "make", "cook", "prepare", "using",
    "with", "and", "or", "the", "a", "an", "some", "any", "my", "me",
    "please", "can", "could", "would", "like", "love", "recipe", "dish",
    "meal", "food", "something", "anything", "stuff", "things", "ingredients",
    "looking", "for", "find", "suggest", "recommend", "give", "show",
    "today", "tonight", "dinner", "lunch", "breakfast", "snack",
    "really", "very", "quite", "just", "also", "too", "as", "well"
}


def load_synonyms() -> dict[str, list[str]]:
    """Load ingredient synonyms from JSON file"""
    synonyms_path = DATA_DIR / "synonyms.json"
    if synonyms_path.exists():
        with open(synonyms_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def normalize_ingredient(ingredient: str, synonyms: dict[str, list[str]]) -> str:
    """Normalize an ingredient name using synonyms"""
    ingredient = ingredient.lower().strip()
    
    if ingredient in synonyms:
        return synonyms[ingredient][0]
    
    return ingredient


def extract_allergies(text: str) -> list[str]:
    """Extract allergies from user text"""
    text_lower = text.lower()
    allergies = []
    
    for pattern in ALLERGY_PATTERNS:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            allergen = match.strip().rstrip('s')
            
            for known_allergen in COMMON_ALLERGENS:
                if allergen in known_allergen or known_allergen in allergen:
                    allergies.append(known_allergen)
                    break
            else:
                if allergen and len(allergen) > 2:
                    allergies.append(allergen)
    
    return list(set(allergies))


def extract_cuisine(text: str) -> Optional[str]:
    """Extract cuisine preference from user text"""
    text_lower = text.lower()
    
    for cuisine in SUPPORTED_CUISINES:
        if cuisine in text_lower:
            return cuisine
    
    for pattern in CUISINE_PATTERNS:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            match = match.strip().lower()
            if match in SUPPORTED_CUISINES:
                return match
    
    return None


def extract_dietary_goals(text: str) -> list[str]:
    """Extract dietary goals from user text"""
    text_lower = text.lower()
    goals = []
    
    for goal_name, patterns in DIETARY_PATTERNS.items():
        for pattern in patterns:
            if pattern in text_lower:
                goals.append(goal_name)
                break
    
    return list(set(goals))


def extract_ingredients(text: str, synonyms: dict[str, list[str]]) -> list[str]:
    """Extract ingredient names from user text"""
    text_lower = text.lower()
    
    # Remove allergy mentions
    for pattern in ALLERGY_PATTERNS:
        text_lower = re.sub(pattern, '', text_lower)
    
    # Remove cuisine mentions
    for cuisine in SUPPORTED_CUISINES:
        text_lower = text_lower.replace(cuisine, '')
    
    # Remove dietary goal mentions
    for patterns in DIETARY_PATTERNS.values():
        for pattern in patterns:
            text_lower = text_lower.replace(pattern, '')
    
    # Clean up text
    text_lower = re.sub(r'[^\w\s,]', ' ', text_lower)
    
    # Split by common delimiters
    parts = re.split(r'[,\n]|\band\b|\bor\b', text_lower)
    
    ingredients = []
    for part in parts:
        words = part.strip().split()
        filtered = [w for w in words if w not in STOP_WORDS and len(w) > 2]
        
        if filtered:
            ingredient = ' '.join(filtered)
            normalized = normalize_ingredient(ingredient, synonyms)
            
            if normalized and len(normalized) > 2:
                ingredients.append(normalized)
    
    # Extract single-word common ingredients
    all_words = text_lower.split()
    common_ingredients = {
        "chicken", "beef", "pork", "lamb", "fish", "salmon", "tuna", "shrimp",
        "rice", "pasta", "noodles", "bread", "potato", "potatoes",
        "tomato", "tomatoes", "onion", "onions", "garlic", "ginger",
        "carrot", "carrots", "broccoli", "spinach", "lettuce", "cabbage",
        "mushroom", "mushrooms", "pepper", "peppers", "corn", "peas",
        "beans", "lentils", "chickpeas", "tofu", "tempeh",
        "egg", "eggs", "cheese", "milk", "cream", "butter", "yogurt",
        "apple", "banana", "lemon", "lime", "orange", "mango",
        "flour", "sugar", "salt", "oil", "vinegar", "soy"
    }
    
    for word in all_words:
        word = word.strip()
        if word in common_ingredients and word not in ingredients:
            normalized = normalize_ingredient(word, synonyms)
            if normalized not in ingredients:
                ingredients.append(normalized)
    
    return list(set(ingredients))


def parse_user_input(text: str) -> ParsedInput:
    """Parse natural language user input into structured format"""
    synonyms = load_synonyms()
    
    return ParsedInput(
        ingredients=extract_ingredients(text, synonyms),
        allergies=extract_allergies(text),
        cuisine=extract_cuisine(text),
        dietary_goals=extract_dietary_goals(text),
        free_text=text
    )
