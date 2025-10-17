import csv
import json
import re
import os
import logging
from collections import defaultdict, Counter
import math
import random
import io

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleRecipeEngine:
    def __init__(self, data_file_path):
        self.data_file_path = data_file_path
        self.recipes = []
        self.categories = []
        self.ingredient_index = defaultdict(set)  # ingredient -> set of recipe indices

    # -----------------------------
    # Parsing helpers (NEW/UPDATED)
    # -----------------------------
    @staticmethod
    def _looks_like_r_vector(s: str) -> bool:
        return bool(re.match(r'^\s*c\s*\(', str(s), flags=re.IGNORECASE | re.DOTALL))

    @staticmethod
    def _is_noise_token(text: str) -> bool:
        """
        True if token is empty after stripping or consists only of quotes/brackets/punctuation.
        Prevents stray steps like `"`, `)`, `,`, etc.
        """
        if text is None:
            return True
        t = str(text).strip()
        if not t:
            return True
        # Remove leading/trailing punctuation and test if anything meaningful remains
        core = re.sub(r'^[\s"\'`,.;:(){}\[\]-]+|[\s"\'`,.;:(){}\[\]-]+$', '', t)
        core = re.sub(r'[\s"\'`,.;:(){}\[\]-]+', '', core)
        return len(core) == 0

    @staticmethod
    def _strip_dangling_wrappers(text: str) -> str:
        """
        Trim surrounding quotes/parens if they’re unbalanced or dangling.
        e.g., '"Step 9' -> 'Step 9', 'Step 10)' -> 'Step 10'
        Balanced parentheses like 'serve warm (optional)' are preserved.
        """
        if text is None:
            return ""
        t = str(text).strip()

        # Remove a single leading or trailing quote if it’s not paired
        if t.count('"') % 2 == 1:
            t = t.strip('"')
        if t.count("'") % 2 == 1:
            t = t.strip("'")

        # Remove a trailing unmatched right paren
        if t.endswith(')') and not t.startswith('('):
            # Only strip if parens are unbalanced
            if t.count(')') > t.count('('):
                t = t[:-1].rstrip()

        # Remove a leading unmatched left paren
        if t.startswith('(') and not t.endswith(')'):
            if t.count('(') > t.count(')'):
                t = t[1:].lstrip()

        return t.strip()

    @staticmethod
    def _clean_step_text(text: str) -> str:
        """Remove stray index lines and leading numbering; normalize spaces."""
        if text is None:
            return ""
        t = str(text)

        # Drop lines that are only numbers like "2" / "3." / "4)"
        lines = re.split(r'[\r\n]+', t)
        lines = [ln for ln in lines if not re.fullmatch(r'\s*\d+[.)]?\s*', ln or "")]
        t = " ".join(lines)

        # Remove leading numbering like "6. ", "6) ", "- ", "• "
        t = re.sub(r'^\s*(?:\d+[.)]?|[-•])\s+', '', t)

        # Normalize spaces
        t = re.sub(r'\s+', ' ', t).strip()

        # Strip any dangling quotes/parens
        t = SimpleRecipeEngine._strip_dangling_wrappers(t)

        return t

    def parse_r_list(self, r_string):
        """
        Parse R c(\"...\") lists or split plain text; remove index artifacts and punctuation-only tokens.
        Fixes issues like stray `"` or `)` becoming their own steps.
        """
        if not r_string or str(r_string).strip().lower() == 'nan':
            return []

        s = str(r_string).strip()

        def finalize(items):
            out = []
            for tok in items:
                tok = self._clean_step_text(tok)
                if not self._is_noise_token(tok):
                    out.append(tok)
            return out

        # Path 1: R-style vector like c("...", "...")
        if self._looks_like_r_vector(s):
            # Extract content between FIRST '(' and LAST ')'
            try:
                first_paren = s.index('(')
                last_paren = s.rindex(')')
                content = s[first_paren + 1:last_paren].strip()
            except ValueError:
                content = s

            # CSV reader to respect quoted commas
            try:
                rdr = csv.reader(io.StringIO(content), delimiter=',', quotechar='"', skipinitialspace=True)
                row = next(rdr, [])
            except Exception:
                row = []

            # If the row collapsed due to newlines, try again with newlines replaced by spaces
            if len(row) <= 1 and ',' in content:
                rdr = csv.reader(io.StringIO(content.replace('\n', ' ')), delimiter=',', quotechar='"', skipinitialspace=True)
                row = next(rdr, [])

            # Clean + drop noise/NA/empty
            items = []
            for tok in row:
                t = (tok or "").strip()
                if t.upper() == "NA":
                    continue
                items.append(t)

            return finalize(items)

        # Path 2: Plain text — split into sentences, then clean + drop noise
        parts = re.findall(r'[^.?!;\n]+(?:[.?!;]|$)', s)
        return finalize(parts)

    # -----------------------------
    # Existing utilities
    # -----------------------------
    def clean_text(self, text):
        """Clean and normalize text"""
        if not text:
            return ""
        text = str(text).strip()
        text = re.sub(r'\s+', ' ', text)
        return text

    def extract_ingredient_words(self, ingredient):
        """Extract meaningful words from ingredient text"""
        if not ingredient:
            return []
        ingredient = re.sub(r'[^\w\s]', ' ', ingredient.lower())
        stop_words = {
            'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'cup', 'cups', 'tablespoon', 'tablespoons', 'teaspoon', 'teaspoons',
            'pound', 'pounds', 'ounce', 'ounces', 'gram', 'grams', 'liter', 'liters',
            'ml', 'kg', 'lb', 'oz', 'tsp', 'tbsp'
        }
        words = [
            word.strip() for word in ingredient.split()
            if word.strip() and len(word.strip()) > 2 and word.strip() not in stop_words
        ]
        return words

    def load_recipes(self):
        """Load recipes from CSV file"""
        try:
            logger.info(f"📂 Loading recipes from: {self.data_file_path}")

            if not os.path.exists(self.data_file_path):
                logger.error(f"❌ Dataset file not found: {self.data_file_path}")
                return False

            recipes_loaded = 0
            categories_set = set()

            with open(self.data_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)

                for idx, row in enumerate(reader):
                    try:
                        recipe = self.process_recipe_row(row, idx)
                        if recipe:
                            self.recipes.append(recipe)
                            categories_set.add(recipe["category"])

                            # Index ingredients for search
                            for ingredient in recipe.get("ingredients", []):
                                words = self.extract_ingredient_words(ingredient)
                                for word in words:
                                    self.ingredient_index[word.lower()].add(len(self.recipes) - 1)
                            recipes_loaded += 1

                        # Limit for deployment
                        if recipes_loaded >= 10000:
                            break

                    except Exception as e:
                        logger.warning(f"Error processing recipe {idx}: {e}")
                        continue

            self.categories = sorted(list(categories_set))

            logger.info(f"✅ Loaded {recipes_loaded} recipes successfully")
            logger.info(f"📊 Found {len(self.categories)} categories")
            logger.info(f"🔍 Indexed {len(self.ingredient_index)} unique ingredients")

            return recipes_loaded > 0

        except Exception as e:
            logger.error(f"❌ Error loading recipes: {e}")
            return False

    def safe_int(self, value, default=0):
        """Safely convert value to int"""
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default

    def safe_float(self, value, default=0.0):
        """Safely convert value to float"""
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def get_difficulty(self, cook_time):
        """Determine difficulty based on cook time"""
        if cook_time <= 15:
            return "Easy"
        elif cook_time <= 45:
            return "Medium"
        else:
            return "Hard"

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
                            # Weight each word equally within the ingredient string
                            recipe_scores[recipe_idx] += 1.0 / max(len(ingredient_words), 1)

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
        count = min(count, len(self.recipes), 50)
        return random.sample(self.recipes, count)

    def get_recipes_by_category(self, category, limit=20):
        """Get recipes by category"""
        try:
            filtered = [r for r in self.recipes if category.lower() in r['category'].lower()]
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

    def process_recipe_row(self, row, index):
        """Process a single recipe row"""
        try:
            # Parse ingredients
            ingredients_parts = self.parse_r_list(row.get("RecipeIngredientParts", ""))
            ingredients_quantities = self.parse_r_list(row.get("RecipeIngredientQuantities", ""))
            instructions = self.parse_r_list(row.get("RecipeInstructions", ""))

            if not ingredients_parts or not instructions:
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
            image_url = (row.get("Images") or "").strip() or "https://via.placeholder.com/400x300/f0f0f0/666?text=Recipe"

            # Extract cook time
            total_time = self.safe_int(row.get("TotalTime"), 30)
            cook_time = self.safe_int(row.get("CookTime"), 30)
            final_cook_time = cook_time if cook_time != 30 else total_time

            # Determine difficulty
            difficulty = self.get_difficulty(final_cook_time)

            recipe = {
                "id": str(row.get("RecipeId", index)),
                "title": self.clean_text(row.get("Name", f"Recipe {index}")),
                "description": self.clean_text(row.get("Description", "Delicious recipe")),
                "image": image_url,
                "cookTime": final_cook_time,
                "servings": self.safe_int(row.get("RecipeServings")) or 4,
                "rating": self.safe_float(row.get("AggregatedRating")) or round(4.2 + (index % 7) * 0.1, 1),
                "category": self.clean_text(row.get("RecipeCategory", "General")),
                "difficulty": difficulty,
                "ingredients": ingredients,
                "instructions": instructions,
                "nutrition": {
                    "calories": self.safe_int(row.get("Calories", 0)),
                    "protein": self.safe_float(row.get("ProteinContent", 0)),
                    "fat": self.safe_float(row.get("FatContent", 0)),
                    "carbs": self.safe_float(row.get("CarbohydrateContent", 0))
                }
            }

            return recipe
        except Exception as e:
            logger.error(f"Error processing recipe row {index}: {e}")
            return None
