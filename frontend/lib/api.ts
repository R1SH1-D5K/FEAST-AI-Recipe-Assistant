/**
 * FEAST API Client
 * Handles all communication with the FastAPI backend
 */

import type { ChatRequest, ChatResponse, Recipe, ConversationContext } from "./types"

// API Base URL - configurable via environment variable
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

/**
 * Custom error class for API errors
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public details?: string
  ) {
    super(message)
    this.name = "ApiError"
  }
}

/**
 * Health check response type
 */
export interface HealthResponse {
  status: "healthy" | "low_quota" | "quota_exhausted" | "unhealthy"
  recipe_count: number
  quota_remaining: number
}

/**
 * Quota response type
 */
export interface QuotaResponse {
  remaining: number
  daily_limit: number
  status: "ok" | "low"
}

/**
 * Check if the backend is healthy
 */
export async function checkHealth(): Promise<HealthResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`)
    if (!response.ok) {
      throw new ApiError("Health check failed", response.status)
    }
    return await response.json()
  } catch (error) {
    console.error("Health check error:", error)
    throw error
  }
}

/**
 * Get current API quota status
 */
export async function getQuota(): Promise<QuotaResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/quota`)
    if (!response.ok) {
      throw new ApiError("Failed to fetch quota", response.status)
    }
    return await response.json()
  } catch (error) {
    console.error("Quota fetch error:", error)
    throw error
  }
}

/**
 * Send a chat message to the backend
 */
export async function sendChatMessage(
  message: string,
  conversationHistory: Array<{ role: string; content: string }> = [],
  context?: ConversationContext
): Promise<ChatResponse> {
  try {
    const requestBody: ChatRequest = {
      message,
      conversation_history: conversationHistory,
      context,
    }

    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestBody),
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new ApiError(
        errorData.detail || "Failed to send message",
        response.status,
        JSON.stringify(errorData)
      )
    }

    const data: ChatResponse = await response.json()
    return data
  } catch (error) {
    console.error("Chat error:", error)
    if (error instanceof ApiError) throw error
    throw new ApiError("Network error occurred")
  }
}

/**
 * Get a specific recipe by ID
 */
export async function getRecipeById(recipeId: string): Promise<Recipe> {
  try {
    const response = await fetch(`${API_BASE_URL}/recipe/${recipeId}`)
    
    if (!response.ok) {
      throw new ApiError("Recipe not found", response.status)
    }

    const data: Recipe = await response.json()
    return data
  } catch (error) {
    console.error("Get recipe error:", error)
    if (error instanceof ApiError) throw error
    throw new ApiError("Failed to fetch recipe")
  }
}

/**
 * Get full recipe details (expands preview to full recipe)
 */
export async function expandRecipe(recipeId: string): Promise<Recipe> {
  try {
    const response = await fetch(`${API_BASE_URL}/recipe/${recipeId}/expand`)
    
    if (!response.ok) {
      throw new ApiError("Failed to expand recipe", response.status)
    }

    const data: Recipe = await response.json()
    return data
  } catch (error) {
    console.error("Expand recipe error:", error)
    if (error instanceof ApiError) throw error
    throw new ApiError("Failed to expand recipe")
  }
}

/**
 * Get random recipes
 */
export async function getRandomRecipes(count: number = 5, tags: string = ""): Promise<Recipe[]> {
  try {
    const params = new URLSearchParams({
      count: count.toString(),
      ...(tags && { tags }),
    })

    const response = await fetch(`${API_BASE_URL}/recipes/random?${params}`)
    
    if (!response.ok) {
      throw new ApiError("Failed to fetch random recipes", response.status)
    }

    const data: Recipe[] = await response.json()
    return data
  } catch (error) {
    console.error("Random recipes error:", error)
    if (error instanceof ApiError) throw error
    throw new ApiError("Failed to fetch random recipes")
  }
}

/**
 * Search recipes
 */
export async function searchRecipes(params: {
  query?: string
  cuisine?: string
  diet?: string
  intolerances?: string
  ingredients?: string
  maxTime?: number
  limit?: number
}): Promise<Recipe[]> {
  try {
    const searchParams = new URLSearchParams()
    
    if (params.query) searchParams.append("query", params.query)
    if (params.cuisine) searchParams.append("cuisine", params.cuisine)
    if (params.diet) searchParams.append("diet", params.diet)
    if (params.intolerances) searchParams.append("intolerances", params.intolerances)
    if (params.ingredients) searchParams.append("ingredients", params.ingredients)
    if (params.maxTime) searchParams.append("maxTime", params.maxTime.toString())
    if (params.limit) searchParams.append("limit", params.limit.toString())

    const response = await fetch(`${API_BASE_URL}/recipes/search?${searchParams}`)
    
    if (!response.ok) {
      throw new ApiError("Failed to search recipes", response.status)
    }

    const data: Recipe[] = await response.json()
    return data
  } catch (error) {
    console.error("Search recipes error:", error)
    if (error instanceof ApiError) throw error
    throw new ApiError("Failed to search recipes")
  }
}

/**
 * Helper to convert recipe to preview format
 */
export function toPreview(recipe: Recipe) {
  return {
    id: recipe.id,
    title: recipe.title,
    image_url: recipe.image_url,
    cuisine: recipe.cuisine,
    cooking_time: recipe.cooking_time,
    nutrition: recipe.nutrition,
    summary: recipe.summary,
  }
}
