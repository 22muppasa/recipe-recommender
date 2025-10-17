from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import os
import ast
import random
import pandas as pd
import numpy as np
from joblib import load
from src.data_processor import initialize_data

recipe_bp = Blueprint('recipes', __name__)

# Data paths
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUT_CSV_LOOKUP = os.path.join(DATA_DIR, "recipes_lookup.csv")
VEC_PATH = os.path.join(DATA_DIR, "tfidf_vectorizer.joblib")
MATRIX_PATH = os.path.join(DATA_DIR, "tfidf_matrix.joblib")
DF_PATH = os.path.join(DATA_DIR, "recipes_df.joblib")

# Global variables for loaded data
tfidf_vectorizer = None
tfidf_matrix = None
df_ingredients = None
df_lookup = None
lookup_by_id = None

def load_data():
    """Load the processed data and ML model"""
    global tfidf_vectorizer, tfidf_matrix, df_ingredients, df_lookup, lookup_by_id
    
    try:
        # Initialize data if not exists
        if not all(os.path.exists(p) for p in [VEC_PATH, MATRIX_PATH, DF_PATH, OUT_CSV_LOOKUP]):
            print("Data files not found. Initializing...")
            if not initialize_data():
                return False
        
        # Load ML model components
        tfidf_vectorizer = load(VEC_PATH)
        tfidf_matrix = load(MATRIX_PATH)
        df_ingredients = load(DF_PATH)
        
        # Load lookup data
        df_lookup = pd.read_csv(OUT_CSV_LOOKUP)
        lookup_by_id = {row["RecipeId"]: row for _, row in df_lookup.iterrows()}
        
        print(f"✅ Loaded {len(df_ingredients)} recipes for recommendations")
        print(f"✅ Loaded {len(df_lookup)} recipes for lookup")
        return True
        
    except Exception as e:
        print(f"Error loading data: {e}")
        return False

def safe_str(val):
    """Safely convert to string, handle NaN values"""
    if pd.isna(val):
        return ""
    return str(val)

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

def format_recipe_for_frontend(recipe_row, similarity_score=None):
    """Convert a recipe row to frontend format"""
    # Parse ingredients
    ingredients = []
    try:
        if hasattr(recipe_row, 'CleanedIngredients'):
            ingredients_str = recipe_row['CleanedIngredients']
        else:
            ingredients_str = recipe_row.get('CleanedIngredients', '[]')
        ingredients = ast.literal_eval(ingredients_str) if ingredients_str else []
    except:
        ingredients = []
    
    # Parse instructions
    instructions = []
    instructions_str = safe_str(recipe_row.get('Instructions', ''))
    if instructions_str:
        # Split numbered instructions
        lines = instructions_str.split('\n')
        instructions = [line.strip() for line in lines if line.strip()]
    
    # Generate a placeholder image URL based on category
    category = safe_str(recipe_row.get('RecipeCategory', 'food'))
    image_keywords = {
        'italian': 'pasta',
        'mediterranean': 'salmon',
        'thai': 'curry',
        'french': 'chocolate',
        'korean': 'bibimbap',
        'moroccan': 'tagine',
        'asian': 'stir-fry',
        'mexican': 'tacos',
        'indian': 'curry',
        'chinese': 'noodles'
    }
    keyword = image_keywords.get(category.lower(), 'food')
    image_url = f"https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800&h=600&fit=crop&q=food+{keyword}"
    
    # Extract cook time from TotalTime or CookTime
    cook_time = 30  # default
    total_time_str = safe_str(recipe_row.get('TotalTime', ''))
    cook_time_str = safe_str(recipe_row.get('CookTime', ''))
    
    # Try to extract minutes from time strings (format: PT30M)
    for time_str in [total_time_str, cook_time_str]:
        if 'PT' in time_str and 'M' in time_str:
            try:
                minutes = int(time_str.replace('PT', '').replace('M', ''))
                cook_time = minutes
                break
            except:
                pass
    
    recipe = {
        'id': str(recipe_row.get('RecipeId', '')),
        'title': safe_str(recipe_row.get('Name', 'Untitled Recipe')),
        'description': safe_str(recipe_row.get('Description', 'Delicious recipe')),
        'image': image_url,
        'cookTime': cook_time,
        'servings': safe_int(recipe_row.get('RecipeServings')) or 4,
        'rating': round(random.uniform(4.2, 4.9), 1),  # Random rating for demo
        'category': safe_str(recipe_row.get('RecipeCategory', 'General')),
        'difficulty': random.choice(['Easy', 'Medium', 'Hard']),  # Random difficulty for demo
        'ingredients': ingredients,
        'instructions': instructions,
        'nutrition': {
            'calories': safe_float(recipe_row.get('Calories')),
            'protein': safe_float(recipe_row.get('ProteinContent')),
            'fat': safe_float(recipe_row.get('FatContent')),
            'carbs': safe_float(recipe_row.get('CarbohydrateContent'))
        }
    }
    
    if similarity_score is not None:
        recipe['similarityScore'] = similarity_score
    
    return recipe

