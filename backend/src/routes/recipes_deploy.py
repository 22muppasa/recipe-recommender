from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import os
import sys
import logging

# Add the src directory to the path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from data_streamer_deploy import RecipeDataStreamerDeploy

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

recipe_bp = Blueprint('recipes', __name__)

# Global data streamer instance
data_streamer = None

def initialize_data_streamer():
    """Initialize the data streamer with deployment optimization"""
    global data_streamer
    
    if data_streamer is not None:
        return True
    
    try:
        # Use the full dataset but with deployment optimization
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        full_file = os.path.join(data_dir, "recipes_deploy_10k.csv")
        
        logger.info(f"🚀 Initializing deployment data streamer with file: {full_file}")
        
        if not os.path.exists(full_file):
            logger.error(f"❌ Dataset file not found: {full_file}")
            return False
        
        data_streamer = RecipeDataStreamerDeploy(full_file)
        
        # Load the dataset with deployment optimization
        if not data_streamer.load_dataset_for_deployment():
            logger.error("❌ Failed to load dataset")
            return False
        
        # Prepare ML data
        if not data_streamer.prepare_ml_data():
            logger.error("❌ Failed to prepare ML data")
            return False
        
        logger.info("✅ Deployment data streamer initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error initializing data streamer: {e}")
        import traceback
        traceback.print_exc()
        return False

# Initialize on module import
logger.info("🚀 Starting recipe backend initialization for deployment...")
if initialize_data_streamer():
    logger.info("✅ Recipe backend ready for deployment!")
else:
    logger.error("❌ Recipe backend initialization failed!")

@recipe_bp.route('/recipes', methods=['GET'])
@cross_origin()
def get_all_recipes():
    """Get all recipes (random sample for performance)"""
    global data_streamer
    
    if data_streamer is None:
        logger.error("❌ Data streamer not initialized")
        return jsonify({'error': 'Backend not ready'}), 500
    
    try:
        recipes = data_streamer.get_random_recipes(count=50)
        logger.info(f"✅ Returning {len(recipes)} random recipes")
        return jsonify(recipes)
    except Exception as e:
        logger.error(f"❌ Error getting recipes: {e}")
        return jsonify({'error': 'Failed to get recipes'}), 500

@recipe_bp.route('/recipes/search', methods=['POST'])
@cross_origin()
def search_recipes():
    """Search recipes by ingredients using ML"""
    global data_streamer
    
    if data_streamer is None:
        logger.error("❌ Data streamer not initialized")
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
        
        # Use ML-powered search
        recommendations = data_streamer.search_recipes(ingredients, top_n)
        
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
    global data_streamer
    
    if data_streamer is None:
        return jsonify({'error': 'Backend not ready'}), 500
    
    try:
        recipe = data_streamer.get_recipe_by_id(recipe_id)
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
    global data_streamer
    
    if data_streamer is None:
        return jsonify([])
    
    try:
        categories = sorted(data_streamer.categories[:20])  # Limit to 20 categories
        return jsonify(categories)
    except Exception as e:
        logger.error(f"❌ Error getting categories: {e}")
        return jsonify([])

@recipe_bp.route('/recipes/random', methods=['GET'])
@cross_origin()
def get_random_recipes():
    """Get random recipes"""
    global data_streamer
    
    if data_streamer is None:
        return jsonify([])
    
    try:
        count = request.args.get('count', 6, type=int)
        count = min(count, 50)  # Limit to 50 max
        
        recipes = data_streamer.get_random_recipes(count)
        logger.info(f"✅ Returning {len(recipes)} random recipes")
        return jsonify(recipes)
    except Exception as e:
        logger.error(f"❌ Error getting random recipes: {e}")
        return jsonify([])

@recipe_bp.route('/recipes/by-category/<category>', methods=['GET'])
@cross_origin()
def get_recipes_by_category(category):
    """Get recipes by category"""
    global data_streamer
    
    if data_streamer is None:
        return jsonify([])
    
    try:
        recipes = data_streamer.get_recipes_by_category(category, limit=20)
        logger.info(f"✅ Returning {len(recipes)} recipes for category: {category}")
        return jsonify(recipes)
    except Exception as e:
        logger.error(f"❌ Error getting recipes by category {category}: {e}")
        return jsonify([])

@recipe_bp.route('/health', methods=['GET'])
@cross_origin()
def health_check():
    """Health check endpoint"""
    global data_streamer
    
    status = {
        'status': 'healthy' if data_streamer is not None else 'unhealthy',
        'dataset_loaded': data_streamer is not None and data_streamer.recipes_df is not None,
        'recipe_count': len(data_streamer.recipes_df) if data_streamer and data_streamer.recipes_df is not None else 0,
        'ml_ready': data_streamer is not None and data_streamer.tfidf_vectorizer is not None,
        'categories_count': len(data_streamer.categories) if data_streamer else 0
    }
    
    return jsonify(status)

@recipe_bp.route('/test-search', methods=['GET'])
@cross_origin()
def test_search():
    """Test endpoint to verify ML search is working"""
    global data_streamer
    
    if data_streamer is None:
        return jsonify({'error': 'Backend not ready'}), 500
    
    try:
        # Test with common ingredients
        test_ingredients = ['chicken', 'rice', 'onion']
        results = data_streamer.search_recipes(test_ingredients, top_n=3)
        
        return jsonify({
            'test_ingredients': test_ingredients,
            'results_count': len(results),
            'results': results
        })
    except Exception as e:
        logger.error(f"❌ Error in test search: {e}")
        return jsonify({'error': 'Test search failed'}), 500

