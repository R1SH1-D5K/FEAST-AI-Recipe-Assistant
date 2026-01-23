"""Test recipe search"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "data" / "recipes.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Test 1: Search for "chicken fried rice" in title
print("=== Test 1: Recipes with 'chicken fried rice' in title ===")
results = cursor.execute(
    "SELECT title, cuisine FROM recipes WHERE LOWER(title) LIKE ? LIMIT 10",
    ('%chicken%fried%rice%',)
).fetchall()
print(f"Found {len(results)} matches:")
for title, cuisine in results:
    print(f"  - {title} ({cuisine})")

# Test 2: Search for "pancake" in title
print("\n=== Test 2: Recipes with 'pancake' in title ===")
results = cursor.execute(
    "SELECT title, cuisine FROM recipes WHERE LOWER(title) LIKE ? LIMIT 10",
    ('%pancake%',)
).fetchall()
print(f"Found {len(results)} matches:")
for title, cuisine in results:
    print(f"  - {title} ({cuisine})")

# Test 3: Count total recipes
print("\n=== Test 3: Total recipe count ===")
count = cursor.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]
print(f"Total recipes in database: {count:,}")

conn.close()
