"""Conversation Manager
Handles the LLM-first conversation flow where the AI drives the conversation
and decides when to search for recipes.
"""


import re
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from core.llm import call_llm_async, LLMError
from core.search import filter_recipes, ScoredRecipe, search_recipes_by_name, Recipe
from core.spoonacular import get_recipe_by_id as spoonacular_get_recipe
from core.parser import ParsedInput


class ConversationIntent(Enum):
    """What the user seems to want"""
    GREETING = "greeting"
    RECIPE_REQUEST = "recipe_request"
    QUESTION = "question"
    CLARIFICATION = "clarification"
    FOLLOW_UP = "follow_up"
    OTHER = "other"


class Strategy(Enum):
    """How we plan to fulfill the request"""
    EXACT_SEARCH = "exact_search"       # Named dish, try direct search
    LOOSE_SEARCH = "loose_search"       # Broader search with softer constraints
    INGREDIENT_REASONING = "ingredient_reasoning"  # Work from ingredients, may or may not call API
    NO_SEARCH = "no_search"             # Pure reasoning/teaching, no API needed


class ConversationPhase(str, Enum):
    DISCOVERY = "discovery"
    NARROWING = "narrowing"
    COMMITMENT = "commitment"
    EXECUTION = "execution"
    ADAPTATION = "adaptation"


class AssistantIntent(str, Enum):
    ASK_CLARIFYING_QUESTION = "ask_clarifying_question"
    SUGGEST_OPTIONS = "suggest_options"
    CONFIRM_CHOICE = "confirm_choice"
    PROVIDE_GUIDANCE = "provide_guidance"
    ADAPT_RECIPE = "adapt_recipe"
    TEACH_CONCEPT = "teach_concept"


@dataclass
class ActiveRecipe:
    recipe_id: str
    recipe_name: str
    source: str = "spoonacular"


@dataclass
class ConversationState:
    phase: ConversationPhase
    assistant_intent: AssistantIntent
    user_goal_summary: str

    active_recipe: Optional[ActiveRecipe] = None

    diet: Optional[str] = None
    allergies: list[str] = field(default_factory=list)
    cuisine: Optional[str] = None
    meal_type: Optional[str] = None
    time_constraint_minutes: Optional[int] = None

    recipes_shown: bool = False
    recipe_expanded: bool = False

    allow_recipe_identity_clarification: bool = True


@dataclass
class IntentAnalysis:
    intent: str
    required_ingredients: list[str]
    optional_ingredients: list[str]
    hard_constraints: list[str]
    soft_constraints: list[str]
    dish_name: Optional[str] = None


@dataclass
class ConversationContext:
    """Tracks conversation state and extracted preferences"""
    ingredients: list[str] = field(default_factory=list)
    allergies: list[str] = field(default_factory=list)
    cuisine_preference: str = ""
    dietary_restrictions: list[str] = field(default_factory=list)
    meal_type: str = ""  # breakfast, lunch, dinner, snack
    cooking_time: str = ""  # quick, moderate, long
    skill_level: str = ""  # easy, medium, advanced
    servings: int = 0
    flavor_preferences: list[str] = field(default_factory=list)
    dislikes: list[str] = field(default_factory=list)
    has_enough_context: bool = False
    last_recommended_recipes: list[str] = field(default_factory=list)
    
    def to_summary(self) -> str:
        """Generate a summary of known preferences"""
        parts = []
        if self.ingredients:
            parts.append(f"Ingredients: {', '.join(self.ingredients)}")
        if self.allergies:
            parts.append(f"Allergies/Avoid: {', '.join(self.allergies)}")
        if self.cuisine_preference:
            parts.append(f"Cuisine: {self.cuisine_preference}")
        if self.dietary_restrictions:
            parts.append(f"Diet: {', '.join(self.dietary_restrictions)}")
        if self.meal_type:
            parts.append(f"Meal type: {self.meal_type}")
        if self.cooking_time:
            parts.append(f"Time: {self.cooking_time}")
        if self.dislikes:
            parts.append(f"Dislikes: {', '.join(self.dislikes)}")
        return "\n".join(parts) if parts else "No preferences specified yet"


# =============================================================================
# CORE SYSTEM PROMPT - THE AI'S BRAIN
# =============================================================================

