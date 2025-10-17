from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import os
import csv
import random
import re

recipe_bp = Blueprint('recipes', __name__)

# Global variables for loaded data
recipes_data = []
categories = []

def load_simple_data():
    """Load recipe data from CSV files without ML dependencies"""
    global recipes_data, categories
    
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    lookup_file = os.path.join(data_dir, "recipes_lookup.csv")
    
    if not os.path.exists(lookup_file):
        print("Recipe lookup file not found")
        return False
    
    try:
        with open(lookup_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            recipes_data = list(reader)
        
        # Extract categories
        categories = list(set(recipe.get('RecipeCategory', '') for recipe in recipes_data if recipe.get('RecipeCategory')))
        categories = [cat for cat in categories if cat and cat.strip()]
        
        print(f"✅ Loaded {len(recipes_data)} recipes")
        print(f"✅ Found {len(categories)} categories")
        return True
        
    except Exception as e:
        print(f"Error loading data: {e}")
        return False

def safe_str(val):
    """Safely convert to string, handle None values"""
    if val is None or val == '':
        return ""
    return str(val)

def safe_float(val):
    """Safely convert to float, return None if invalid"""
    try:
        if val is None or val == '':
            return None
        return float(val)
    except (ValueError, TypeError):
        return None

def safe_int(val):
    """Safely convert to int, return None if invalid"""
    try:
        if val is None or val == '':
            return None
        return int(float(val))
    except (ValueError, TypeError):
        return None

def parse_ingredients(ingredients_str):
    """Parse ingredients string into a list"""
    if not ingredients_str:
        return []
    
    try:
        # Try to parse as a list string
        if ingredients_str.startswith('[') and ingredients_str.endswith(']'):
            # Remove brackets and split by comma
            content = ingredients_str[1:-1]
            ingredients = [item.strip().strip("'\"") for item in content.split(',')]
            return [ing for ing in ingredients if ing]
    except:
        pass
    
    return []

def parse_instructions(instructions_str):
    """Parse instructions string into a list"""
    if not instructions_str:
        return []
    
    lines = instructions_str.split('\n')
    return [line.strip() for line in lines if line.strip()]

def extract_time_minutes(time_str):
    """Extract minutes from time string (format: PT30M)"""
    if not time_str or 'PT' not in time_str:
        return 30  # default
    
    try:
        if 'M' in time_str:
            minutes = int(time_str.replace('PT', '').replace('M', ''))
            return minutes
    except:
        pass
    
    return 30

def format_recipe_for_frontend(recipe_row):
    """Convert a recipe row to frontend format"""
    ingredients = parse_ingredients(recipe_row.get('CleanedIngredients', ''))
    instructions = parse_instructions(recipe_row.get('Instructions', ''))
    
    # Generate image URL based on category
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
    
    # Extract cook time
    total_time = extract_time_minutes(safe_str(recipe_row.get('TotalTime', '')))
    cook_time = extract_time_minutes(safe_str(recipe_row.get('CookTime', '')))
    final_cook_time = cook_time if cook_time != 30 else total_time
    
    recipe = {
        'id': str(recipe_row.get('RecipeId', '')),
        'title': safe_str(recipe_row.get('Name', 'Untitled Recipe')),
        'description': safe_str(recipe_row.get('Description', 'Delicious recipe')),
        'image': image_url,
        'cookTime': final_cook_time,
        'servings': safe_int(recipe_row.get('RecipeServings')) or 4,
        'rating': round(random.uniform(4.2, 4.9), 1),
        'category': safe_str(recipe_row.get('RecipeCategory', 'General')),
        'difficulty': random.choice(['Easy', 'Medium', 'Hard']),
        'ingredients': ingredients,
        'instructions': instructions,
        'nutrition': {
            'calories': safe_float(recipe_row.get('Calories')),
            'protein': safe_float(recipe_row.get('ProteinContent')),
            'fat': safe_float(recipe_row.get('FatContent')),
            'carbs': safe_float(recipe_row.get('CarbohydrateContent'))
        }
    }
    
    return recipe

def simple_ingredient_search(search_ingredients, recipes, top_n=6):
    """Simple ingredient-based search without ML"""
    if not search_ingredients:
        return []
    
    search_terms = [term.lower().strip() for term in search_ingredients]
    scored_recipes = []
    
    for recipe in recipes:
        ingredients = parse_ingredients(recipe.get('CleanedIngredients', ''))
        ingredients_text = ' '.join(ingredients).lower()
        
        # Calculate simple similarity score
        matches = 0
        for term in search_terms:
            if term in ingredients_text:
                matches += 1
        
        if matches > 0:
            score = matches / len(search_terms)
            recipe_formatted = format_recipe_for_frontend(recipe)
            recipe_formatted['similarityScore'] = score
            scored_recipes.append(recipe_formatted)
    
    # Sort by score and return top N
    scored_recipes.sort(key=lambda x: x['similarityScore'], reverse=True)
    return scored_recipes[:top_n]

# Load data when module is imported
load_simple_data()

@recipe_bp.route('/recipes', methods=['GET'])
@cross_origin()
def get_all_recipes():
    """Get all recipes (limited sample for performance)"""
    if not recipes_data:
        return jsonify([])
    
    # Return a random sample of recipes
    sample_size = min(50, len(recipes_data))
    sample_recipes = random.sample(recipes_data, sample_size)
    
    recipes = []
    for recipe_row in sample_recipes:
        recipe = format_recipe_for_frontend(recipe_row)
        recipes.append(recipe)
    
    return jsonify(recipes)

@recipe_bp.route('/recipes/search', methods=['POST'])
@cross_origin()
def search_recipes():
    """Search recipes by ingredients using simple matching"""
    data = request.get_json()
    
    if not data or 'ingredients' not in data:
        return jsonify({'error': 'Ingredients list is required'}), 400
    
    ingredients = data['ingredients']
    top_n = data.get('top_n', 6)
    
    if not ingredients:
        return jsonify([])
    
    # Use simple search
    recommendations = simple_ingredient_search(ingredients, recipes_data, top_n)
    
    return jsonify(recommendations)

@recipe_bp.route('/recipes/<recipe_id>', methods=['GET'])
@cross_origin()
def get_recipe_by_id(recipe_id):
    """Get a specific recipe by ID"""
    recipe_data = next((r for r in recipes_data if r.get('RecipeId') == recipe_id), None)
    if recipe_data:
        recipe = format_recipe_for_frontend(recipe_data)
        return jsonify(recipe)
    else:
        return jsonify({'error': 'Recipe not found'}), 404

@recipe_bp.route('/recipes/categories', methods=['GET'])
@cross_origin()
def get_categories():
    """Get all available recipe categories"""
    return jsonify(sorted(categories[:10]))  # Limit to 10 categories

@recipe_bp.route('/recipes/random', methods=['GET'])
@cross_origin()
def get_random_recipes():
    """Get random recipes"""
    if not recipes_data:
        return jsonify([])
    
    count = request.args.get('count', 6, type=int)
    count = min(count, len(recipes_data))
    
    random_recipes_data = random.sample(recipes_data, count)
    recipes = []
    
    for recipe_row in random_recipes_data:
        recipe = format_recipe_for_frontend(recipe_row)
        recipes.append(recipe)
    
    return jsonify(recipes)

@recipe_bp.route('/recipes/by-category/<category>', methods=['GET'])
@cross_origin()
def get_recipes_by_category(category):
    """Get recipes by category"""
    filtered_recipes = [r for r in recipes_data if category.lower() in r.get('RecipeCategory', '').lower()]
    
    # Limit results for performance
    sample_size = min(20, len(filtered_recipes))
    if len(filtered_recipes) > sample_size:
        filtered_recipes = random.sample(filtered_recipes, sample_size)
    
    recipes = []
    for recipe_row in filtered_recipes:
        recipe = format_recipe_for_frontend(recipe_row)
        recipes.append(recipe)
    
    return jsonify(recipes)

