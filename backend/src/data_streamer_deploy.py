import pandas as pd
import numpy as np
import re
import json
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecipeDataStreamerDeploy:
    def __init__(self, data_file_path):
        self.data_file_path = data_file_path
        self.recipes_df = None
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None
        self.categories = []
        self.chunk_size = 5000  # Smaller chunks for deployment
        self.max_recipes = 10000  # Use 10K recipes for deployment
        
    def parse_r_list(self, r_string):
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
            logger.warning(f"Error parsing R list '{r_string[:100]}...': {e}")
            return []

    def load_dataset_for_deployment(self):
        """Load a substantial portion of the dataset optimized for deployment"""
        logger.info("🚀 Starting to load dataset for deployment...")
        
        if not os.path.exists(self.data_file_path):
            logger.error(f"❌ Dataset file not found: {self.data_file_path}")
            return False
        
        try:
            # Read the dataset in chunks to manage memory
            logger.info("📊 Reading dataset in chunks...")
            
            chunk_list = []
            total_loaded = 0
            
            for chunk in pd.read_csv(self.data_file_path, chunksize=self.chunk_size):
                # Filter out recipes with missing essential data
                chunk = chunk.dropna(subset=['Name', 'RecipeIngredientParts'])
                
                if len(chunk) > 0:
                    chunk_list.append(chunk)
                    total_loaded += len(chunk)
                    
                    logger.info(f"📊 Loaded {total_loaded} recipes so far...")
                    
                    # Stop when we reach our target
                    if total_loaded >= self.max_recipes:
                        break
            
            # Combine all chunks
            self.recipes_df = pd.concat(chunk_list, ignore_index=True)
            
            # Limit to max_recipes
            if len(self.recipes_df) > self.max_recipes:
                self.recipes_df = self.recipes_df.head(self.max_recipes)
            
            final_count = len(self.recipes_df)
            logger.info(f"📊 Final dataset: {final_count} recipes loaded for deployment")
            
            # Extract categories
            self.categories = list(self.recipes_df['RecipeCategory'].dropna().unique())
            self.categories = [cat for cat in self.categories if cat and str(cat).strip() and str(cat) != 'nan']
            
            logger.info(f"📊 Found {len(self.categories)} unique categories")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading dataset: {e}")
            return False
    
    def prepare_ml_data(self):
        """Prepare ML data by processing ingredients efficiently"""
        logger.info("🤖 Preparing ML data for deployment...")
        
        if self.recipes_df is None:
            logger.error("❌ Dataset not loaded")
            return False
        
        try:
            # Process ingredients efficiently
            ingredients_text = []
            valid_indices = []
            
            total_recipes = len(self.recipes_df)
            logger.info(f"🔄 Processing {total_recipes} recipes for ML...")
            
            for idx, (_, row) in enumerate(self.recipes_df.iterrows()):
                if idx % 5000 == 0:
                    logger.info(f"🔄 Processed {idx}/{total_recipes} recipes...")
                
                try:
                    ingredients = self.parse_r_list(row.get('RecipeIngredientParts', ''))
                    if ingredients:
                        # Clean and join ingredients
                        clean_ingredients = [ing.lower().strip() for ing in ingredients if ing and ing.strip()]
                        if clean_ingredients:
                            ingredients_text.append(' '.join(clean_ingredients))
                            valid_indices.append(idx)
                except Exception as e:
                    logger.warning(f"Error processing recipe {row.get('RecipeId', 'unknown')}: {e}")
            
            # Filter dataframe to only include recipes with valid ingredients
            self.recipes_df = self.recipes_df.iloc[valid_indices].reset_index(drop=True)
            
            logger.info(f"✅ Processed {len(ingredients_text)} recipes with valid ingredients")
            
            # Create TF-IDF vectorizer with deployment-optimized parameters
            logger.info("🤖 Creating TF-IDF vectors for deployment...")
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=3000,  # Optimized for deployment
                stop_words='english',
                ngram_range=(1, 2),
                min_df=2,
                max_df=0.8,
                lowercase=True,
                token_pattern=r'\b[a-zA-Z][a-zA-Z]+\b'
            )
            
            self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(ingredients_text)
            
            logger.info(f"✅ Created TF-IDF matrix with shape {self.tfidf_matrix.shape}")
            
            # Test the ML functionality
            logger.info("🧪 Testing ML functionality...")
            test_results = self.search_recipes(['chicken'], top_n=3)
            if test_results:
                logger.info(f"✅ ML test successful - found {len(test_results)} results")
                for i, recipe in enumerate(test_results):
                    logger.info(f"  {i+1}. {recipe['title']} (similarity: {recipe.get('similarityScore', 'N/A'):.3f})")
            else:
                logger.warning("⚠️ ML test returned no results")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error preparing ML data: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def search_recipes(self, search_ingredients, top_n=6):
        """Search recipes using ML"""
        if not search_ingredients or self.tfidf_vectorizer is None or self.recipes_df is None:
            logger.warning("❌ ML search: Missing data or vectorizer")
            return []
        
        try:
            # Clean and prepare query
            clean_ingredients = [ing.lower().strip() for ing in search_ingredients if ing and ing.strip()]
            if not clean_ingredients:
                return []
            
            query_text = ' '.join(clean_ingredients)
            logger.info(f"🔍 Searching for: {query_text}")
            
            # Create query vector
            query_vector = self.tfidf_vectorizer.transform([query_text])
            
            # Calculate similarities
            similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()
            
            # Get top matches
            top_indices = similarities.argsort()[-top_n*2:][::-1]  # Get more candidates
            
            results = []
            for idx in top_indices:
                if len(results) >= top_n:
                    break
                    
                if similarities[idx] > 0.001:  # Very low threshold for better recall
                    try:
                        row = self.recipes_df.iloc[idx]
                        recipe = self.format_recipe_for_frontend(row)
                        if recipe and recipe.get('ingredients'):  # Only include recipes with ingredients
                            recipe['similarityScore'] = float(similarities[idx])
                            results.append(recipe)
                    except Exception as e:
                        logger.warning(f"Error formatting recipe at index {idx}: {e}")
                        continue
            
            logger.info(f"✅ Found {len(results)} matching recipes")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error in ML search: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def extract_time_minutes(self, time_str):
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
            logger.warning(f"Error parsing time '{time_str}': {e}")
        
        return 30

    def safe_float(self, val):
        """Safely convert to float"""
        try:
            if pd.isna(val) or val == '' or val is None:
                return None
            return float(val)
        except:
            return None

    def safe_int(self, val):
        """Safely convert to int"""
        try:
            if pd.isna(val) or val == '' or val is None:
                return None
            return int(float(val))
        except:
            return None

    def get_first_image(self, images_str):
        """Extract the first image URL from the images string"""
        images = self.parse_r_list(images_str)
        if images and len(images) > 0:
            # Clean the URL - remove any extra characters
            url = images[0].strip()
            # Validate it's a proper URL
            if url.startswith('http'):
                return url
        
        # Fallback to a food-related placeholder
        return "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800&h=600&fit=crop&q=food"

    def format_recipe_for_frontend(self, row):
        """Convert a recipe row to frontend format"""
        try:
            # Parse ingredients
            ingredients_parts = self.parse_r_list(row.get('RecipeIngredientParts', ''))
            ingredients_quantities = self.parse_r_list(row.get('RecipeIngredientQuantities', ''))
            instructions = self.parse_r_list(row.get('RecipeInstructions', ''))
            
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
            image_url = self.get_first_image(row.get('Images', ''))
            
            # Extract cook time
            total_time = self.extract_time_minutes(row.get('TotalTime'))
            cook_time = self.extract_time_minutes(row.get('CookTime'))
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
                'servings': self.safe_int(row.get('RecipeServings')) or 4,
                'rating': self.safe_float(row.get('AggregatedRating')) or round(np.random.uniform(4.2, 4.9), 1),
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
            logger.error(f"Error formatting recipe {row.get('RecipeId', 'unknown')}: {e}")
            return None
    
    def get_random_recipes(self, count=6):
        """Get random recipes"""
        if self.recipes_df is None or len(self.recipes_df) == 0:
            return []
        
        count = min(count, len(self.recipes_df), 50)  # Limit to 50 max
        random_recipes_data = self.recipes_df.sample(n=count)
        recipes = []
        
        for _, row in random_recipes_data.iterrows():
            recipe = self.format_recipe_for_frontend(row)
            if recipe:
                recipes.append(recipe)
        
        return recipes
    
    def get_recipes_by_category(self, category, limit=20):
        """Get recipes by category"""
        if self.recipes_df is None:
            return []
        
        try:
            filtered_recipes = self.recipes_df[self.recipes_df['RecipeCategory'].str.contains(category, case=False, na=False)]
            
            # Limit results for performance
            sample_size = min(limit, len(filtered_recipes))
            if len(filtered_recipes) > sample_size:
                filtered_recipes = filtered_recipes.sample(n=sample_size)
            
            recipes = []
            for _, row in filtered_recipes.iterrows():
                recipe = self.format_recipe_for_frontend(row)
                if recipe:
                    recipes.append(recipe)
            
            return recipes
        except Exception as e:
            logger.error(f"Error getting recipes by category {category}: {e}")
            return []
    
    def get_recipe_by_id(self, recipe_id):
        """Get a specific recipe by ID"""
        if self.recipes_df is None:
            return None
        
        try:
            recipe_data = self.recipes_df[self.recipes_df['RecipeId'] == int(recipe_id)]
            if len(recipe_data) > 0:
                recipe = self.format_recipe_for_frontend(recipe_data.iloc[0])
                return recipe
            return None
        except Exception as e:
            logger.error(f"Error getting recipe {recipe_id}: {e}")
            return None