SYSTEM_PROMPT = """You are FEAST, a thoughtful and friendly cooking companion. You genuinely enjoy helping people discover what to cook.

## 🧠 YOUR CORE IDENTITY: REASONING ASSISTANT, NOT KEYWORD SEARCH

You are NOT a keyword-based recipe search assistant.
You are a REASONING assistant who thinks through cooking problems like a helpful friend would.

### Before ANY response, you MUST internally analyze:

1. **INTENT ANALYSIS** - What kind of cooking problem is this?
   - Browsing/exploring: "what should I make for dinner?"
   - Specific dish: "how do I make pad thai?"
   - Ingredient-based: "I have chicken and broccoli"
   - Constraint-based: "something quick and healthy"
   - Learning: "what's the difference between sautéing and stir-frying?"
   - Inspiration: "I'm bored with my usual meals"

2. **CONSTRAINT EXTRACTION** - Separate hard vs soft requirements:
   - HARD constraints: allergies, dietary restrictions (must respect)
   - SOFT constraints: time preferences, cuisine wishes (can flex)
   - Available ingredients vs nice-to-have ingredients

3. **RESPONSE STRATEGY** - Choose the right approach:
   - Direct match: User asked for a specific dish → search for it
   - Partial match: Close options exist → suggest with adaptations
   - Ingredient-driven: User has X ingredients → find recipes using them
   - Guided clarification: Need just a bit more info → ask ONE helpful question
   - Creative suggestion: Nothing exact → suggest related dishes or techniques

## 🚫 HARD FAILURES ARE FORBIDDEN

This rule overrides EVERYTHING else:

**You must NEVER say "I couldn't find anything" without offering solutions.**

If no exact database match exists, you MUST still:
- Suggest similar dishes that ARE available
- Propose ingredient substitutions that would unlock more options
- Recommend relaxing a constraint ("If you're flexible on the Italian requirement, I've got some amazing Mediterranean options...")
- Explain what's limiting results and how to work around it
- Offer to search for something related

**Examples of FORBIDDEN responses:**
❌ "I couldn't find recipes matching those criteria."
❌ "No results found for your search."
❌ "Sorry, I don't have anything for that."

**Examples of REQUIRED behavior:**
✅ "Hmm, I don't have an exact match for vegan keto tiramisu, but I've got a couple directions we could go - there's a beautiful coconut cream-based dessert that hits similar notes, or I could show you a lighter cheesecake that's easier to adapt. What sounds more appealing?"
✅ "That's a pretty specific combo! I'm not finding an exact match, but if you're open to it, [dish X] is really close and just needs [small tweak]. Want to see it?"
✅ "I don't have that exact recipe, but this is actually a great opportunity - [related dish] uses the same technique and you probably have the ingredients. Let me show you."

## 💬 CONVERSATIONAL STYLE

You are a friendly, warm cooking companion - not a search engine.

### Your responses should:
- Feel like talking to a knowledgeable friend who loves food
- Include brief insights about WHY something works (flavor, technique, culture)
- Guide the conversation forward naturally
- Show genuine enthusiasm without being over-the-top

### Response structure (loosely):
1. **Context-aware opener** - Acknowledge what they asked, show you understood
2. **Insight or reasoning** - Brief explanation of your thinking or a food tip
3. **Action** - Recipes, suggestions, or a gentle follow-up question

### Tone guidelines:
- Warm and encouraging, especially for beginners
- Casually knowledgeable - share food wisdom naturally
- Keep it conversational - vary your phrasing
- 1 emoji max per response (or none) - no spam

### Avoid:
- Generic filler: "Enjoy cooking!", "Happy cooking!", "Awesome!"
- One-line responses without substance
- Search-engine tone: "Here are your results"
- Repeating yourself or using the same phrases
- Over-explaining or being preachy

### Good examples:
- "Pad thai is one of those dishes that looks fancy but comes together really fast once you have the sauce figured out. Here are a few versions..."
- "Ooh, chicken and broccoli is a great starting point. Are you thinking Asian-style, or more of a creamy pasta situation?"
- "I love that you're exploring Indian food! Biryani is definitely a project, but so worth it. Let me show you a couple approaches..."

## 📋 TECHNICAL RULES

### When to search (include [SEARCH_RECIPES] in your response):
- User asks for a specific dish by name
- User describes what they want to cook
- User provides ingredients and asks what to make
- You've determined a search would help (after reasoning)

### Recipe data rules (NON-NEGOTIABLE):
- Use ONLY recipe data provided from the database
- NEVER invent ingredients, measurements, or instructions
- Copy recipe details EXACTLY as provided
- You MAY add conversational framing around real data
- Include recipe images when presenting full recipes

### When presenting recipes:
- Your message should be brief and friendly
- Recipe cards are shown automatically by the system
- Do NOT manually list recipe titles or say "Click to see more"
- Focus your message on WHY these recipes fit their request

## 🎯 REMEMBER

You are allowed to:
- Suggest dishes even if no exact database match exists
- Combine cooking knowledge with available options
- Explain your reasoning in a friendly way
- Ask clarifying questions when genuinely helpful
- Be creative in finding solutions

You exist to make cooking feel accessible, fun, and personal.
Every interaction should feel like chatting with a friend who happens to know a lot about food.
## 🔀 CONVERSATION PHASES (derive before each response)
- DISCOVERY: intent/constraints unclear
- NARROWING: options presented, no choice yet
- COMMITMENT: user picked a recipe or approach
- EXECUTION: step-by-step cooking guidance
- ADAPTATION: substitutions, mistakes, or new constraints

## 🎯 ASSISTANT INTENT (choose exactly ONE each turn)
- ask_clarifying_question
- suggest_options
- confirm_choice
- provide_guidance
- adapt_recipe
- teach_concept

Rules:
- Ask at most one clarifying question, and only if the answer would materially change results. If optional, proceed without asking.
- Every response must move the user toward the next phase and end with one concrete forward action (question, confirmation, or offer). No open-ended endings.
- If the user has already selected or expanded a recipe, do NOT ask which recipe they mean. Assume the active recipe unless they explicitly switch.

Allowed assistant intents by phase:
- discovery: ask_clarifying_question, suggest_options
- narrowing: suggest_options, confirm_choice
- commitment: confirm_choice
- execution: provide_guidance, teach_concept
- adaptation: adapt_recipe, provide_guidance

## 🧾 RESPONSE FORMAT (must use, tags removed before user sees)
[ASSISTANT_INTENT]: <enum from above>
[USER_GOAL_SUMMARY]: <1 sentence>
[RESPONSE]:
<user-facing message only>
"""


