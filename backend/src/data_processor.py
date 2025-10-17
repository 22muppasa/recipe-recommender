import re
import csv
import os
import ast
import pandas as pd
import numpy as np
from ast import literal_eval
from datasets import load_dataset
from sklearn.feature_extraction.text import TfidfVectorizer
from joblib import dump, load

# --- CONFIG ---
HF_DATASET = "untitledwebsite123/food-recipes"
DATA_FILE = "recipes.csv"
SPLIT = "train"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OUT_CSV_ING = os.path.join(DATA_DIR, "processed_recipes.csv")
OUT_CSV_LOOKUP = os.path.join(DATA_DIR, "recipes_lookup.csv")
VEC_PATH = os.path.join(DATA_DIR, "tfidf_vectorizer.joblib")
MATRIX_PATH = os.path.join(DATA_DIR, "tfidf_matrix.joblib")
DF_PATH = os.path.join(DATA_DIR, "recipes_df.joblib")

# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)

# --- Helpers ---
_r_list_re = re.compile(r'^\s*c\((.*)\)\s*$', re.DOTALL)

def parse_r_list_string(val):
    """
    Accepts:
      - R-like: c("a","b") or c('a','b')
      - JSON-like lists: '["a","b"]'
      - Already-parsed Python lists
      - None/NaN/empty strings
    Returns a Python list[str].
    """
    if val is None:
        return []

    if isinstance(val, list):
        return [str(x) for x in val]

    if isinstance(val, str):
        s = val.strip()
        if not s:
            return []

        m = _r_list_re.match(s)
        if m:
            content = m.group(1)
            items = re.findall(r'"([^"]*)"|\'([^\']*)\'', content)
            return [x for tup in items for x in tup if x]

        if s.startswith('[') and s.endswith(']'):
            try:
                parsed = literal_eval(s)
                if isinstance(parsed, list):
                    return [str(x) for x in parsed]
            except Exception:
                pass

    return [str(val)]

def clean_ingredient(ing):
    return str(ing).strip().lower()

def normalize_instructions(raw):
    """
    Normalize instructions into a single string with numbered steps.
    Handles list-like values (R c(), JSON, Python list) or plain strings.
    """
    steps = parse_r_list_string(raw)
    # If parse fell back to a single giant string, split on common delimiters
    if len(steps) == 1 and ("\n" in steps[0] or "." in steps[0]):
        blob = steps[0]
        # try splitting by newlines first, then fallback to period
        chunks = [line.strip() for line in blob.split("\n") if line.strip()]
        if len(chunks) < 2:
            chunks = [p.strip() for p in blob.split(".") if p.strip()]
        steps = chunks
    steps = [s.strip() for s in steps if s and s.strip()]
    if not steps:
        return ""
    return "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))

def safe_float(val):
    """Safely convert to float, return None if invalid"""
    try:
        if pd.isna(val):
            return None
        return float(val)
    except (ValueError, TypeError):
        return None

def safe_int(val):
    """Safely convert to int, return None if invalid"""
    try:
        if pd.isna(val):
            return None
        return int(float(val))
    except (ValueError, TypeError):
        return None

