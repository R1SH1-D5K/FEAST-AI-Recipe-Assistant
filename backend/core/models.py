"""
Recipe Data Model
Defines the Recipe dataclass and related types
"""

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Ingredient:
    """Represents a single ingredient in a recipe"""
    name: str
    quantity: str = ""
    unit: str = ""
    original: str = ""
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "quantity": self.quantity,
            "unit": self.unit,
            "original": self.original
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Ingredient":
        return cls(
            name=data.get("name", ""),
            quantity=data.get("quantity", ""),
            unit=data.get("unit", ""),
            original=data.get("original", "")
        )

@dataclass
class Nutrition:
    """Nutritional information for a recipe"""
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            "calories": self.calories,
            "protein": self.protein,
            "carbs": self.carbs,
            "fat": self.fat,
            "fiber": self.fiber,
            "sugar": self.sugar,
            "sodium": self.sodium
        }
    
    @classmethod
    def from_dict(cls, data: Optional[dict]) -> Optional["Nutrition"]:
        if not data:
            return None
        return cls(
            calories=data.get("calories"),
            protein=data.get("protein"),
            carbs=data.get("carbs"),
            fat=data.get("fat"),
            fiber=data.get("fiber"),
            sugar=data.get("sugar"),
            sodium=data.get("sodium")
        )

@dataclass
class Recipe:
    """Represents a complete recipe"""
    id: str
    title: str
    ingredients: list[Ingredient]
    instructions: list[str]
    cuisine: str
    source: str
    source_id: str
    category: str = ""
    tags: list[str] = field(default_factory=list)
    image_url: str = ""
    source_url: str = ""
    youtube_url: str = ""
    nutrition: Optional[Nutrition] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "ingredients": [ing.to_dict() for ing in self.ingredients],
            "instructions": self.instructions,
            "cuisine": self.cuisine,
            "category": self.category,
            "tags": self.tags,
            "image_url": self.image_url,
            "source": self.source,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "youtube_url": self.youtube_url,
            "nutrition": self.nutrition.to_dict() if self.nutrition else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Recipe":
        ingredients = [
            Ingredient.from_dict(ing) if isinstance(ing, dict) else Ingredient(name=str(ing))
            for ing in data.get("ingredients", [])
        ]
        
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            ingredients=ingredients,
            instructions=data.get("instructions", []),
            cuisine=data.get("cuisine", "unknown"),
            category=data.get("category", ""),
            tags=data.get("tags", []),
            image_url=data.get("image_url", ""),
            source=data.get("source", ""),
            source_id=data.get("source_id", ""),
            source_url=data.get("source_url", ""),
            youtube_url=data.get("youtube_url", ""),
            nutrition=Nutrition.from_dict(data.get("nutrition"))
        )
    
    def get_ingredient_names(self) -> list[str]:
        """Get list of ingredient names (lowercase)"""
        return [ing.name.lower() for ing in self.ingredients if ing.name]
    
    def get_ingredients_text(self) -> str:
        """Get formatted ingredients list for display"""
        lines = []
        for ing in self.ingredients:
            if ing.original:
                lines.append(ing.original)
            elif ing.quantity or ing.unit:
                lines.append(f"{ing.quantity} {ing.unit} {ing.name}".strip())
            else:
                lines.append(ing.name)
        return "\n".join(lines)
    
    def get_instructions_text(self) -> str:
        """Get formatted instructions for display"""
        return "\n".join(
            f"{i+1}. {step}" 
            for i, step in enumerate(self.instructions)
        )
    
    def format_for_prompt(self) -> str:
        """Format recipe for LLM prompt"""
        ingredients_list = ", ".join(self.get_ingredient_names())
        
        instructions_preview = self.instructions[:3] if self.instructions else []
        instructions_text = " | ".join(instructions_preview)
        if len(self.instructions) > 3:
            instructions_text += f" ... ({len(self.instructions)} steps total)"
        
        nutrition_text = ""
        if self.nutrition and self.nutrition.calories:
            parts = []
            if self.nutrition.calories:
                parts.append(f"{self.nutrition.calories:.0f} cal")
            if self.nutrition.protein:
                parts.append(f"{self.nutrition.protein:.0f}g protein")
            if self.nutrition.carbs:
                parts.append(f"{self.nutrition.carbs:.0f}g carbs")
            if self.nutrition.fat:
                parts.append(f"{self.nutrition.fat:.0f}g fat")
            nutrition_text = f"\nNutrition: {', '.join(parts)}"
        
        return (
            f"Title: {self.title}\n"
            f"Cuisine: {self.cuisine}\n"
            f"Ingredients: {ingredients_list}\n"
            f"Instructions: {instructions_text}"
            f"{nutrition_text}\n"
            f"Source: {self.source} (ID: {self.source_id})"
        )