def build_conversation_prompt(
    user_message: str,
    conversation_history: list[dict],
    context: ConversationContext,
    reasoning_note: str = ""
) -> list[dict]:
    """Build the prompt for the conversation LLM"""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if reasoning_note:
        # Give the model a compact, structured snapshot of our analysis/strategy.
        messages.append({"role": "system", "content": reasoning_note})
    
    # Add context summary if we have preferences
    if context.ingredients or context.allergies or context.cuisine_preference:
        context_msg = f"\n\n[CONVERSATION CONTEXT]\n{context.to_summary()}"
        messages[0]["content"] += context_msg
    
    # Add conversation history (last 10 messages)
    for msg in conversation_history[-10:]:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    
    # Add current user message
    messages.append({"role": "user", "content": user_message})
    
    return messages


def extract_context_from_response(
    llm_response: str,
    user_message: str,
    existing_context: ConversationContext
) -> ConversationContext:
    """Update context based on conversation"""
    context = existing_context
    combined_text = (user_message + " " + llm_response).lower()
    
    # Extract ingredients mentioned
    common_ingredients = [
        'chicken', 'beef', 'pork', 'fish', 'salmon', 'shrimp', 'tofu', 'eggs',
        'rice', 'pasta', 'noodles', 'bread', 'potato', 'potatoes',
        'tomato', 'tomatoes', 'onion', 'garlic', 'carrot', 'broccoli', 'spinach',
        'cheese', 'milk', 'cream', 'butter', 'yogurt',
        'beans', 'lentils', 'chickpeas'
    ]
    for ing in common_ingredients:
        if ing in user_message.lower() and ing not in context.ingredients:
            context.ingredients.append(ing)
    
    # Extract allergies/restrictions
    allergy_keywords = {
        'allergic to': True, 'allergy': True, 'intolerant': True,
        "can't eat": True, "don't eat": True, 'avoid': True,
        'no ': True, 'without': True
    }
    allergens = ['nuts', 'peanuts', 'dairy', 'gluten', 'shellfish', 'eggs', 'soy', 'wheat', 'fish']
    for allergen in allergens:
        if allergen in user_message.lower():
            for keyword in allergy_keywords:
                if keyword in user_message.lower():
                    if allergen not in context.allergies:
                        context.allergies.append(allergen)
                    break
    
    # Extract cuisine preference
    cuisines = ['italian', 'mexican', 'chinese', 'japanese', 'indian', 'thai', 
                'french', 'greek', 'korean', 'vietnamese', 'american', 'mediterranean']
    for cuisine in cuisines:
        if cuisine in user_message.lower():
            context.cuisine_preference = cuisine
            break
    
    # Extract meal type
    meal_types = {'breakfast': 'breakfast', 'lunch': 'lunch', 'dinner': 'dinner', 
                  'snack': 'snack', 'dessert': 'dessert', 'brunch': 'breakfast'}
    for keyword, meal in meal_types.items():
        if keyword in user_message.lower():
            context.meal_type = meal
            break
    
    # Extract time constraints
    if any(word in user_message.lower() for word in ['quick', 'fast', '15 min', '20 min', '30 min', 'hurry']):
        context.cooking_time = 'quick'
    elif any(word in user_message.lower() for word in ['slow', 'hour', 'hours', 'time']):
        context.cooking_time = 'long'
    
    # Extract dietary preferences
    diets = ['vegetarian', 'vegan', 'keto', 'low-carb', 'gluten-free', 'dairy-free', 'healthy', 'low-fat']
    for diet in diets:
        if diet in user_message.lower() and diet not in context.dietary_restrictions:
            context.dietary_restrictions.append(diet)
    
    return context


