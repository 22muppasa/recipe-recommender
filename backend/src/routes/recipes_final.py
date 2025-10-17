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
import json

recipe_bp = Blueprint('recipes', __name__)

# Global variables for loaded data
recipes_df = None
tfidf_vectorizer = None
tfidf_matrix = None
categories = []

def parse_r_list(r_string):
    """Parse R-style list notation c(...) into Python list"""
    if pd.isna(r_string) or not r_string or r_string == '':
        return []
    
    r_string = str(r_string).strip()
    
    # Handle simple string case (not wrapped in c())
    if not r_string.startswith('c('):
        # Remove quotes if present
        if r_string.startswith('"') and r_string.endswith('"'):
            return [r_string[1:-1]]
        return [r_string]
    
    try:
        # Remove c( and )
        content = r_string[2:-1].strip()
        
        if not content:
            return []
        
        # Split by comma but respect quoted strings
        items = []
        current_item = ""
        in_quotes = False
        quote_char = None
        escape_next = False
        
        i = 0
        while i < len(content):
            char = content[i]
            
            if escape_next:
                current_item += char
                escape_next = False
            elif char == '\\':
                escape_next = True
                current_item += char
            elif char in ['"', "'"] and not escape_next:
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                    quote_char = None
                current_item += char
            elif char == ',' and not in_quotes:
                # End of current item
                item = current_item.strip()
                if item.startswith('"') and item.endswith('"'):
                    item = item[1:-1]
                elif item.startswith("'") and item.endswith("'"):
                    item = item[1:-1]
                
                if item:  # Only add non-empty items
                    items.append(item)
                current_item = ""
            else:
                current_item += char
            
            i += 1
        
        # Add the last item
        if current_item.strip():
            item = current_item.strip()
            if item.startswith('"') and item.endswith('"'):
                item = item[1:-1]
            elif item.startswith("'") and item.endswith("'"):
                item = item[1:-1]
            
            if item:
                items.append(item)
        
        return items
    
    except Exception as e:
        print(f"Error parsing R list '{r_string[:100]}...': {e}")
        return []

def extract_time_minutes(time_str):
    """Extract minutes from time string (format: PT30M)"""
    if not time_str or pd.isna(time_str):
        return 30  # default
    
    try:
        time_str = str(time_str).strip()
        if 'PT' in time_str:
            if 'H' in time_str and 'M' in time_str:
                # Format like PT1H30M
                hours_match = re.search(r'(\d+)H', time_str)
                minutes_match = re.search(r'(\d+)M', time_str)
                hours = int(hours_match.group(1)) if hours_match else 0
                minutes = int(minutes_match.group(1)) if minutes_match else 0
                return hours * 60 + minutes
            elif 'H' in time_str:
                # Format like PT1H
                hours_match = re.search(r'(\d+)H', time_str)
                hours = int(hours_match.group(1)) if hours_match else 0
                return hours * 60
            elif 'M' in time_str:
                # Format like PT30M
                minutes_match = re.search(r'(\d+)M', time_str)
                minutes = int(minutes_match.group(1)) if minutes_match else 30
                return minutes
        else:
            # Try to extract just numbers
            numbers = re.findall(r'\d+', time_str)
            if numbers:
                return int(numbers[0])
    except Exception as e:
        print(f"Error parsing time '{time_str}': {e}")
    
    return 30

def safe_float(val):
    """Safely convert to float"""
    try:
        if pd.isna(val) or val == '' or val is None:
            return None
        return float(val)
    except:
        return None

def safe_int(val):
    """Safely convert to int"""
    try:
        if pd.isna(val) or val == '' or val is None:
            return None
        return int(float(val))
    except:
        return None

def get_first_image(images_str):
    """Extract the first image URL from the images string"""
    images = parse_r_list(images_str)
    if images and len(images) > 0:
        # Clean the URL - remove any extra characters
        url = images[0].strip()
        # Validate it's a proper URL
        if url.startswith('http'):
            return url
    
    # Fallback to a food-related placeholder
    return "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800&h=600&fit=crop&q=food"

