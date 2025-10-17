from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import os
import sys
import logging

# Add the src directory to the path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from simple_recipe_engine import SimpleRecipeEngine

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

recipe_bp = Blueprint('recipes', __name__)

# Global recipe engine instance
recipe_engine = None

def initialize_recipe_engine():
    """Initialize the simple recipe engine"""
    global recipe_engine
    
    if recipe_engine is not None:
        return True
    
    try:
        # Use the deployment dataset
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        data_file = os.path.join(data_dir, "recipes_deploy_10k.csv")
        
        logger.info(f"🚀 Initializing simple recipe engine with file: {data_file}")
        
        if not os.path.exists(data_file):
            logger.error(f"❌ Dataset file not found: {data_file}")
            return False
        
        recipe_engine = SimpleRecipeEngine(data_file)
        
        # Load the recipes
        if not recipe_engine.load_recipes():
            logger.error("❌ Failed to load recipes")
            return False
        
        logger.info("✅ Simple recipe engine initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error initializing recipe engine: {e}")
        import traceback
        traceback.print_exc()
        return False

# Initialize on module import
logger.info("🚀 Starting simple recipe backend initialization...")
if initialize_recipe_engine():
    logger.info("✅ Simple recipe backend ready!")
else:
    logger.error("❌ Simple recipe backend initialization failed!")

@recipe_bp.route('/recipes', methods=['GET'])
@cross_origin()
def get_all_recipes():
    """Get all recipes (random sample)"""
    global recipe_engine
    
    if recipe_engine is None:
        logger.error("❌ Recipe engine not initialized")
        return jsonify({'error': 'Backend not ready'}), 500
    
    try:
        recipes = recipe_engine.get_random_recipes(count=50)
        logger.info(f"✅ Returning {len(recipes)} random recipes")
        return jsonify(recipes)
    except Exception as e:
        logger.error(f"❌ Error getting recipes: {e}")
        return jsonify({'error': 'Failed to get recipes'}), 500

@recipe_bp.route('/recipes/search', methods=['POST'])
@cross_origin()
def search_recipes():
    """Search recipes by ingredients"""
    global recipe_engine
    
    if recipe_engine is None:
        logger.error("❌ Recipe engine not initialized")
        return jsonify({'error': 'Backend not ready'}), 500
    
    try:
        data = request.get_json()
        
        if not data or 'ingredients' not in data:
            return jsonify({'error': 'Ingredients list is required'}), 400
        
        ingredients = data['ingredients']
        top_n = data.get('top_n', 6)
        
        if not ingredients:
            return jsonify([])
        
        logger.info(f"🔍 API Search request: {ingredients}")
        
        # Use simple ingredient matching
        recommendations = recipe_engine.search_recipes(ingredients, top_n)
        
        logger.info(f"✅ Returning {len(recommendations)} recommendations")
        return jsonify(recommendations)
        
    except Exception as e:
        logger.error(f"❌ Error in search endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Search failed'}), 500

@recipe_bp.route('/recipes/<recipe_id>', methods=['GET'])
@cross_origin()
def get_recipe_by_id(recipe_id):
    """Get a specific recipe by ID"""
    global recipe_engine
    
    if recipe_engine is None:
        return jsonify({'error': 'Backend not ready'}), 500
    
    try:
        recipe = recipe_engine.get_recipe_by_id(recipe_id)
        if recipe:
            return jsonify(recipe)
        else:
            return jsonify({'error': 'Recipe not found'}), 404
    except Exception as e:
        logger.error(f"❌ Error getting recipe {recipe_id}: {e}")
        return jsonify({'error': 'Failed to get recipe'}), 500

@recipe_bp.route('/recipes/categories', methods=['GET'])
@cross_origin()
def get_categories():
    """Get all available recipe categories"""
    global recipe_engine
    
    if recipe_engine is None:
        return jsonify([])
    
    try:
        categories = sorted(recipe_engine.categories[:20])  # Limit to 20 categories
        return jsonify(categories)
    except Exception as e:
        logger.error(f"❌ Error getting categories: {e}")
        return jsonify([])

@recipe_bp.route('/recipes/random', methods=['GET'])
@cross_origin()
def get_random_recipes():
    """Get random recipes"""
    global recipe_engine
    
    if recipe_engine is None:
        return jsonify([])
    
    try:
        count = request.args.get('count', 6, type=int)
        count = min(count, 50)  # Limit to 50 max
        
        recipes = recipe_engine.get_random_recipes(count)
        logger.info(f"✅ Returning {len(recipes)} random recipes")
        return jsonify(recipes)
    except Exception as e:
        logger.error(f"❌ Error getting random recipes: {e}")
        return jsonify([])

@recipe_bp.route('/recipes/by-category/<category>', methods=['GET'])
@cross_origin()
def get_recipes_by_category(category):
    """Get recipes by category"""
    global recipe_engine
    
    if recipe_engine is None:
        return jsonify([])
    
    try:
        recipes = recipe_engine.get_recipes_by_category(category, limit=20)
        logger.info(f"✅ Returning {len(recipes)} recipes for category: {category}")
        return jsonify(recipes)
    except Exception as e:
        logger.error(f"❌ Error getting recipes by category {category}: {e}")
        return jsonify([])

@recipe_bp.route('/health', methods=['GET'])
@cross_origin()
def health_check():
    """Health check endpoint"""
    global recipe_engine
    
    status = {
        'status': 'healthy' if recipe_engine is not None else 'unhealthy',
        'dataset_loaded': recipe_engine is not None and len(recipe_engine.recipes) > 0,
        'recipe_count': len(recipe_engine.recipes) if recipe_engine else 0,
        'search_ready': recipe_engine is not None and len(recipe_engine.ingredient_index) > 0,
        'categories_count': len(recipe_engine.categories) if recipe_engine else 0
    }
    
    return jsonify(status)

@recipe_bp.route('/test-search', methods=['GET'])
@cross_origin()
def test_search():
    """Test endpoint to verify search is working"""
    global recipe_engine
    
    if recipe_engine is None:
        return jsonify({'error': 'Backend not ready'}), 500
    
    try:
        # Test with common ingredients
        test_ingredients = ['chicken', 'rice', 'onion']
        results = recipe_engine.search_recipes(test_ingredients, top_n=3)
        
        return jsonify({
            'test_ingredients': test_ingredients,
            'results_count': len(results),
            'results': results
        })
    except Exception as e:
        logger.error(f"❌ Error in test search: {e}")
        return jsonify({'error': 'Test search failed'}), 500