def should_search_recipes(llm_response: str) -> bool:
    """Check if the LLM wants to search for recipes"""
    return "[SEARCH_RECIPES]" in llm_response


def analyze_intent_and_constraints(user_message: str, context: ConversationContext) -> IntentAnalysis:
    """Lightweight intent/constraint analysis for strategy selection."""
    text = user_message.lower()
    required_ingredients: list[str] = []
    optional_ingredients: list[str] = []
    hard_constraints: list[str] = []
    soft_constraints: list[str] = []
    dish_name = None

    # Dish name detection (kept simple, used for exact search)
    direct = re.search(r"(?:recipe for|how to make|make|cook|prepare)\s+([\w\s'-]{3,})", text)
    if direct:
        dish_name = direct.group(1).strip()

    # Ingredient cues (comma or 'with' lists)
    if "," in text or " with " in text or " using " in text:
        # Very simple extraction: split on common separators
        tokens = re.split(r"[,/]| with | using | and ", text)
        for tok in tokens:
            tok = tok.strip()
            if tok and len(tok.split()) <= 3 and not tok.isdigit():
                optional_ingredients.append(tok)

    # Constraints
    diet_flags = ["vegan", "vegetarian", "keto", "paleo", "gluten-free", "dairy-free", "low carb", "low-carb", "healthy"]
    time_flags = ["15 min", "20 min", "30 min", "quick", "fast", "under 20", "under 30"]
    allergy_flags = ["allergic", "avoid", "can't eat", "no ", "without"]
    if any(flag in text for flag in diet_flags):
        soft_constraints.append("dietary preference")
    if any(flag in text for flag in time_flags):
        soft_constraints.append("time: quick")
    if any(flag in text for flag in allergy_flags):
        hard_constraints.append("allergy/avoid")
    if context.allergies:
        hard_constraints.extend([f"avoid: {a}" for a in context.allergies])
    if context.dietary_restrictions:
        soft_constraints.extend([f"diet: {d}" for d in context.dietary_restrictions])

    # Intent classification
    if any(word in text for word in ["how to", "difference between", "what is", "technique", "why"]):
        intent = "learning"
    elif dish_name:
        intent = "specific_dish"
    elif optional_ingredients:
        intent = "ingredient_based"
    elif soft_constraints or hard_constraints:
        intent = "constraint_based"
    elif any(word in text for word in ["anything", "ideas", "bored", "inspire", "inspiration", "suggest"]):
        intent = "browsing"
    else:
        intent = "browsing"

    return IntentAnalysis(
        intent=intent,
        required_ingredients=required_ingredients,
        optional_ingredients=optional_ingredients,
        hard_constraints=hard_constraints,
        soft_constraints=soft_constraints,
        dish_name=dish_name,
    )


def determine_conversation_phase(
    user_message: str,
    conversation_history: list[dict],
    context: ConversationContext,
    analysis: IntentAnalysis,
    recipe_detail_requested: bool = False
) -> ConversationPhase:
    """Infer conversation phase from user input, history, and known context."""
    text = user_message.lower()

    # Direct signals for adaptation
    if any(keyword in text for keyword in ["swap", "substitute", "instead", "without", "ran out", "out of", "can't have", "allergic", "replace"]):
        return ConversationPhase.ADAPTATION

    # Execution cues
    if any(keyword in text for keyword in ["next step", "what's next", "temperature", "preheat", "bake", "simmer", "timer", "cook it", "how long", "step"]):
        return ConversationPhase.EXECUTION

    # If user asked for a specific recipe detail, they are committing
    if recipe_detail_requested or analysis.dish_name:
        return ConversationPhase.COMMITMENT

    # Signals of choosing from options
    if any(keyword in text for keyword in ["i'll take", "i'll go with", "let's make", "let's do", "choose", "pick", "the first one", "the second one", "go with"]):
        return ConversationPhase.COMMITMENT

    # If we have already shown options, assume narrowing until a choice is made
    if context.last_recommended_recipes:
        return ConversationPhase.NARROWING

    # Learning or browsing starts in discovery
    if analysis.intent in ["learning", "browsing"]:
        return ConversationPhase.DISCOVERY

    # Ingredient or constraint-driven without a chosen dish → narrowing
    if analysis.intent in ["ingredient_based", "constraint_based"]:
        return ConversationPhase.NARROWING if context.ingredients or context.dietary_restrictions else ConversationPhase.DISCOVERY

    return ConversationPhase.DISCOVERY


def should_ask_clarifying_question(analysis: IntentAnalysis, context: ConversationContext) -> bool:
    """Decide if a clarifying question is materially useful."""
    if analysis.intent == "learning":
        return False
    if analysis.dish_name:
        return False
    if analysis.optional_ingredients or context.ingredients:
        return False
    # If we have almost no signal, one clarifying question can help
    return True


