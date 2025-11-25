import csv
import json
import re
import os
import logging
from collections import defaultdict, Counter
import math
import random
import io
from datasets import load_dataset
import threading  # ✅ NEW

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("simple_recipe_engine")

class SimpleRecipeEngine:
    def __init__(self, data_source, initial_limit=1500, background_load=True):
        """
        initial_limit: how many recipes to load synchronously at startup.
        background_load: if True, load the rest of the dataset in a background thread.
        """
        # data_source can be a file path (for local CSV) or a dataset name (for HF)
        self.data_source = data_source
        self.recipes = []
        self.categories = []
        self.ingredient_index = defaultdict(set)  # ingredient -> set of recipe indices

        # NEW: background loading controls
        self.initial_limit = initial_limit
        self.background_load = background_load
        self._background_started = False
        self.fully_loaded = False

        # NEW: track IDs we've already added so we can safely re-scan the dataset
        self._seen_ids = set()

        self.is_hf_dataset = (
            isinstance(data_source, str)
            and '/' in data_source
            and not os.path.exists(data_source)
        )
        if self.is_hf_dataset:
            logger.info(f"💡 Data source detected as Hugging Face dataset: {self.data_source}")
        else:
            logger.info(f"💡 Data source detected as local file: {self.data_source}")

    # -----------------------------
    # Core detectors / cleaners
    # -----------------------------
    @staticmethod
    def _looks_like_r_vector(s: str) -> bool:
        return bool(re.match(r'^\s*c\s*\(', str(s), flags=re.IGNORECASE | re.DOTALL))

    @staticmethod
    def _is_noise_token(text: str) -> bool:
        if text is None:
            return True
        t = str(text).strip()
        if not t:
            return True
        core = re.sub(r'^[\s"\'`,.;:(){}\[\]-]+|[\s"\'`,.;:(){}\[\]-]+$', '', t)
        core = re.sub(r'[\s"\'`,.;:(){}\[\]-]+', '', core)
        return len(core) == 0

    @staticmethod
    def _strip_dangling_wrappers(text: str) -> str:
        if text is None:
            return ""
        t = str(text).strip()
        if t.count('"') % 2 == 1:
            t = t.strip('"')
        if t.count("'") % 2 == 1:
            t = t.strip("'")
        # Only strip clearly unmatched parens
        if t.endswith(')') and t.count(')') > t.count('('):
            t = t[:-1].rstrip()
        if t.startswith('(') and t.count('(') > t.count(')'):
            t = t[1:].lstrip()
        return t.strip()

    @staticmethod
    def _clean_step_text(text: str) -> str:
        # (Used for instructions; unchanged behavior you liked)
        if text is None:
            return ""
        t = str(text)
        lines = re.split(r'[\r\n]+', t)
        lines = [ln for ln in lines if not re.fullmatch(r'\s*\d+[.)]?\s*', ln or "")]
        t = " ".join(lines)
        t = re.sub(r'^\s*(?:\d+[.)]?|[-•])\s+', '', t)
        t = re.sub(r'\s+', ' ', t).strip()
        t = SimpleRecipeEngine._strip_dangling_wrappers(t)
        return t

    # -----------------------------
    # Instructions parser (UNCHANGED)
    # -----------------------------
    def parse_r_list(self, r_string):
        """
        Parse R c(\"...\") lists or split plain text for INSTRUCTIONS.
        This is the exact behavior you approved—do not change.
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

        if self._looks_like_r_vector(s):
            try:
                first_paren = s.index('(')
                last_paren = s.rindex(')')
                content = s[first_paren + 1:last_paren].strip()
            except ValueError:
                content = s
            try:
                rdr = csv.reader(io.StringIO(content), delimiter=',', quotechar='"', skipinitialspace=True)
                row = next(rdr, [])
            except Exception:
                row = []
            if len(row) <= 1 and ',' in content:
                rdr = csv.reader(io.StringIO(content.replace('\n', ' ')), delimiter=',', quotechar='"', skipinitialspace=True)
                row = next(rdr, [])
            items = []
            for tok in row:
                t = (tok or "").strip()
                if t.upper() == "NA":
                    continue
                items.append(t)
            return finalize(items)

        parts = re.findall(r'[^.?!;\n]+(?:[.?!;]|$)', s)
        return finalize(parts)

    # -----------------------------
    # NEW: Robust R-vector extractor for INGREDIENTS/QUANTITIES
    # -----------------------------
    @staticmethod
    def _parse_r_vector_keep_placeholders(s: str):
        """
        Extract ALL quoted elements from c("a","b",...),
        preserving position (NA -> ""), tolerating newlines/commas.
        """
        if not s:
            return []
        txt = str(s).strip()
        if not SimpleRecipeEngine._looks_like_r_vector(txt):
            # Not an R vector; return a conservative single-token list
            return [txt] if txt else []

        # Grab content inside the outermost parens
        try:
            first_paren = txt.index('(')
            last_paren = txt.rindex(')')
            content = txt[first_paren + 1:last_paren]
        except ValueError:
            content = txt

        matches = re.findall(r'"([^"]*)"', content, flags=re.DOTALL)

        out = []
        for m in matches:
            t = (m or "").strip()
            if t.upper() == "NA":
                t = ""  # placeholder to keep alignment
            out.append(t)
        return out

    # -----------------------------
    # Ingredient pairing (PADDING, not truncating)
    # -----------------------------
    def _pair_quantities_ingredients(self, quantities, ingredients, row_idx=None, recipe_name=None):
        """
        Align to the LONGER list and pad the shorter with "" so every ingredient gets a quantity slot and vice versa.
        """
        q = list(quantities or [])
        ing = list(ingredients or [])

        if len(q) != len(ing):
            id_info = f"(row {row_idx})" if row_idx is not None else ""
            name_info = f' name="{recipe_name}"' if recipe_name else ""
            logger.info(
                f"ℹ️ Aligning quantities and ingredients by padding {id_info}{name_info}: "
                f"quantities={len(q)}, ingredients={len(ing)} -> aligned={max(len(q), len(ing))}"
            )

        n = max(len(q), len(ing))
        if len(q) < n:
            q.extend([""] * (n - len(q)))
        if len(ing) < n:
            ing.extend([""] * (n - len(ing)))

        paired = []
        for i in range(n):
            qty = q[i].strip() if isinstance(q[i], str) else str(q[i] or "").strip()
            item = ing[i].strip() if isinstance(ing[i], str) else str(ing[i] or "").strip()
            combined = f"{qty} {item}".strip() if qty else item
            if combined:
                paired.append(combined)

        return paired

    # -----------------------------
    # Text utilities
    # -----------------------------
    def clean_text(self, text):
        if not text:
            return ""
        text = str(text).strip()
        text = re.sub(r'\s+', ' ', text)
        return text

    def extract_ingredient_words(self, ingredient):
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
            w for w in (ingredient.split()) if w and len(w) > 2 and w not in stop_words
        ]
        return words

    # -----------------------------
    # SOURCE ITERATOR HELPER
    # -----------------------------
    def _iter_source_rows(self):
        """
        Unified iterator over rows from HF or local CSV.
        Yields (idx, row_dict).
        """
        if self.is_hf_dataset:
            logger.info(f"📂 Streaming recipes from Hugging Face dataset: {self.data_source}")
            dataset = load_dataset(self.data_source, split='train', streaming=True)
            for idx, row in enumerate(dataset):
                yield idx, row
        else:
            logger.info(f"📂 Loading recipes from local file: {self.data_source}")
            if not os.path.exists(self.data_source):
                logger.error(f"❌ Dataset file not found: {self.data_source}")
                return
            with open(self.data_source, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader):
                    yield idx, row

    # -----------------------------
    # BACKGROUND LOAD
    # -----------------------------
    def _background_load_remaining(self):
        """
        Re-scan the dataset in a background thread and add any recipes
        whose IDs we haven't seen yet.
        """
        try:
            logger.info("🚀 Background loading of remaining recipes started")
            categories_set = set(self.categories)

            for idx, row in self._iter_source_rows():
                try:
                    recipe = self.process_recipe_row(row, idx)
                    if not recipe:
                        continue

                    rid = recipe["id"]
                    if rid in self._seen_ids:
                        # Already loaded in initial batch
                        continue

                    # Mark as seen and add
                    self._seen_ids.add(rid)
                    self.recipes.append(recipe)
                    categories_set.add(recipe["category"])

                    # Index ingredients for search
                    for ingredient in recipe.get("ingredients", []):
                        for word in self.extract_ingredient_words(ingredient):
                            self.ingredient_index[word.lower()].add(len(self.recipes) - 1)

                except Exception as e:
                    logger.warning(f"Error processing recipe (background) {idx}: {e}")

            self.categories = sorted(list(categories_set))
            self.fully_loaded = True
            logger.info(f"✅ Background loading complete; total recipes = {len(self.recipes)}")
            logger.info(f"📊 Final category count: {len(self.categories)}")
            logger.info(f"🔍 Final ingredient index size: {len(self.ingredient_index)}")

        except Exception as e:
            logger.error(f"❌ Background loading failed: {e}")

    # -----------------------------
    # Load / search
    # -----------------------------
    def load_recipes(self):
        """
        Load recipes. If background_load is True, only a subset (initial_limit)
        is loaded synchronously, then the rest is loaded in the background.
        """
        try:
            recipes_loaded_now = 0
            categories_set = set(self.categories)

            for idx, row in self._iter_source_rows():
                try:
                    recipe = self.process_recipe_row(row, idx)
                    if not recipe:
                        continue

                    rid = recipe["id"]
                    if rid in self._seen_ids:
                        continue

                    # Add to in-memory structures
                    self._seen_ids.add(rid)
                    self.recipes.append(recipe)
                    categories_set.add(recipe["category"])

                    for ingredient in recipe.get("ingredients", []):
                        for word in self.extract_ingredient_words(ingredient):
                            self.ingredient_index[word.lower()].add(len(self.recipes) - 1)

                    recipes_loaded_now += 1

                    # If we only want a fast initial batch, stop here and spawn background loader
                    if (
                        self.background_load
                        and not self._background_started
                        and recipes_loaded_now >= self.initial_limit
                    ):
                        self.categories = sorted(list(categories_set))
                        self._background_started = True

                        logger.info(
                            f"⏸ Initial load reached {recipes_loaded_now} recipes; "
                            f"starting background loader for the rest."
                        )

                        # Start background thread
                        t = threading.Thread(
                            target=self._background_load_remaining,
                            daemon=True
                        )
                        t.start()

                        break  # stop initial, return control to caller

                except Exception as e:
                    logger.warning(f"Error processing recipe {idx}: {e}")

            else:
                # If we never hit the break, we finished the whole dataset synchronously
                self.categories = sorted(list(categories_set))
                self.fully_loaded = True
                logger.info(f"✅ Loaded all recipes synchronously; total={len(self.recipes)}")
                logger.info(f"📊 Found {len(self.categories)} categories")
                logger.info(f"🔍 Indexed {len(self.ingredient_index)} unique ingredients")

            return len(self.recipes) > 0

        except Exception as e:
            logger.error(f"❌ Error loading recipes: {e}")
            return False

    # -----------------------------
    # Safe parsers
    # -----------------------------
    def safe_int(self, value, default=0):
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default

    def safe_float(self, value, default=0.0):
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    # -----------------------------
    # Convenience
    # -----------------------------
    def get_difficulty(self, cook_time):
        if cook_time <= 15:
            return "Easy"
        elif cook_time <= 45:
            return "Medium"
        else:
            return "Hard"

    def search_recipes(self, search_ingredients, top_n=6):
        if not search_ingredients:
            return []
        try:
            logger.info(f"🔍 Searching for: {search_ingredients}")
            recipe_scores = defaultdict(float)
            for ingredient in search_ingredients:
                for word in self.extract_ingredient_words(ingredient):
                    if word in self.ingredient_index:
                        for recipe_idx in self.ingredient_index[word]:
                            recipe_scores[recipe_idx] += 1.0 / max(len(self.extract_ingredient_words(ingredient)), 1)
            sorted_recipes = sorted(recipe_scores.items(), key=lambda x: x[1], reverse=True)
            results = []
            for recipe_idx, score in sorted_recipes[:top_n]:
                if score > 0:
                    recipe = self.recipes[recipe_idx].copy()
                    recipe['similarityScore'] = min(score, 1.0)
                    results.append(recipe)
            logger.info(f"✅ Found {len(results)} matching recipes")
            return results
        except Exception as e:
            logger.error(f"❌ Error in search: {e}")
            return []

    def get_random_recipes(self, count=6):
        if not self.recipes:
            return []
        count = min(count, len(self.recipes), 50)
        return random.sample(self.recipes, count)

    def get_recipes_by_category(self, category, limit=20):
        try:
            filtered = [r for r in self.recipes if category.lower() in r['category'].lower()]
            if len(filtered) > limit:
                filtered = random.sample(filtered, limit)
            return filtered
        except Exception as e:
            logger.error(f"Error getting recipes by category: {e}")
            return []

    def get_recipe_by_id(self, recipe_id):
        try:
            for recipe in self.recipes:
                if recipe['id'] == str(recipe_id):
                    return recipe
            return None
        except Exception as e:
            logger.error(f"Error getting recipe by ID: {e}")
            return None

    # -----------------------------
    # Row processing
    # -----------------------------
    def process_recipe_row(self, row, index):
        """
        Process a single recipe row.
        - INSTRUCTIONS parsing remains as-is (your approved logic).
        - INGREDIENTS/QUANTITIES now use a strict R-vector extractor + padding alignment.
        """
        try:
            # Raw fields
            ing_parts_raw = row.get("RecipeIngredientParts", "")
            ing_quants_raw = row.get("RecipeIngredientQuantities", "")
            instructions_raw = row.get("RecipeInstructions", "")

            # Parse with robust vector extractor for ingredients/quantities
            ing_parts = self._parse_r_vector_keep_placeholders(ing_parts_raw)
            ing_quants = self._parse_r_vector_keep_placeholders(ing_quants_raw)

            # Keep your exact instruction parsing
            instructions = self.parse_r_list(instructions_raw)

            if not ing_parts or not instructions:
                return None  # need ingredients and instructions at minimum

            # Align (pad shorter side) so every ingredient has a quantity slot
            ingredients = self._pair_quantities_ingredients(
                ing_quants, ing_parts, row_idx=index, recipe_name=row.get("Name")
            )

            if not ingredients:
                return None

            # Image
            image_list = self._parse_r_vector_keep_placeholders(row.get("Images", ""))
            image_url = image_list[0] if image_list else "https://via.placeholder.com/400x300/f0f0f0/666?text=Recipe"

            # Times / difficulty
            total_time = self.safe_int(row.get("TotalTime"), 30)
            cook_time = self.safe_int(row.get("CookTime"), 30)
            final_cook_time = cook_time if cook_time != 30 else total_time
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
