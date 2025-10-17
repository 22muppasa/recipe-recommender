from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import os
import pandas as pd
import numpy as np
import re
import random
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import ast

recipe_bp = Blueprint('recipes', __name__)

# Global variables for loaded data
recipes_df = None
tfidf_vectorizer = None
tfidf_matrix = None
categories = []

def parse_r_list(r_string):
    """Parse R-style list notation c(...) into Python list"""
    if pd.isna(r_string) or not r_string:
        return []
    
    # Handle simple string case
    if not r_string.startswith('c('):
        return [r_string.strip('"')]
    
    try:
        # Remove c( and )
        content = r_string[2:-1]
        
        # Split by comma but respect quoted strings
        items = []
        current_item = ""
        in_quotes = False
        quote_char = None
        
        i = 0
        while i < len(content):
            char = content[i]
            
            if char in ['"', "'"] and (i == 0 or content[i-1] != '\\'):
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                    quote_char = None
            elif char == ',' and not in_quotes:
                items.append(current_item.strip().strip('"').strip("'"))
                current_item = ""
                i += 1
                continue
            
            current_item += char
            i += 1
        
        # Add the last item
        if current_item.strip():
            items.append(current_item.strip().strip('"').strip("'"))
        
        return [item for item in items if item]
    
    except Exception as e:
        print(f"Error parsing R list: {e}")
        return []

def extract_time_minutes(time_str):
    """Extract minutes from time string (format: PT30M)"""
    if not time_str or pd.isna(time_str):
        return 30  # default
    
    try:
        if 'PT' in str(time_str):
            time_str = str(time_str)
            if 'H' in time_str and 'M' in time_str:
                # Format like PT1H30M
                hours = int(re.search(r'(\d+)H', time_str).group(1))
                minutes = int(re.search(r'(\d+)M', time_str).group(1))
                return hours * 60 + minutes
            elif 'H' in time_str:
                # Format like PT1H
                hours = int(re.search(r'(\d+)H', time_str).group(1))
                return hours * 60
            elif 'M' in time_str:
                # Format like PT30M
                minutes = int(re.search(r'(\d+)M', time_str).group(1))
                return minutes
    except:
        pass
    
    return 30

def safe_float(val):
    """Safely convert to float"""
    try:
        if pd.isna(val) or val == '':
            return None
        return float(val)
    except:
        return None

def safe_int(val):
    """Safely convert to int"""
    try:
        if pd.isna(val) or val == '':
            return None
        return int(float(val))
    except:
        return None

def get_first_image(images_str):
    """Extract the first image URL from the images string"""
    images = parse_r_list(images_str)
    if images:
        return images[0]
    return "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800&h=600&fit=crop&q=food"

def format_recipe_for_frontend(row):
    """Convert a recipe row to frontend format"""
    ingredients_parts = parse_r_list(row.get('RecipeIngredientParts', ''))
    ingredients_quantities = parse_r_list(row.get('RecipeIngredientQuantities', ''))
    instructions = parse_r_list(row.get('RecipeInstructions', ''))
    
    # Combine ingredients with quantities
    ingredients = []
    for i, part in enumerate(ingredients_parts):
        if i < len(ingredients_quantities) and ingredients_quantities[i]:
            ingredients.append(f"{ingredients_quantities[i]} {part}")
        else:
            ingredients.append(part)
    
    # Get the first image from the dataset
    image_url = get_first_image(row.get('Images', ''))
    
    # Extract cook time
    total_time = extract_time_minutes(row.get('TotalTime'))
    cook_time = extract_time_minutes(row.get('CookTime'))
    final_cook_time = cook_time if cook_time != 30 else total_time
    
    # Determine difficulty based on cook time and instruction count
    difficulty = "Easy"
    if final_cook_time > 60 or len(instructions) > 8:
        difficulty = "Hard"
    elif final_cook_time > 30 or len(instructions) > 5:
        difficulty = "Medium"
    
    recipe = {
        'id': str(row.get('RecipeId', '')),
        'title': str(row.get('Name', 'Untitled Recipe')),
        'description': str(row.get('Description', 'Delicious recipe')),
        'image': image_url,
        'cookTime': final_cook_time,
        'servings': safe_int(row.get('RecipeServings')) or 4,
        'rating': safe_float(row.get('AggregatedRating')) or round(random.uniform(4.2, 4.9), 1),
        'category': str(row.get('RecipeCategory', 'General')),
        'difficulty': difficulty,
        'ingredients': ingredients,
        'instructions': instructions,
        'nutrition': {
            'calories': safe_float(row.get('Calories')),
            'protein': safe_float(row.get('ProteinContent')),
            'fat': safe_float(row.get('FatContent')),
            'carbs': safe_float(row.get('CarbohydrateContent'))
        }
    }
    
    return recipe

