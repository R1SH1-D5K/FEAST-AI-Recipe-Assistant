export interface Nutrition {
  calories: number
  protein: number
  carbs: number
  fat: number
  fiber?: number
  sugar?: number
  sodium?: number
}

export interface Ingredient {
  name: string
  quantity: string
  unit: string
  original?: string
}

export interface Recipe {
  id: string
  title: string
  image_url: string
  cuisine: string
  cooking_time?: number
  servings?: number
  ingredients: Ingredient[]
  instructions: string | string[]
  nutrition?: Nutrition
  tags?: string[]
  match_score?: number
  matched_ingredients?: number
  missing_ingredients?: string[]
  source_url?: string
  summary?: string
}

export interface RecipePreview {
  id: string
  title: string
  image_url: string
  cuisine: string
  cooking_time?: number
  nutrition?: Nutrition
  summary?: string
}

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  recipePreviews?: RecipePreview[]
  fullRecipe?: Recipe
}

export interface ConversationContext {
  ingredients?: string[]
  allergies?: string[]
  cuisine_preference?: string
  dietary_restrictions?: string[]
  meal_type?: string
  cooking_time?: string
  skill_level?: string
  servings?: number
  flavor_preferences?: string[]
  dislikes?: string[]
  last_recommended_recipes?: string[]
}

export interface ChatRequest {
  message: string
  conversation_history: Array<{ role: string; content: string }>
  context?: ConversationContext
}

export interface ChatResponse {
  message: string
  recipes: Recipe[]
  context: ConversationContext
  error?: string
  quota_remaining: number
}