def format_recipe_for_frontend(row):
    """Convert a recipe row to frontend format"""
    try:
        # Parse ingredients
        ingredients_parts = parse_r_list(row.get('RecipeIngredientParts', ''))
        ingredients_quantities = parse_r_list(row.get('RecipeIngredientQuantities', ''))
        instructions = parse_r_list(row.get('RecipeInstructions', ''))
        
        # Combine ingredients with quantities
        ingredients = []
        for i, part in enumerate(ingredients_parts):
            if i < len(ingredients_quantities) and ingredients_quantities[i]:
                quantity = str(ingredients_quantities[i]).strip()
                ingredient = str(part).strip()
                if quantity and ingredient:
                    ingredients.append(f"{quantity} {ingredient}")
                else:
                    ingredients.append(ingredient)
            else:
                ingredients.append(str(part).strip())
        
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
        
        # Clean up instructions - remove empty ones
        instructions = [inst.strip() for inst in instructions if inst and inst.strip()]
        
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
    except Exception as e:
        print(f"Error formatting recipe {row.get('RecipeId', 'unknown')}: {e}")
        return None

def load_ml_data():
    """Load recipe data and prepare ML models"""
    global recipes_df, tfidf_vectorizer, tfidf_matrix, categories
    
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    full_file = os.path.join(data_dir, "recipes_deploy.csv")
    
    if not os.path.exists(full_file):
        print("❌ Full recipe file not found")
        return False
    
    try:
        print("📊 Loading full dataset...")
        recipes_df = pd.read_csv(full_file)
        
        # Filter out recipes with missing essential data
        initial_count = len(recipes_df)
        recipes_df = recipes_df.dropna(subset=['Name', 'RecipeIngredientParts'])
        filtered_count = len(recipes_df)
        
        print(f"📊 Filtered from {initial_count} to {filtered_count} recipes")
        
        # Take a manageable sample for performance (increase for production)
        sample_size = min(5000, len(recipes_df))  # Use all available recipes from smaller dataset
        if len(recipes_df) > sample_size:
            recipes_df = recipes_df.sample(n=sample_size, random_state=42)
        
        print(f"✅ Using {len(recipes_df)} recipes for ML processing")
        
        # Extract categories
        categories = list(recipes_df['RecipeCategory'].dropna().unique())
        categories = [cat for cat in categories if cat and str(cat).strip() and str(cat) != 'nan']
        
        # Prepare ingredients text for ML
        print("🔄 Preparing ingredient text for ML...")
        ingredients_text = []
        valid_indices = []
        
        for idx, (_, row) in enumerate(recipes_df.iterrows()):
            try:
                ingredients = parse_r_list(row.get('RecipeIngredientParts', ''))
                if ingredients:
                    # Clean and join ingredients
                    clean_ingredients = [ing.lower().strip() for ing in ingredients if ing and ing.strip()]
                    if clean_ingredients:
                        ingredients_text.append(' '.join(clean_ingredients))
                        valid_indices.append(idx)
            except Exception as e:
                print(f"Error processing ingredients for recipe {row.get('RecipeId', 'unknown')}: {e}")
        
        # Filter dataframe to only include recipes with valid ingredients
        recipes_df = recipes_df.iloc[valid_indices].reset_index(drop=True)
        
        print(f"✅ Processed {len(ingredients_text)} recipes with valid ingredients")
        
        # Create TF-IDF vectorizer
        print("🤖 Creating TF-IDF vectors...")
        tfidf_vectorizer = TfidfVectorizer(
            max_features=3000,  # Reduced for better performance
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.8,
            lowercase=True
        )
        
        tfidf_matrix = tfidf_vectorizer.fit_transform(ingredients_text)
        
        print(f"✅ Created TF-IDF matrix with shape {tfidf_matrix.shape}")
        print(f"✅ Found {len(categories)} categories")
        
        # Test the ML functionality
        print("🧪 Testing ML functionality...")
        test_results = ml_ingredient_search(['chicken', 'rice'], top_n=3)
        if test_results:
            print(f"✅ ML test successful - found {len(test_results)} results")
        else:
            print("⚠️ ML test returned no results")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading ML data: {e}")
        import traceback
        traceback.print_exc()
        return False

