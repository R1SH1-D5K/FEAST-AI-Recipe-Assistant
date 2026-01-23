"""
LLM Integration
Handles communication with the configured LLM via OpenRouter API (current: Gemma)
"""

import time
import httpx

from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    LLM_MODEL,  # LLM model identifier (currently Gemma via OpenRouter)
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    LLM_TIMEOUT,
    LLM_MAX_RETRIES
)


class LLMError(Exception):
    """Base exception for LLM-related errors"""
    pass


class RateLimitError(LLMError):
    """Raised when API rate limit is hit"""
    pass


class APIError(LLMError):
    """Raised for general API errors"""
    pass


def call_llm(
    messages: list[dict],
    model: str = LLM_MODEL,
    temperature: float = LLM_TEMPERATURE,
    max_tokens: int = LLM_MAX_TOKENS,
    timeout: int = LLM_TIMEOUT
) -> str:
    """Call configured LLM via OpenRouter API"""
    if not OPENROUTER_API_KEY:
        raise APIError(
            "OpenRouter API key not found. "
            "Please set OPENROUTER_API_KEY in your .env file."
        )
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://feast-recipe-assistant.app",
        "X-Title": "FEAST Recipe Assistant"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    last_error = None
    
    for attempt in range(LLM_MAX_RETRIES):
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    OPENROUTER_BASE_URL,
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 2 ** attempt))
                    if attempt < LLM_MAX_RETRIES - 1:
                        time.sleep(retry_after)
                        continue
                    raise RateLimitError(
                        f"Rate limited by OpenRouter. Please try again in {retry_after} seconds."
                    )
                
                if response.status_code != 200:
                    error_detail = response.text
                    try:
                        error_json = response.json()
                        error_detail = error_json.get("error", {}).get("message", error_detail)
                    except:
                        pass
                    raise APIError(f"API error ({response.status_code}): {error_detail}")
                
                data = response.json()
                
                if "choices" not in data or len(data["choices"]) == 0:
                    raise APIError("Invalid API response: no choices returned")
                
                content = data["choices"][0].get("message", {}).get("content", "")
                
                if not content:
                    raise APIError("Empty response from API")
                
                return content
                
        except httpx.TimeoutException:
            last_error = APIError(f"Request timed out after {timeout} seconds")
            if attempt < LLM_MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
                
        except httpx.RequestError as e:
            last_error = APIError(f"Network error: {str(e)}")
            if attempt < LLM_MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
    
    if last_error:
        raise last_error
    raise APIError("Failed to get response after multiple attempts")


async def call_llm_async(
    messages: list[dict],
    model: str = LLM_MODEL,
    temperature: float = LLM_TEMPERATURE,
    max_tokens: int = LLM_MAX_TOKENS,
    timeout: int = LLM_TIMEOUT
) -> str:
    """Async version of call_llm"""
    if not OPENROUTER_API_KEY:
        raise APIError(
            "OpenRouter API key not found. "
            "Please set OPENROUTER_API_KEY in your .env file."
        )
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://feast-recipe-assistant.app",
        "X-Title": "FEAST Recipe Assistant"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    import asyncio
    
    last_error = None
    
    for attempt in range(LLM_MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    OPENROUTER_BASE_URL,
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 2 ** attempt))
                    if attempt < LLM_MAX_RETRIES - 1:
                        await asyncio.sleep(retry_after)
                        continue
                    raise RateLimitError(
                        f"Rate limited. Please try again in {retry_after} seconds."
                    )
                
                if response.status_code != 200:
                    error_detail = response.text
                    try:
                        error_json = response.json()
                        error_detail = error_json.get("error", {}).get("message", error_detail)
                    except:
                        pass
                    raise APIError(f"API error ({response.status_code}): {error_detail}")
                
                data = response.json()
                
                if "choices" not in data or len(data["choices"]) == 0:
                    raise APIError("Invalid API response: no choices returned")
                
                content = data["choices"][0].get("message", {}).get("content", "")
                
                if not content:
                    raise APIError("Empty response from API")
                
                return content
                
        except httpx.TimeoutException:
            last_error = APIError(f"Request timed out after {timeout} seconds")
            if attempt < LLM_MAX_RETRIES - 1:
                await asyncio.sleep(2 ** attempt)
                continue
                
        except httpx.RequestError as e:
            last_error = APIError(f"Network error: {str(e)}")
            if attempt < LLM_MAX_RETRIES - 1:
                await asyncio.sleep(2 ** attempt)
                continue
    
    if last_error:
        raise last_error
    raise APIError("Failed to get response after multiple attempts")
