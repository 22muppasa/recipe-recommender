from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import os
import re
import random
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

recipe_bp = Blueprint('recipes', __name__)

# Global variables for loaded data
recipes_df = None
tfidf_vectorizer = None
tfidf_matrix = None
categories = []


def parse_r_list(r_string):
    """Parse R-style list notation c(...) into Python list."""
    if pd.isna(r_string) or not r_string:
        return []

    r_string = str(r_string)

    # Simple string case (not wrapped in c())
    if not r_string.startswith('c('):
        return [r_string.strip().strip('"').strip("'")]

    try:
        # Remove c( and trailing )
        content = r_string[2:-1]

        items = []
        current_item = ""
        in_quotes = False
        quote_char = None

        i = 0
        while i < len(content):
            char = content[i]

            if char in ['"', "'"] and (i == 0 or content[i - 1] != '\\'):
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                    quote_char = None
            elif char == ',' and not in_quotes:
                stripped = current_item.strip().strip('"').strip("'")
                if stripped:
                    items.append(stripped)
                current_item = ""
                i += 1
                continue

            current_item += char
            i += 1

        if current_item.strip():
            stripped = current_item.strip().strip('"').strip("'")
            if stripped:
                items.append(stripped)

        return items
    except Exception as e:
        print(f"Error parsing R list: {e}")
        return []


def extract_time_minutes(time_str):
    """Extract minutes from an ISO 8601-like time string (e.g., PT30M, PT1H30M)."""
    if not time_str or pd.isna(time_str):
        return 30

    try:
        time_str = str(time_str)
        if 'PT' not in time_str:
            return 30

        hours_match = re.search(r'(\d+)H', time_str)
        minutes_match = re.search(r'(\d+)M', time_str)

        hours = int(hours_match.group(1)) if hours_match else 0
        minutes = int(minutes_match.group(1)) if minutes_match else 0

        total = hours * 60 + minutes
        return total if total > 0 else 30
    except Exception:
        return 30


def safe_float(val):
    """Safely convert to float; return None if not possible."""
    try:
        if pd.isna(val) or val == '' or val is None:
            return None
        return float(val)
    except Exception:
        return None


def safe_int(val):
    """Safely convert to int; return None if not possible."""
    try:
        if pd.isna(val) or val == '' or val is None:
            return None
        return int(float(val))
    except Exception:
        return None


def get_first_image(images_str):
    """Extract the first image URL from the images string."""
    images = parse_r_list(images_str)
    if images:
        url = str(images[0]).strip()
        if url.startswith('http'):
            return url

    # Fallback placeholder image
    return "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800&h=600&fit=crop&q=food"


def format_recipe_for_frontend(row):
    """Convert a recipe row to a dict suitable for the frontend."""
    ingredients_parts = parse_r_list(row.get('RecipeIngredientParts', ''))
    ingredients_quantities = parse_r_list(row.get('RecipeIngredientQuantities', ''))
    instructions = parse_r_list(row.get('RecipeInstructions', ''))

    # Combine ingredients with quantities
    ingredients = []
    for i, part in enumerate(ingredients_parts):
        part_str = str(part).strip()
        if i < len(ingredients_quantities) and ingredients_quantities[i]:
            qty = str(ingredients_quantities[i]).strip()
            ingredients.append(f"{qty} {part_str}" if qty else part_str)
        else:
            ingredients.append(part_str)

    image_url = get_first_image(row.get('Images', ''))

    total_time = extract_time_minutes(row.get('TotalTime'))
    cook_time = extract_time_minutes(row.get('CookTime'))
    final_cook_time = cook_time if cook_time != 30 else total_time

    # Determine difficulty based on time and instruction count
    difficulty = "Easy"
    if final_cook_time > 60 or len(instructions) > 8:
        difficulty = "Hard"
    elif final_cook_time > 30 or len(instructions) > 5:
        difficulty = "Medium"

    return {
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
            'carbs': safe_float(row.get('CarbohydrateContent')),
        },
    }