def load_ml_data():
    """Load recipe data and prepare ML models"""
    global recipes_df, tfidf_vectorizer, tfidf_matrix, categories
    
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    full_file = os.path.join(data_dir, "recipes_full.csv")
    
    if not os.path.exists(full_file):
        print("Full recipe file not found")
        return False
    
    try:
        print("Loading full dataset...")
        recipes_df = pd.read_csv(full_file)
        
        # Filter out recipes with missing essential data
        recipes_df = recipes_df.dropna(subset=['Name', 'RecipeIngredientParts'])
        
        # Take a sample for performance (can be increased)
        if len(recipes_df) > 10000:
            recipes_df = recipes_df.sample(n=10000, random_state=42)
        
        print(f"✅ Loaded {len(recipes_df)} recipes")
        
        # Extract categories
        categories = list(recipes_df['RecipeCategory'].dropna().unique())
        categories = [cat for cat in categories if cat and str(cat).strip()]
        
        # Prepare ingredients text for ML
        ingredients_text = []
        for _, row in recipes_df.iterrows():
            ingredients = parse_r_list(row.get('RecipeIngredientParts', ''))
            ingredients_text.append(' '.join(ingredients))
        
        # Create TF-IDF vectorizer
        print("Creating TF-IDF vectors...")
        tfidf_vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2
        )
        
        tfidf_matrix = tfidf_vectorizer.fit_transform(ingredients_text)
        
        print(f"✅ Created TF-IDF matrix with shape {tfidf_matrix.shape}")
        print(f"✅ Found {len(categories)} categories")
        
        return True
        
    except Exception as e:
        print(f"Error loading ML data: {e}")
        return False

def ml_ingredient_search(search_ingredients, top_n=6):
    """ML-powered ingredient search using TF-IDF and cosine similarity"""
    if not search_ingredients or tfidf_vectorizer is None:
        return []
    
    try:
        # Create query vector
        query_text = ' '.join(search_ingredients)
        query_vector = tfidf_vectorizer.transform([query_text])
        
        # Calculate similarities
        similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()
        
        # Get top matches
        top_indices = similarities.argsort()[-top_n:][::-1]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0:  # Only include recipes with some similarity
                row = recipes_df.iloc[idx]
                recipe = format_recipe_for_frontend(row)
                recipe['similarityScore'] = float(similarities[idx])
                results.append(recipe)
        
        return results
        
    except Exception as e:
        print(f"Error in ML search: {e}")
        return []

# Load data when module is imported
load_ml_data()

@recipe_bp.route('/recipes', methods=['GET'])
@cross_origin()
def get_all_recipes():
    """Get all recipes (limited sample for performance)"""
    if recipes_df is None or len(recipes_df) == 0:
        return jsonify([])
    
    # Return a random sample of recipes
    sample_size = min(50, len(recipes_df))
    sample_recipes = recipes_df.sample(n=sample_size)
    
    recipes = []
    for _, row in sample_recipes.iterrows():
        recipe = format_recipe_for_frontend(row)
        recipes.append(recipe)
    
    return jsonify(recipes)

@recipe_bp.route('/recipes/search', methods=['POST'])
@cross_origin()
def search_recipes():
    """Search recipes by ingredients using ML"""
    data = request.get_json()
    
    if not data or 'ingredients' not in data:
        return jsonify({'error': 'Ingredients list is required'}), 400
    
    ingredients = data['ingredients']
    top_n = data.get('top_n', 6)
    
    if not ingredients:
        return jsonify([])
    
    # Use ML-powered search
    recommendations = ml_ingredient_search(ingredients, top_n)
    
    return jsonify(recommendations)

@recipe_bp.route('/recipes/<recipe_id>', methods=['GET'])
@cross_origin()
def get_recipe_by_id(recipe_id):
    """Get a specific recipe by ID"""
    if recipes_df is None:
        return jsonify({'error': 'Dataset not loaded'}), 500
    
    recipe_data = recipes_df[recipes_df['RecipeId'] == int(recipe_id)]
    if len(recipe_data) > 0:
        recipe = format_recipe_for_frontend(recipe_data.iloc[0])
        return jsonify(recipe)
    else:
        return jsonify({'error': 'Recipe not found'}), 404

@recipe_bp.route('/recipes/categories', methods=['GET'])
@cross_origin()
def get_categories():
    """Get all available recipe categories"""
    return jsonify(sorted(categories[:15]))  # Limit to 15 categories

@recipe_bp.route('/recipes/random', methods=['GET'])
@cross_origin()
def get_random_recipes():
    """Get random recipes"""
    if recipes_df is None or len(recipes_df) == 0:
        return jsonify([])
    
    count = request.args.get('count', 6, type=int)
    count = min(count, len(recipes_df))
    
    random_recipes_data = recipes_df.sample(n=count)
    recipes = []
    
    for _, row in random_recipes_data.iterrows():
        recipe = format_recipe_for_frontend(row)
        recipes.append(recipe)
    
    return jsonify(recipes)

@recipe_bp.route('/recipes/by-category/<category>', methods=['GET'])
@cross_origin()
def get_recipes_by_category(category):
    """Get recipes by category"""
    if recipes_df is None:
        return jsonify([])
    
    filtered_recipes = recipes_df[recipes_df['RecipeCategory'].str.contains(category, case=False, na=False)]
    
    # Limit results for performance
    sample_size = min(20, len(filtered_recipes))
    if len(filtered_recipes) > sample_size:
        filtered_recipes = filtered_recipes.sample(n=sample_size)
    
    recipes = []
    for _, row in filtered_recipes.iterrows():
        recipe = format_recipe_for_frontend(row)
        recipes.append(recipe)
    
    return jsonify(recipes)