def choose_assistant_intent(
    phase: ConversationPhase,
    analysis: IntentAnalysis,
    needs_clarification: bool
) -> AssistantIntent:
    """Map phase + analysis to a single assistant intent."""
    if phase == ConversationPhase.ADAPTATION:
        return AssistantIntent.ADAPT_RECIPE
    if phase == ConversationPhase.EXECUTION:
        return AssistantIntent.PROVIDE_GUIDANCE if analysis.intent != "learning" else AssistantIntent.TEACH_CONCEPT
    if phase == ConversationPhase.COMMITMENT:
        return AssistantIntent.CONFIRM_CHOICE
    if phase == ConversationPhase.NARROWING:
        return AssistantIntent.SUGGEST_OPTIONS if not needs_clarification else AssistantIntent.SUGGEST_OPTIONS
    if phase == ConversationPhase.DISCOVERY:
        if analysis.intent == "learning":
            return AssistantIntent.TEACH_CONCEPT
        return AssistantIntent.ASK_CLARIFYING_QUESTION if needs_clarification else AssistantIntent.SUGGEST_OPTIONS
    return AssistantIntent.SUGGEST_OPTIONS


def summarize_user_goal(user_message: str, analysis: IntentAnalysis, context: ConversationContext) -> str:
    """Create a compact, one-sentence goal summary for the LLM."""
    parts = []
    if analysis.dish_name:
        parts.append(f"Cook {analysis.dish_name}")
    elif analysis.intent == "ingredient_based" and (analysis.optional_ingredients or context.ingredients):
        parts.append(f"Find recipes using {', '.join(analysis.optional_ingredients or context.ingredients)}")
    elif analysis.intent == "constraint_based":
        parts.append("Find recipes matching their constraints")
    elif analysis.intent == "learning":
        parts.append("Teach a cooking concept or technique")
    else:
        parts.append("Suggest good meal ideas")

    if context.allergies:
        parts.append(f"avoid {', '.join(context.allergies)}")
    if context.dietary_restrictions:
        parts.append(f"dietary prefs: {', '.join(context.dietary_restrictions)}")
    if context.cuisine_preference:
        parts.append(f"cuisine: {context.cuisine_preference}")
    return "; ".join(parts)[:240]


def decide_strategy(analysis: IntentAnalysis) -> Strategy:
    """Explicit strategy selection before any retrieval."""
    if analysis.intent == "specific_dish":
        return Strategy.EXACT_SEARCH
    if analysis.intent == "ingredient_based":
        return Strategy.INGREDIENT_REASONING
    if analysis.intent == "constraint_based":
        return Strategy.LOOSE_SEARCH
    if analysis.intent == "learning":
        return Strategy.NO_SEARCH
    # browsing / inspiration default
    return Strategy.LOOSE_SEARCH


def summarize_analysis_for_prompt(
    analysis: IntentAnalysis,
    strategy: Strategy,
    phase: ConversationPhase,
    assistant_intent: AssistantIntent,
    user_goal_summary: str
) -> str:
    """Compact, structured snapshot to steer the LLM and enforce the response contract."""
    return (
        "[REASONING SNAPSHOT]\n"
        f"Intent: {analysis.intent}\n"
        f"Strategy: {strategy.value}\n"
        f"Phase: {phase.value}\n"
        f"AssistantIntent: {assistant_intent.value}\n"
        f"UserGoal: {user_goal_summary or 'n/a'}\n"
        f"Dish: {analysis.dish_name or 'n/a'}\n"
        f"Required ingredients: {', '.join(analysis.required_ingredients) or 'n/a'}\n"
        f"Optional ingredients: {', '.join(analysis.optional_ingredients) or 'n/a'}\n"
        f"Hard constraints: {', '.join(analysis.hard_constraints) or 'n/a'}\n"
        f"Soft constraints: {', '.join(analysis.soft_constraints) or 'n/a'}\n"
        "ActiveRecipe: tracked internally; assume active recipe for follow-ups after expansion.\n"
        f"AllowRecipeIdentityClarification: {'true' if phase in [ConversationPhase.DISCOVERY, ConversationPhase.NARROWING] else 'false'}\n"
        "Active recipe is locked when present; assume active recipe for follow-ups after expansion.\n"
        "Clarification rule: Ask at most one clarifying question only if it materially changes results. If optional, proceed without asking.\n"
        "Forward progress: Move toward the next phase and end with one concrete forward action (question, confirmation, or offer).\n"
        "Response format (must follow):\n[ASSISTANT_INTENT]: <enum>\n[USER_GOAL_SUMMARY]: <1 sentence>\n[RESPONSE]:\n<user-facing message only>"
    )


def clean_response_for_display(response: str) -> str:
    """Remove internal tags from response before showing to user, but preserve markdown formatting."""
    # Remove only internal tags, not markdown
    response = re.sub(r'\[SEARCH_RECIPES\]', '', response)
    # Remove the "Looking for:" line that follows
    response = re.sub(r'Looking for:.*?(?=\n|$)', '', response)
    # Do NOT strip markdown (e.g., **, *, _, etc.)
    return response.strip()