def load_ml_data():
    """Load recipe data and prepare TF-IDF matrix."""
    global recipes_df, tfidf_vectorizer, tfidf_matrix, categories

    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    full_file = os.path.join(data_dir, "recipes_full.csv")

    if not os.path.exists(full_file):
        print("Full recipe file not found:", full_file)
        return False

    try:
        df = pd.read_csv(full_file)
        df = df.dropna(subset=['Name', 'RecipeIngredientParts'])

        # Sample for performance
        if len(df) > 10000:
            df = df.sample(n=10000, random_state=42)

        # Categories
        cats = df['RecipeCategory'].dropna().unique()
        cat_list = [str(cat).strip() for cat in cats if str(cat).strip()]

        # Prepare ingredients text for ML
        ingredients_text = []
        for _, row in df.iterrows():
            ingredients = parse_r_list(row.get('RecipeIngredientParts', ''))
            ingredients_text.append(' '.join(ingredients))

        if not ingredients_text:
            print("No ingredient text found.")
            return False

        vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2,
        )
        matrix = vectorizer.fit_transform(ingredients_text)

        recipes_df = df
        tfidf_vectorizer = vectorizer
        tfidf_matrix = matrix
        categories[:] = cat_list

        print(f"Loaded {len(recipes_df)} recipes. TF-IDF shape: {tfidf_matrix.shape}")
        return True
    except Exception as e:
        print(f"Error loading ML data: {e}")
        return False


def ml_ingredient_search(search_ingredients, top_n=6):
    """Ingredient search using TF-IDF and cosine similarity."""
    if not search_ingredients or tfidf_vectorizer is None or tfidf_matrix is None or recipes_df is None:
        return []

    try:
        query_text = ' '.join(str(ing) for ing in search_ingredients if ing)
        if not query_text.strip():
            return []

        query_vector = tfidf_vectorizer.transform([query_text])
        similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()

        # Take extra top candidates, then filter
        top_indices = similarities.argsort()[-top_n * 2:][::-1]

        results = []
        for idx in top_indices:
            if len(results) >= top_n:
                break
            if similarities[idx] <= 0:
                continue

            row = recipes_df.iloc[idx]
            recipe = format_recipe_for_frontend(row)
            if recipe:
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
    """Get a random sample of recipes."""
    if recipes_df is None or len(recipes_df) == 0:
        return jsonify([])

    sample_size = min(50, len(recipes_df))
    sample_recipes = recipes_df.sample(n=sample_size)

    recipes = []
    for _, row in sample_recipes.iterrows():
        recipes.append(format_recipe_for_frontend(row))

    return jsonify(recipes)


@recipe_bp.route('/recipes/search', methods=['POST'])
@cross_origin()
def search_recipes():
    """Search recipes by ingredients using ML."""
    data = request.get_json()

    if not data or 'ingredients' not in data:
        return jsonify({'error': 'Ingredients list is required'}), 400

    ingredients = data['ingredients']
    top_n = data.get('top_n', 6)

    if not ingredients:
        return jsonify([])

    recommendations = ml_ingredient_search(ingredients, top_n)
    return jsonify(recommendations)


@recipe_bp.route('/recipes/<recipe_id>', methods=['GET'])
@cross_origin()
def get_recipe_by_id(recipe_id):
    """Get a specific recipe by ID."""
    if recipes_df is None:
        return jsonify({'error': 'Dataset not loaded'}), 500

    try:
        recipe_data = recipes_df[recipes_df['RecipeId'] == int(recipe_id)]
    except ValueError:
        return jsonify({'error': 'Invalid recipe id'}), 400

    if len(recipe_data) > 0:
        recipe = format_recipe_for_frontend(recipe_data.iloc[0])
        return jsonify(recipe)

    return jsonify({'error': 'Recipe not found'}), 404


@recipe_bp.route('/recipes/categories', methods=['GET'])
@cross_origin()
def get_categories_route():
    """Get a subset of available recipe categories."""
    return jsonify(sorted(categories[:15]))


@recipe_bp.route('/recipes/random', methods=['GET'])
@cross_origin()
def get_random_recipes():
    """Get random recipes."""
    if recipes_df is None or len(recipes_df) == 0:
        return jsonify([])

    count = request.args.get('count', 6, type=int)
    count = min(count, len(recipes_df))

    random_recipes_data = recipes_df.sample(n=count)
    recipes = [format_recipe_for_frontend(row) for _, row in random_recipes_data.iterrows()]

    return jsonify(recipes)


@recipe_bp.route('/recipes/by-category/<category>', methods=['GET'])
@cross_origin()
def get_recipes_by_category(category):
    """Get recipes by category."""
    if recipes_df is None:
        return jsonify([])

    filtered_recipes = recipes_df[
        recipes_df['RecipeCategory'].str.contains(category, case=False, na=False)
    ]

    sample_size = min(20, len(filtered_recipes))
    if len(filtered_recipes) > sample_size:
        filtered_recipes = filtered_recipes.sample(n=sample_size)

    recipes = [format_recipe_for_frontend(row) for _, row in filtered_recipes.iterrows()]
    return jsonify(recipes)