def process_dataset():
    """Process the Hugging Face dataset and create processed files"""
    print("Loading dataset from Hugging Face...")
    
    try:
        ds = load_dataset(HF_DATASET, data_files=DATA_FILE, streaming=True, split=SPLIT)
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return False

    # Open both CSVs and write headers
    with open(OUT_CSV_ING, "w", newline="", encoding="utf-8") as f_ing, \
         open(OUT_CSV_LOOKUP, "w", newline="", encoding="utf-8") as f_lu:

        w_ing = csv.writer(f_ing)
        w_lu = csv.writer(f_lu)

        # processed ingredients file (for vectorization/recs)
        w_ing.writerow([
            "RecipeId",
            "Name",
            "CleanedIngredients",
            "Calories",
            "ProteinContent",
            "FatContent",
            "CarbohydrateContent",
        ])

        # lookup file (for fetching instructions + recipe info)
        w_lu.writerow([
            "RecipeId",
            "Name",
            "Instructions",
            "Description",
            "RecipeCategory",
            "RecipeCuisine",
            "TotalTime",
            "PrepTime",
            "CookTime",
            "RecipeServings",
            "Calories",
            "ProteinContent",
            "FatContent",
            "CarbohydrateContent",
            "Keywords",
            "RecipeUrl",
        ])

        processed_count = 0
        for i, row in enumerate(ds):
            # Common fields
            recipe_id = row.get("RecipeId")
            name = row.get("Name")

            # Skip if essential fields are missing
            if not recipe_id or not name:
                continue

            # ---- Ingredients (cleaned) ----
            raw_parts = row.get("RecipeIngredientParts")
            parts = parse_r_list_string(raw_parts)
            cleaned = [clean_ingredient(x) for x in parts]

            # Skip recipes with no ingredients
            if not cleaned:
                continue

            calories = safe_float(row.get("Calories"))
            protein = safe_float(row.get("ProteinContent"))
            fat = safe_float(row.get("FatContent"))
            carbs = safe_float(row.get("CarbohydrateContent"))

            # Write to processed ingredients CSV
            w_ing.writerow([
                recipe_id,
                name,
                str(cleaned),
                calories,
                protein,
                fat,
                carbs,
            ])

            # ---- Instructions & metadata for lookup ----
            instructions = normalize_instructions(row.get("RecipeInstructions"))
            description = row.get("Description", "")
            category = row.get("RecipeCategory", "")
            cuisine = row.get("RecipeCuisine", "")
            tot_time = row.get("TotalTime", "")
            prep_time = row.get("PrepTime", "")
            cook_time = row.get("CookTime", "")
            servings = safe_int(row.get("RecipeServings"))
            keywords = row.get("Keywords", "")
            url = row.get("RecipeUrl") or row.get("URL") or row.get("Url") or ""

            w_lu.writerow([
                recipe_id,
                name,
                instructions,
                description,
                category,
                cuisine,
                tot_time,
                prep_time,
                cook_time,
                servings,
                calories,
                protein,
                fat,
                carbs,
                keywords,
                url,
            ])

            processed_count += 1
            if processed_count % 1000 == 0:
                print(f"Processed {processed_count} recipes...")
            
            # Limit to first 5000 recipes for demo purposes
            if processed_count >= 5000:
                break

    print(f"✅ Done. Processed {processed_count} recipes.")
    print(f"Saved {OUT_CSV_ING} and {OUT_CSV_LOOKUP}.")
    return True

def build_recommendation_model():
    """Build the TF-IDF recommendation model"""
    print("Building recommendation model...")
    
    if not os.path.exists(OUT_CSV_ING):
        print("Processed ingredients file not found. Run process_dataset() first.")
        return False

    # Load processed data
    usecols = ["RecipeId", "Name", "CleanedIngredients"]
    df = pd.read_csv(OUT_CSV_ING, usecols=usecols)

    def safe_list_eval(s):
        try:
            v = ast.literal_eval(s)
            return v if isinstance(v, list) else []
        except Exception:
            return []

    df["CleanedIngredients"] = df["CleanedIngredients"].apply(safe_list_eval)
    df["IngredientsString"] = df["CleanedIngredients"].apply(lambda x: " ".join(x))

    # Build TF-IDF vectorizer and matrix
    tfidf_vectorizer = TfidfVectorizer(
        preprocessor=None,
        tokenizer=str.split,
        lowercase=False,
        dtype=np.float32,
        min_df=2,
        max_features=50000,
        ngram_range=(1, 1)
    )
    
    tfidf_matrix = tfidf_vectorizer.fit_transform(df["IngredientsString"])
    
    # Save the model components
    dump(tfidf_vectorizer, VEC_PATH)
    dump(tfidf_matrix, MATRIX_PATH)
    dump(df, DF_PATH)
    
    print(f"✅ Model built and saved. Matrix shape: {tfidf_matrix.shape}")
    return True

def initialize_data():
    """Initialize data processing and model building"""
    print("Initializing recipe data and recommendation model...")
    
    # Check if processed files already exist
    if (os.path.exists(OUT_CSV_ING) and os.path.exists(OUT_CSV_LOOKUP) and 
        os.path.exists(VEC_PATH) and os.path.exists(MATRIX_PATH) and os.path.exists(DF_PATH)):
        print("✅ Data and model files already exist.")
        return True
    
    # Process dataset
    if not process_dataset():
        return False
    
    # Build recommendation model
    if not build_recommendation_model():
        return False
    
    print("✅ Data initialization complete!")
    return True

if __name__ == "__main__":
    initialize_data()

