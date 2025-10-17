import React, { useState, useEffect, useMemo } from 'react';
import RecipeCardWithSimilarity, { Recipe } from './RecipeCardWithSimilarity';
import RecipeModal from './RecipeModal';
import SplitText from './SplitText';

interface RecipeGridWithBackendProps {
  searchQuery: string;
}

interface BackendRecipe {
  id: string;
  title: string;
  description: string;
  image: string;
  cookTime: number;
  servings: number;
  rating: number;
  category: string;
  difficulty: string;
  ingredients: string[];
  instructions: string[];
  nutrition: {
    calories?: number;
    protein?: number;
    fat?: number;
    carbs?: number;
  };
  similarityScore?: number;
}

const API_BASE_URL = window.location.origin;

const RecipeGridWithBackend: React.FC<RecipeGridWithBackendProps> = ({ searchQuery }) => {
  const [recipes, setRecipes] = useState<BackendRecipe[]>([]);
  const [categories, setCategories] = useState<string[]>(['All']);
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedRecipe, setSelectedRecipe] = useState<BackendRecipe | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  // Load categories on component mount
  useEffect(() => {
    const loadCategories = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/recipes/categories`);
        if (response.ok) {
          const categoryData = await response.json();
          setCategories(['All', ...categoryData]);
        }
      } catch (error) {
        console.error('Error loading categories:', error);
      }
    };

    loadCategories();
  }, []);

  // Load initial recipes
  useEffect(() => {
    const loadInitialRecipes = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const response = await fetch(`${API_BASE_URL}/api/recipes/random?count=50`);
        if (response.ok) {
          const recipeData = await response.json();
          setRecipes(recipeData);
        } else {
          setError('Failed to load recipes');
        }
      } catch (error) {
        console.error('Error loading recipes:', error);
        setError('Failed to load recipes');
      } finally {
        setLoading(false);
      }
    };

    loadInitialRecipes();
  }, []);

  // Handle search queries
  useEffect(() => {
    const searchRecipes = async () => {
      if (!searchQuery.trim()) {
        // If no search query, load random recipes
        setIsSearching(true);
        try {
          const response = await fetch(`${API_BASE_URL}/api/recipes/random?count=50`);
          if (response.ok) {
            const recipeData = await response.json();
            setRecipes(recipeData);
          }
        } catch (error) {
          console.error('Error loading random recipes:', error);
        } finally {
          setIsSearching(false);
        }
        return;
      }

      setIsSearching(true);
      setError(null);

      try {
        // Split search query into ingredients
        const ingredients = searchQuery.split(/[,\s]+/).filter(ing => ing.trim().length > 0);
        
        const response = await fetch(`${API_BASE_URL}/api/recipes/search`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            ingredients: ingredients,
            top_n: 12
          }),
        });

        if (response.ok) {
          const searchResults = await response.json();
          setRecipes(searchResults);
          
          if (searchResults.length === 0) {
            setError('No recipes found for your ingredients. Try different ingredients or check spelling.');
          }
        } else {
          setError('Search failed. Please try again.');
        }
      } catch (error) {
        console.error('Error searching recipes:', error);
        setError('Search failed. Please try again.');
      } finally {
        setIsSearching(false);
      }
    };

    // Debounce search
    const timeoutId = setTimeout(searchRecipes, 500);
    return () => clearTimeout(timeoutId);
  }, [searchQuery]);

  // Handle category filtering
  useEffect(() => {
    const loadRecipes = async () => {
      setLoading(true);
      setError(null);

      try {
        let response;
        
        if (selectedCategory === 'All' || !selectedCategory) {
          // Load random recipes for "All" category
          response = await fetch(`${API_BASE_URL}/api/recipes/random?count=20`);
        } else {
          // Load recipes by specific category
          response = await fetch(`${API_BASE_URL}/api/recipes/by-category/${encodeURIComponent(selectedCategory)}`);
        }
        
        if (response.ok) {
          const categoryRecipes = await response.json();
          setRecipes(categoryRecipes);
        } else {
          setError('Failed to load recipes');
        }
      } catch (error) {
        console.error('Error loading recipes:', error);
        setError('Failed to load recipes');
      } finally {
        setLoading(false);
      }
    };

    // Only load category recipes if there's no search query
    if (!searchQuery.trim()) {
      loadRecipes();
    }
  }, [selectedCategory, searchQuery]);

  const filteredRecipes = useMemo(() => {
    if (selectedCategory === 'All') {
      return recipes;
    }
    return recipes.filter(recipe => 
      recipe.category.toLowerCase().includes(selectedCategory.toLowerCase())
    );
  }, [recipes, selectedCategory]);

  const handleRecipeClick = (recipe: BackendRecipe) => {
    setSelectedRecipe(recipe);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedRecipe(null);
  };

  const convertToRecipeCardFormat = (backendRecipe: BackendRecipe): Recipe => {
    return {
      id: backendRecipe.id,
      title: backendRecipe.title,
      description: backendRecipe.description,
      image: backendRecipe.image,
      cookTime: backendRecipe.cookTime,
      servings: backendRecipe.servings,
      rating: backendRecipe.rating,
      category: backendRecipe.category,
      difficulty: backendRecipe.difficulty,
      ingredients: backendRecipe.ingredients,
      instructions: backendRecipe.instructions,
      similarityScore: backendRecipe.similarityScore
    };
  };

  const getDisplayTitle = () => {
    if (searchQuery.trim()) {
      return `Recipe Recommendations`;
    }
    if (selectedCategory !== 'All') {
      return `${selectedCategory} Recipes`;
    }
    return 'Featured Recipes';
  };

  const getDisplaySubtitle = () => {
    if (searchQuery.trim()) {
      const ingredients = searchQuery.split(/[,\s]+/).filter(ing => ing.trim().length > 0);
      return `Based on your ingredients: ${ingredients.join(', ')}`;
    }
    if (selectedCategory !== 'All') {
      return `Discover delicious ${selectedCategory.toLowerCase()} cuisine`;
    }
    return 'Discover culinary masterpieces from around the world';
  };

  return (
    <section id="recipes" className="py-20 px-6">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <SplitText
            text={getDisplayTitle()}
            tag="h2"
            className="text-4xl font-bold mb-6"
            delay={30}
            duration={0.6}
          />
          <SplitText
            text={getDisplaySubtitle()}
            tag="p"
            className="text-xl text-muted-foreground max-w-2xl mx-auto"
            delay={20}
            duration={0.5}
          />
        </div>

        <div className="flex flex-wrap justify-center gap-4 mb-12">
          {categories.map((category) => (
            <button
              key={category}
              onClick={() => setSelectedCategory(category)}
              className={`category-tag cursor-target ${
                selectedCategory === category ? 'active' : ''
              }`}
            >
              {category}
            </button>
          ))}
        </div>

        {error && (
          <div className="text-center mb-8">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 max-w-md mx-auto">
              <p className="text-red-700">{error}</p>
            </div>
          </div>
        )}

        {(loading || isSearching) && (
          <div className="text-center mb-8">
            <div className="inline-flex items-center gap-2 text-muted-foreground">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
              {isSearching ? 'Searching recipes...' : 'Loading delicious recipes...'}
            </div>
          </div>
        )}

        {!loading && !isSearching && filteredRecipes.length === 0 && !error && (
          <div className="text-center mb-8">
            <p className="text-muted-foreground">No recipes found. Try different ingredients or remove some filters.</p>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {filteredRecipes.map((recipe) => (
            <div key={recipe.id} className="animate-fade-up">
              <RecipeCardWithSimilarity 
                recipe={convertToRecipeCardFormat(recipe)} 
                onClick={handleRecipeClick}
                showSimilarityScore={!!searchQuery.trim() && !!recipe.similarityScore}
              />
            </div>
          ))}
        </div>

        {searchQuery.trim() && filteredRecipes.length > 0 && (
          <div className="text-center mt-8">
            <p className="text-sm text-muted-foreground">
              Found {filteredRecipes.length} recipes matching your ingredients
              {filteredRecipes.some(r => r.similarityScore) && (
                <span className="block mt-1">
                  Recipes are ranked by ingredient similarity
                </span>
              )}
            </p>
          </div>
        )}
      </div>

      <RecipeModal
        recipe={selectedRecipe ? convertToRecipeCardFormat(selectedRecipe) : null}
        isOpen={isModalOpen}
        onClose={handleCloseModal}
      />
    </section>
  );
};

export default RecipeGridWithBackend;