def ml_ingredient_search(search_ingredients, top_n=6):
    """ML-powered ingredient search using TF-IDF and cosine similarity"""
    if not search_ingredients or tfidf_vectorizer is None or recipes_df is None:
        print("❌ ML search: Missing data or vectorizer")
        return []
    
    try:
        # Clean and prepare query
        clean_ingredients = [ing.lower().strip() for ing in search_ingredients if ing and ing.strip()]
        if not clean_ingredients:
            return []
        
        query_text = ' '.join(clean_ingredients)
        print(f"🔍 Searching for: {query_text}")
        
        # Create query vector
        query_vector = tfidf_vectorizer.transform([query_text])
        
        # Calculate similarities
        similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()
        
        # Get top matches
        top_indices = similarities.argsort()[-top_n*2:][::-1]  # Get more candidates
        
        results = []
        for idx in top_indices:
            if len(results) >= top_n:
                break
                
            if similarities[idx] > 0.01:  # Lower threshold for better recall
                try:
                    row = recipes_df.iloc[idx]
                    recipe = format_recipe_for_frontend(row)
                    if recipe and recipe.get('ingredients'):  # Only include recipes with ingredients
                        recipe['similarityScore'] = float(similarities[idx])
                        results.append(recipe)
                except Exception as e:
                    print(f"Error formatting recipe at index {idx}: {e}")
                    continue
        
        print(f"✅ Found {len(results)} matching recipes")
        return results
        
    except Exception as e:
        print(f"❌ Error in ML search: {e}")
        import traceback
        traceback.print_exc()
        return []

# Load data when module is imported
print("🚀 Initializing recipe backend...")
if load_ml_data():
    print("✅ Recipe backend initialized successfully")
else:
    print("❌ Failed to initialize recipe backend")

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
        if recipe:
            recipes.append(recipe)
    
    return jsonify(recipes)

@recipe_bp.route('/recipes/search', methods=['POST'])
@cross_origin()
def search_recipes():
    """Search recipes by ingredients using ML"""
    try:
        data = request.get_json()
        
        if not data or 'ingredients' not in data:
            return jsonify({'error': 'Ingredients list is required'}), 400
        
        ingredients = data['ingredients']
        top_n = data.get('top_n', 6)
        
        if not ingredients:
            return jsonify([])
        
        print(f"🔍 API Search request: {ingredients}")
        
        # Use ML-powered search
        recommendations = ml_ingredient_search(ingredients, top_n)
        
        print(f"✅ Returning {len(recommendations)} recommendations")
        return jsonify(recommendations)
        
    except Exception as e:
        print(f"❌ Error in search endpoint: {e}")
        return jsonify({'error': 'Search failed'}), 500

@recipe_bp.route('/recipes/<recipe_id>', methods=['GET'])
@cross_origin()
def get_recipe_by_id(recipe_id):
    """Get a specific recipe by ID"""
    if recipes_df is None:
        return jsonify({'error': 'Dataset not loaded'}), 500
    
    try:
        recipe_data = recipes_df[recipes_df['RecipeId'] == int(recipe_id)]
        if len(recipe_data) > 0:
            recipe = format_recipe_for_frontend(recipe_data.iloc[0])
            if recipe:
                return jsonify(recipe)
        
        return jsonify({'error': 'Recipe not found'}), 404
    except Exception as e:
        print(f"Error getting recipe {recipe_id}: {e}")
        return jsonify({'error': 'Failed to get recipe'}), 500

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
    count = min(count, len(recipes_df), 20)  # Limit to 20 max
    
    random_recipes_data = recipes_df.sample(n=count)
    recipes = []
    
    for _, row in random_recipes_data.iterrows():
        recipe = format_recipe_for_frontend(row)
        if recipe:
            recipes.append(recipe)
    
    return jsonify(recipes)

@recipe_bp.route('/recipes/by-category/<category>', methods=['GET'])
@cross_origin()
def get_recipes_by_category(category):
    """Get recipes by category"""
    if recipes_df is None:
        return jsonify([])
    
    try:
        filtered_recipes = recipes_df[recipes_df['RecipeCategory'].str.contains(category, case=False, na=False)]
        
        # Limit results for performance
        sample_size = min(20, len(filtered_recipes))
        if len(filtered_recipes) > sample_size:
            filtered_recipes = filtered_recipes.sample(n=sample_size)
        
        recipes = []
        for _, row in filtered_recipes.iterrows():
            recipe = format_recipe_for_frontend(row)
            if recipe:
                recipes.append(recipe)
        
        return jsonify(recipes)
    except Exception as e:
        print(f"Error getting recipes by category {category}: {e}")
        return jsonify([])

@recipe_bp.route('/health', methods=['GET'])
@cross_origin()
def health_check():
    """Health check endpoint"""
    status = {
        'status': 'healthy',
        'dataset_loaded': recipes_df is not None,
        'recipe_count': len(recipes_df) if recipes_df is not None else 0,
        'ml_ready': tfidf_vectorizer is not None,
        'categories_count': len(categories)
    }
    return jsonify(status)

