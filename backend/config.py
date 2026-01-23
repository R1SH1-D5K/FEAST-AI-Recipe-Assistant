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

# Turso Configuration
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "libsql://feast-db-kiillah.aws-ap-south-1.turso.io")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3Njc2MzQzNDksImlkIjoiMzM2ODE1YmQtNWIyYi00Yzk5LThlNTgtYTkyYjZjZmRiOTIxIiwicmlkIjoiYmE0M2ExNWUtYWY2Yi00ODE2LWE2MjAtN2YxOWU1OGU3MTMzIn0.hJ1G71EgWtGfrKl-dF4VIjCGTMG1c4ohlKtYCmL2Qfk8t3WZnfM8TIsn1IxeH27vsCGyB4VEA33IKZFEzzpFBA")
USE_TURSO = os.getenv("USE_TURSO", "true").lower() == "true"

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
SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY", "ba13a882d7414ac3a81aab1c3f0a8a61")
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
