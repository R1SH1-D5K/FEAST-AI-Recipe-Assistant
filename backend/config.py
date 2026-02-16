"""
FEAST Backend Configuration
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "recipes.db"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# OpenRouter Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
LLM_MODEL = "google/gemma-3-27b-it:free"                                         # primary model via OpenRouter
DEEPSEEK_MODEL = LLM_MODEL  # compatibility alias for legacy naming

# LLM Settings
LLM_TEMPERATURE = 0.7
LLM_MAX_TOKENS = 1000
LLM_TIMEOUT = 30
LLM_MAX_RETRIES = 3

# Search Settings
MAX_CANDIDATES = 5
MIN_INGREDIENT_MATCH_SCORE = 0.3

# Spoonacular API Configuration
SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY", "")
SPOONACULAR_BASE_URL = "https://api.spoonacular.com"

# TheMealDB API (legacy - kept for reference)
MEALDB_API_URL = "https://www.themealdb.com/api/json/v1/1"

# CORS - Frontend URLs
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    os.getenv("FRONTEND_URL", ""),  # Production frontend URL
]
# Filter empty strings
CORS_ORIGINS = [origin for origin in CORS_ORIGINS if origin]

# Supported cuisines
SUPPORTED_CUISINES = [
    "american", "british", "canadian", "chinese", "croatian", "dutch",
    "egyptian", "filipino", "french", "greek", "indian", "irish",
    "italian", "jamaican", "japanese", "kenyan", "malaysian", "mexican",
    "moroccan", "polish", "portuguese", "russian", "spanish", "thai",
    "tunisian", "turkish", "vietnamese"
]

# Common allergens
COMMON_ALLERGENS = [
    "peanuts", "tree nuts", "dairy", "eggs", "gluten",
    "shellfish", "fish", "soy", "sesame"
]