def strip_structured_tags(response: str) -> str:
    """Allow-list only the [RESPONSE] block; everything else is discarded. Preserve markdown formatting."""
    # Find the [RESPONSE] marker (case-insensitive), accept optional colon
    pattern = re.compile(r"\[RESPONSE\]\s*:?", flags=re.IGNORECASE)
    match = pattern.search(response)
    if not match:
        # If the model skipped the marker, try to use the whole reply after cleaning tags
        cleaned_all = clean_response_for_display(response)
        # Drop any leaked reasoning/debug blocks to avoid exposing system prompts
        cleaned_all = re.sub(r"\[REASONING SNAPSHOT\][\s\S]*", "", cleaned_all).strip()
        # Collapse excessive blank lines after removal
        cleaned_all = re.sub(r"\n{3,}", "\n\n", cleaned_all)
        return cleaned_all or "I'm here and ready to help—what would you like to cook or clarify?"

    # Take everything after the marker
    start = match.end()
    response_only = response[start:]

    # Trim leading newlines/spaces
    response_only = response_only.lstrip()

    # If empty after trimming, fallback
    if not response_only.strip():
        return "I'm here and ready to help—what would you like to cook or clarify?"

    # Only strip internal tags, not markdown
    return clean_response_for_display(response_only)


def format_full_recipe_for_llm(recipe: Recipe) -> str:
    """Format complete recipe data for LLM to present (with exact data preservation)"""
    # Format ingredients exactly as they are in the database
    ingredients_list = []
    for ing in recipe.ingredients:
        # Use the 'original' field which has the exact text with quantities
        if hasattr(ing, 'original') and ing.original:
            ingredients_list.append(ing.original)
        elif hasattr(ing, 'name') and ing.name:
            ingredients_list.append(ing.name)
        else:
            # Fallback to constructing from parts if needed
            parts = []
            if hasattr(ing, 'quantity') and ing.quantity:
                parts.append(str(ing.quantity))
            if hasattr(ing, 'unit') and ing.unit:
                parts.append(ing.unit)
            if hasattr(ing, 'name') and ing.name:
                parts.append(ing.name)
            ingredients_list.append(' '.join(parts) if parts else 'Unknown ingredient')
    
    # Format instructions exactly as they are
    instructions_list = recipe.instructions if recipe.instructions else []
    
    formatted = f"""[RECIPE DATA FROM DATABASE - USE EXACTLY AS PROVIDED]

⚠️ CRITICAL: You MUST use this data EXACTLY as written below. Do NOT change measurements, do NOT rephrase ingredients, do NOT modify instructions. This is REAL recipe data from Spoonacular that the user needs to cook safely.

Title: {recipe.title}
Cuisine: {recipe.cuisine}
Source: {recipe.source}
Image URL: {recipe.image_url}

INGREDIENTS (copy each line EXACTLY - do NOT change "1½ tsp" to "1.5 tsp" or any other modifications):
"""
    for i, ing in enumerate(ingredients_list, 1):
        formatted += f"{i}. {ing}\n"
    
    formatted += f"\nINSTRUCTIONS (copy each step EXACTLY - do NOT rephrase or combine steps):\n"
    for i, step in enumerate(instructions_list, 1):
        formatted += f"{i}. {step}\n"
    
    formatted += f"""
⚠️ REMINDER: Present this recipe data EXACTLY as provided above. Your job is to:
1. Add the image at the top using markdown: ![{recipe.title}]({recipe.image_url})
2. Add friendly conversational framing ("Here's how to make it!", "Let's get cooking!", etc.)
3. Format the ingredients and instructions nicely with bullets or numbers
4. Do NOT change any measurements, ingredient names, or instruction wording
5. Do NOT add steps or tips that aren't in the data above
"""
    
    return formatted


