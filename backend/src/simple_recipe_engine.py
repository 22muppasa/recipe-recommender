import csv
import json
import re
import os
import logging
from collections import defaultdict, Counter
import math

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleRecipeEngine:
    def __init__(self, data_file_path):
        self.data_file_path = data_file_path
        self.recipes = []
        self.categories = []
        self.ingredient_index = defaultdict(set)  # ingredient -> set of recipe indices
        
    def parse_r_list(self, r_string):
        """Parse R-style list notation c(...) into Python list"""
        if not r_string or r_string == '' or r_string == 'nan':
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
            
            # Simple parsing - split by comma and clean quotes
            items = []
            parts = content.split('","')
            
            for i, part in enumerate(parts):
                # Clean up quotes
                part = part.strip()
                if part.startswith('"'):
                    part = part[1:]
                if part.endswith('"'):
                    part = part[:-1]
                
                if part:
                    items.append(part)
            
            return items
        
        except Exception as e:
            logger.warning(f"Error parsing R list '{r_string[:100]}...': {e}")
            return []

    def load_recipes(self):
        """Load recipes from CSV file"""
        logger.info("🚀 Loading recipes from CSV...")
        
        if not os.path.exists(self.data_file_path):
            logger.error(f"❌ Dataset file not found: {self.data_file_path}")
            return False
        
        try:
            with open(self.data_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for i, row in enumerate(reader):
                    if i >= 10000:  # Limit for deployment
                        break
                    
                    if i % 1000 == 0:
                        logger.info(f"📊 Processed {i} recipes...")
                    
                    try:
                        recipe = self.process_recipe_row(row, i)
                        if recipe:
                            self.recipes.append(recipe)
                            
                            # Build ingredient index
                            for ingredient in recipe.get('ingredients', []):
                                # Extract key words from ingredient
                                words = self.extract_ingredient_words(ingredient)
                                for word in words:
                                    self.ingredient_index[word.lower()].add(len(self.recipes) - 1)
                    
                    except Exception as e:
                        logger.warning(f"Error processing recipe {i}: {e}")
                        continue
            
            # Extract unique categories
            self.categories = list(set([r['category'] for r in self.recipes if r.get('category')]))
            
            logger.info(f"✅ Loaded {len(self.recipes)} recipes with {len(self.categories)} categories")
            
            # Test search
            test_results = self.search_recipes(['chicken'], top_n=3)
            logger.info(f"🧪 Test search found {len(test_results)} results")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading recipes: {e}")
            return False
    
    def extract_ingredient_words(self, ingredient):
        """Extract meaningful words from ingredient string"""
        # Remove quantities and common words
        ingredient = ingredient.lower()
        # Remove numbers and measurements
        ingredient = re.sub(r'\d+', '', ingredient)
        ingredient = re.sub(r'\b(cup|cups|tablespoon|tablespoons|teaspoon|teaspoons|pound|pounds|ounce|ounces|lb|lbs|oz|tsp|tbsp|clove|cloves)\b', '', ingredient)
        
        # Extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', ingredient)
        return [w for w in words if w not in ['and', 'the', 'for', 'with', 'fresh', 'dried', 'chopped', 'sliced', 'diced']]
    
    def extract_time_minutes(self, time_str):
        """Extract minutes from time string"""
        if not time_str or time_str == 'nan':
            return 30
        
        try:
            time_str = str(time_str).strip()
            if 'PT' in time_str:
                if 'H' in time_str and 'M' in time_str:
                    hours_match = re.search(r'(\d+)H', time_str)
                    minutes_match = re.search(r'(\d+)M', time_str)
                    hours = int(hours_match.group(1)) if hours_match else 0
                    minutes = int(minutes_match.group(1)) if minutes_match else 0
                    return hours * 60 + minutes
                elif 'H' in time_str:
                    hours_match = re.search(r'(\d+)H', time_str)
                    hours = int(hours_match.group(1)) if hours_match else 0
                    return hours * 60
                elif 'M' in time_str:
                    minutes_match = re.search(r'(\d+)M', time_str)
                    minutes = int(minutes_match.group(1)) if minutes_match else 30
                    return minutes
            else:
                numbers = re.findall(r'\d+', time_str)
                if numbers:
                    return int(numbers[0])
        except:
            pass
        
        return 30

    def safe_float(self, val):
        """Safely convert to float"""
        try:
            if not val or val == 'nan' or val == '':
                return None
            return float(val)
        except:
            return None

    def safe_int(self, val):
        """Safely convert to int"""
        try:
            if not val or val == 'nan' or val == '':
                return None
            return int(float(val))
        except:
            return None

    def get_first_image(self, images_str):
        """Extract the first image URL"""
        images = self.parse_r_list(images_str)
        if images and len(images) > 0:
            url = images[0].strip()
            if url.startswith('http'):
                return url
        
        return "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800&h=600&fit=crop&q=food"

    def process_recipe_row(self, row, index):
        """Process a single recipe row"""
        try:
            # Parse ingredients
            ingredients_parts = self.parse_r_list(row.get('RecipeIngredientParts', ''))
            ingredients_quantities = self.parse_r_list(row.get('RecipeIngredientQuantities', ''))
            instructions = self.parse_r_list(row.get('RecipeInstructions', ''))
            
            if not ingredients_parts:
                return None
            
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
            
            # Get image
            image_url = self.get_first_image(row.get('Images', ''))
            
            # Extract cook time
            total_time = self.extract_time_minutes(row.get('TotalTime'))
            cook_time = self.extract_time_minutes(row.get('CookTime'))
            final_cook_time = cook_time if cook_time != 30 else total_time
            
            # Determine difficulty
            difficulty = "Easy"
            if final_cook_time > 60 or len(instructions) > 8:
                difficulty = "Hard"
            elif final_cook_time > 30 or len(instructions) > 5:
                difficulty = "Medium"
            
            # Clean instructions
            instructions = [inst.strip() for inst in instructions if inst and inst.strip()]
            
            recipe = {
                'id': str(row.get('RecipeId', index)),
                'title': str(row.get('Name', 'Untitled Recipe')),
                'description': str(row.get('Description', 'Delicious recipe')),
                'image': image_url,
                'cookTime': final_cook_time,
                'servings': self.safe_int(row.get('RecipeServings')) or 4,
                'rating': self.safe_float(row.get('AggregatedRating')) or round(4.2 + (index % 7) * 0.1, 1),
                'category': str(row.get('RecipeCategory', 'General')),
                'difficulty': difficulty,
                'ingredients': ingredients,
                'instructions': instructions,
                'nutrition': {
                    'calories': self.safe_float(row.get('Calories')),
                    'protein': self.safe_float(row.get('ProteinContent')),
                    'fat': self.safe_float(row.get('FatContent')),
                    'carbs': self.safe_float(row.get('CarbohydrateContent'))
                }
            }
            
            return recipe
        except Exception as e:
            logger.error(f"Error processing recipe row: {e}")
            return None
    
    def search_recipes(self, search_ingredients, top_n=6):
        """Search recipes using simple ingredient matching"""
        if not search_ingredients:
            return []
        
        try:
            logger.info(f"🔍 Searching for: {search_ingredients}")
            
            # Find recipes that match ingredients
            recipe_scores = defaultdict(float)
            
            for ingredient in search_ingredients:
                ingredient_words = self.extract_ingredient_words(ingredient)
                
                for word in ingredient_words:
                    word_lower = word.lower()
                    if word_lower in self.ingredient_index:
                        for recipe_idx in self.ingredient_index[word_lower]:
                            recipe_scores[recipe_idx] += 1.0 / len(ingredient_words)
            
            # Sort by score
            sorted_recipes = sorted(recipe_scores.items(), key=lambda x: x[1], reverse=True)
            
            results = []
            for recipe_idx, score in sorted_recipes[:top_n]:
                if score > 0:
                    recipe = self.recipes[recipe_idx].copy()
                    recipe['similarityScore'] = min(score, 1.0)  # Cap at 1.0
                    results.append(recipe)
            
            logger.info(f"✅ Found {len(results)} matching recipes")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error in search: {e}")
            return []
    
    def get_random_recipes(self, count=6):
        """Get random recipes"""
        if not self.recipes:
            return []
        
        import random
        count = min(count, len(self.recipes), 50)
        return random.sample(self.recipes, count)
    
    def get_recipes_by_category(self, category, limit=20):
        """Get recipes by category"""
        try:
            filtered = [r for r in self.recipes if category.lower() in r['category'].lower()]
            
            import random
            if len(filtered) > limit:
                filtered = random.sample(filtered, limit)
            
            return filtered
        except Exception as e:
            logger.error(f"Error getting recipes by category: {e}")
            return []
    
    def get_recipe_by_id(self, recipe_id):
        """Get recipe by ID"""
        try:
            for recipe in self.recipes:
                if recipe['id'] == str(recipe_id):
                    return recipe
            return None
        except Exception as e:
            logger.error(f"Error getting recipe by ID: {e}")
            return None