# Load data when module is imported
load_data()

# Sample fallback recipes in case data loading fails
SAMPLE_RECIPES = [
]

def get_recommendations_ml(ingredients_list, top_n=6):
    """
    Get recipe recommendations using machine learning model
    Returns list of top_n dicts with recipe data
    """
    global tfidf_vectorizer, tfidf_matrix, df_ingredients, lookup_by_id
    
    if tfidf_vectorizer is None or tfidf_matrix is None or df_ingredients is None:
        print("ML model not loaded, falling back to sample data")
        return []
    
    cleaned = [str(ing).strip().lower() for ing in ingredients_list if str(ing).strip()]
    if not cleaned:
        return []

    q = " ".join(cleaned)
    q_vec = tfidf_vectorizer.transform([q])
    scores = (tfidf_matrix @ q_vec.T).toarray().ravel()

    if top_n >= len(scores):
        top_idx = np.argsort(scores)[::-1]
    else:
        part = np.argpartition(scores, -top_n)[-top_n:]
        top_idx = part[np.argsort(scores[part])[::-1]]

    recommendations = []
    for idx in top_idx:
        if scores[idx] > 0:  # Only include recipes with some similarity
            recipe_id = df_ingredients.iloc[idx]["RecipeId"]
            recipe_data = lookup_by_id.get(recipe_id)
            if recipe_data is not None:
                recipe = format_recipe_for_frontend(recipe_data, float(scores[idx]))
                recommendations.append(recipe)
    
    return recommendations

@recipe_bp.route('/recipes', methods=['GET'])
@cross_origin()
def get_all_recipes():
    """Get all recipes (limited sample for performance)"""
    global df_lookup
    
    if df_lookup is None:
        return jsonify([])
    
    # Return a random sample of recipes
    sample_size = min(50, len(df_lookup))
    sample_recipes = df_lookup.sample(n=sample_size)
    
    recipes = []
    for _, recipe_row in sample_recipes.iterrows():
        recipe = format_recipe_for_frontend(recipe_row)
        recipes.append(recipe)
    
    return jsonify(recipes)

@recipe_bp.route('/recipes/search', methods=['POST'])
@cross_origin()
def search_recipes():
    """Search recipes by ingredients using ML model"""
    data = request.get_json()
    
    if not data or 'ingredients' not in data:
        return jsonify({'error': 'Ingredients list is required'}), 400
    
    ingredients = data['ingredients']
    top_n = data.get('top_n', 6)
    
    if not ingredients:
        return jsonify([])
    
    # Use ML model for recommendations
    recommendations = get_recommendations_ml(ingredients, top_n)
    
    return jsonify(recommendations)

@recipe_bp.route('/recipes/<recipe_id>', methods=['GET'])
@cross_origin()
def get_recipe_by_id(recipe_id):
    """Get a specific recipe by ID"""
    global lookup_by_id
    
    if lookup_by_id is None:
        return jsonify({'error': 'Recipe data not loaded'}), 500
    
    recipe_data = lookup_by_id.get(recipe_id)
    if recipe_data is not None:
        recipe = format_recipe_for_frontend(recipe_data)
        return jsonify(recipe)
    else:
        return jsonify({'error': 'Recipe not found'}), 404

@recipe_bp.route('/recipes/categories', methods=['GET'])
@cross_origin()
def get_categories():
    """Get all available recipe categories"""
    global df_lookup
    
    if df_lookup is None:
        return jsonify([])
    
    categories = df_lookup['RecipeCategory'].dropna().unique().tolist()
    categories = [cat for cat in categories if cat and str(cat).strip()]
    return jsonify(sorted(categories))

@recipe_bp.route('/recipes/random', methods=['GET'])
@cross_origin()
def get_random_recipes():
    """Get random recipes"""
    global df_lookup
    
    if df_lookup is None:
        return jsonify([])
    
    count = request.args.get('count', 6, type=int)
    count = min(count, len(df_lookup))
    
    random_recipes_data = df_lookup.sample(n=count)
    recipes = []
    
    for _, recipe_row in random_recipes_data.iterrows():
        recipe = format_recipe_for_frontend(recipe_row)
        recipes.append(recipe)
    
    return jsonify(recipes)

@recipe_bp.route('/recipes/by-category/<category>', methods=['GET'])
@cross_origin()
def get_recipes_by_category(category):
    """Get recipes by category"""
    global df_lookup
    
    if df_lookup is None:
        return jsonify([])
    
    filtered_recipes = df_lookup[df_lookup['RecipeCategory'].str.contains(category, case=False, na=False)]
    
    # Limit results for performance
    sample_size = min(20, len(filtered_recipes))
    if len(filtered_recipes) > sample_size:
        filtered_recipes = filtered_recipes.sample(n=sample_size)
    
    recipes = []
    for _, recipe_row in filtered_recipes.iterrows():
        recipe = format_recipe_for_frontend(recipe_row)
        recipes.append(recipe)
    
    return jsonify(recipes)