async def process_conversation(
    user_message: str,
    conversation_history: list[dict],
    context: ConversationContext
) -> tuple[str, Optional[list[ScoredRecipe]], ConversationContext]:
    """
    Process a conversation turn.
    Returns: (response_text, recipes_if_any, updated_context)
    """
    recipe_detail_requested = False
    # Check if user is requesting details about a specific recipe
    recipe_detail_match = re.search(
        r"(?:i'?d like to make|tell me (?:more )?about|how (?:do i make|to make)|show me|details? (?:for|about)|make) ['\"]([^'\"]+)['\"]",
        user_message,
        re.IGNORECASE
    )
    if recipe_detail_match:
        recipe_detail_requested = True
    
    if recipe_detail_match:
        recipe_title = recipe_detail_match.group(1).strip()
        # Search for this recipe via Spoonacular
        candidates = await search_recipes_by_name(recipe_title, limit=5)
        
        # Find best match by title similarity
        best_match = None
        best_score = 0
        for candidate in candidates:
            from rapidfuzz import fuzz
            score = fuzz.ratio(recipe_title.lower(), candidate.recipe.title.lower())
            if score > best_score:
                best_score = score
                best_match = candidate
        
        if best_match and best_score > 60:
            # User is asking for details about a specific recipe
            # FIRST: Fetch the full recipe details from Spoonacular API
            from core.spoonacular import get_full_recipe
            full_recipe_result = await get_full_recipe(best_match.recipe.source_id)
            
            if not full_recipe_result or not full_recipe_result.recipe.ingredients:
                # Fallback if we can't get full details
                return "I'm having trouble getting the full recipe details right now. Please try again!", None, context
            
            # Send the full recipe data to the LLM with strict instructions
            recipe_data = format_full_recipe_for_llm(full_recipe_result.recipe)

            # Lock active recipe and phase for execution
            state.active_recipe = ActiveRecipe(
                recipe_id=str(full_recipe_result.recipe.source_id),
                recipe_name=full_recipe_result.recipe.title,
                source="spoonacular",
            )
            state.phase = ConversationPhase.EXECUTION
            state.assistant_intent = AssistantIntent.PROVIDE_GUIDANCE
            state.recipe_expanded = True
            state.allow_recipe_identity_clarification = False
            
            # Create a special prompt for recipe presentation with STRONG anti-hallucination measures
            special_messages = [
                {"role": "system", "content": SYSTEM_PROMPT + """

🚨 EXTRA WARNING FOR THIS REQUEST 🚨
The user has selected a specific recipe and needs the EXACT details from Spoonacular.
You are receiving real recipe data below. You MUST copy it word-for-word.
DO NOT use your training data to generate recipe ingredients or instructions.
DO NOT create a recipe from memory.
USE ONLY THE DATA PROVIDED BELOW.
Use the response format:
[ASSISTANT_INTENT]: provide_guidance
[USER_GOAL_SUMMARY]: <1 sentence>
[RESPONSE]:
<user-facing message only>"""},
                {"role": "user", "content": f"""{user_message}

{recipe_data}

⚠️ CRITICAL INSTRUCTION:
Present the recipe above EXACTLY as provided. Do NOT change any words, measurements, or steps.
Add the recipe image at the top, add friendly framing text, but keep all recipe data identical to what's above.
Use the structured response format shown above."""}
            ]
            
            llm_response = await call_llm_async(special_messages)
            cleaned = strip_structured_tags(llm_response)
            
            # Return with no recipe cards (details already shown)
            return cleaned, None, context
    
    # Intent/constraint analysis and strategy selection happen before any search
    analysis = analyze_intent_and_constraints(user_message, context)
    strategy = decide_strategy(analysis)
    needs_clarification = should_ask_clarifying_question(analysis, context)
    phase = determine_conversation_phase(user_message, conversation_history, context, analysis, recipe_detail_requested)
    assistant_intent = choose_assistant_intent(phase, analysis, needs_clarification)
    user_goal_summary = summarize_user_goal(user_message, analysis, context)

    # Initialize conversation state
    state = ConversationState(
        phase=phase,
        assistant_intent=assistant_intent,
        user_goal_summary=user_goal_summary,
        allergies=context.allergies.copy(),
        cuisine=context.cuisine_preference or None,
        meal_type=context.meal_type or None,
        diet=context.dietary_restrictions[0] if context.dietary_restrictions else None,
        recipes_shown=bool(context.last_recommended_recipes),
        recipe_expanded=False,
        allow_recipe_identity_clarification=True,
    )

    # Recover active recipe if we are past commitment and missing it
    phase_order = [ConversationPhase.DISCOVERY, ConversationPhase.NARROWING, ConversationPhase.COMMITMENT, ConversationPhase.EXECUTION, ConversationPhase.ADAPTATION]
    if state.phase in phase_order[2:] and not state.active_recipe and context.last_recommended_recipes:
        last_id = str(context.last_recommended_recipes[-1])
        state.active_recipe = ActiveRecipe(recipe_id=last_id, recipe_name="selected recipe")
        state.allow_recipe_identity_clarification = False

    # Enforce clarification lock when committed/executing/adapting
    if state.phase in (ConversationPhase.COMMITMENT, ConversationPhase.EXECUTION, ConversationPhase.ADAPTATION):
        state.allow_recipe_identity_clarification = False

    # If clarification is disallowed, correct intent to a valid non-clarifying option
    if not state.allow_recipe_identity_clarification and state.assistant_intent == AssistantIntent.ASK_CLARIFYING_QUESTION:
        if state.phase == ConversationPhase.NARROWING:
            state.assistant_intent = AssistantIntent.SUGGEST_OPTIONS
        elif state.phase == ConversationPhase.COMMITMENT:
            state.assistant_intent = AssistantIntent.CONFIRM_CHOICE
        elif state.phase == ConversationPhase.EXECUTION:
            state.assistant_intent = AssistantIntent.PROVIDE_GUIDANCE
        elif state.phase == ConversationPhase.ADAPTATION:
            state.assistant_intent = AssistantIntent.ADAPT_RECIPE
        else:
            state.assistant_intent = AssistantIntent.SUGGEST_OPTIONS

    reasoning_note = summarize_analysis_for_prompt(
        analysis=analysis,
        strategy=strategy,
        phase=state.phase,
        assistant_intent=state.assistant_intent,
        user_goal_summary=state.user_goal_summary,
    )

    # Normal conversation flow
    messages = build_conversation_prompt(user_message, conversation_history, context, reasoning_note)
    llm_response_raw = await call_llm_async(messages)
    llm_response_clean = strip_structured_tags(llm_response_raw)
    
    # Update context based on conversation
    context = extract_context_from_response(llm_response_clean, user_message, context)
    context.has_enough_context = bool(
        context.ingredients or context.allergies or context.cuisine_preference or context.dietary_restrictions
    )
    
    # Decide if we should search (explicit strategy-driven, still honoring explicit tags)
    recipes = None
    
    # --- Detect direct dish requests ---
    # Try multiple patterns to catch different phrasings
    dish_name = None
    
    # Pattern 1: "how to make X" or "recipe for X"
    direct_dish_match = re.search(
        r"(?:how (?:to|do i|can i) (?:make|cook|prepare)|recipe for|show me (?:a|an|the)?|make me|cook|i want|give me|i'd like to make|i would like to make) (?:some |a |an |the )?([\w\s'-]+)",
        user_message, 
        re.IGNORECASE
    )
    
    if direct_dish_match:
        dish_name = direct_dish_match.group(1).strip()
        # Clean up common trailing words and punctuation
        dish_name = re.sub(r'\s+(recipe|recipes|please|thanks|how do i make them)[\?,!]*$', '', dish_name, flags=re.IGNORECASE)
        dish_name = re.sub(r'[,\?!]+$', '', dish_name).strip()
    
    # Pattern 2: Just the dish name with contextual words (e.g., "Strawberry pancakes")
    if not dish_name and len(user_message.split()) <= 5:
        # Short message might be just a dish name
        potential_dish = re.sub(r'^(make|cook|recipe for|show me|i want|give me|how to make)\s+', '', user_message, flags=re.IGNORECASE)
        potential_dish = re.sub(r'\s+(recipe|recipes|please|thanks)[\?,!]*$', '', potential_dish, flags=re.IGNORECASE)
        potential_dish = potential_dish.strip()
        if len(potential_dish) > 2:
            dish_name = potential_dish
    
    should_search = strategy in (Strategy.EXACT_SEARCH, Strategy.LOOSE_SEARCH) or should_search_recipes(llm_response_raw)
    if should_search or dish_name:
        parsed = ParsedInput(
            ingredients=context.ingredients,
            allergies=context.allergies,
            cuisine=context.cuisine_preference if context.cuisine_preference else None,
            dietary_goals=context.dietary_restrictions,
            free_text=dish_name if dish_name else user_message
        )
        
        if strategy in (Strategy.EXACT_SEARCH, Strategy.LOOSE_SEARCH):
            # Retrieval is optional; we only call the API when strategy says so.
            if dish_name:
                recipes = await search_recipes_by_name(
                    dish_name=dish_name,
                    cuisine=context.cuisine_preference,
                    limit=5
                )
            else:
                recipes = await filter_recipes(parsed, limit=5)
        
        # If no recipes found, trigger adaptive response (NO HARD FAILURES)
        if not recipes:
            recovery_messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"""The user asked: "{user_message}"

We attempted a search but found no exact matches.

You must NOT say "I couldn't find anything" or give up.

Do ONE or MORE of these:
1) Suggest similar dishes (name 2-3) that are close
2) Offer to relax a constraint (time, cuisine, diet) with a concrete suggestion
3) Propose ingredient substitutions that would unlock options
4) Recommend a related dish that uses similar techniques or flavors
5) Briefly explain what's limiting results and offer a workaround

Keep it warm and concise. End with a clear next step or question.
Use the structured response format:
[ASSISTANT_INTENT]: <enum>
[USER_GOAL_SUMMARY]: <1 sentence>
[RESPONSE]:
<user-facing message only>

User context:
{context.to_summary()}"""}
            ]
            recovery_raw = await call_llm_async(recovery_messages)
            llm_response_clean = strip_structured_tags(recovery_raw)
    
    # Ingredient reasoning or no-search paths already cleaned
    display_response = llm_response_clean

    # Track when options were shown to inform phases later
    if recipes is not None:
        if recipes:
            context.last_recommended_recipes = [r.recipe.title for r in recipes]
            state.recipes_shown = True
        else:
            context.last_recommended_recipes = []

    return display_response, recipes, context
