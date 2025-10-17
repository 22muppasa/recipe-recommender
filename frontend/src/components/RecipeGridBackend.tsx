import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import RecipeCard, { Recipe } from './RecipeCard';
import RecipeModal from './RecipeModal';
import SplitText from './SplitText';

interface RecipeGridProps {
  searchQuery: string;
}

// API functions
const fetchRecipes = async (): Promise<Recipe[]> => {
  const response = await fetch('/api/recipes');
  if (!response.ok) {
    throw new Error('Failed to fetch recipes');
  }
  return response.json();
};

const searchRecipesByIngredients = async (ingredients: string[]): Promise<Recipe[]> => {
  const response = await fetch('/api/recipes/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ ingredients, top_n: 12 }),
  });
  if (!response.ok) {
    throw new Error('Failed to search recipes');
  }
  return response.json();
};

const fetchCategories = async (): Promise<string[]> => {
  const response = await fetch('/api/recipes/categories');
  if (!response.ok) {
    throw new Error('Failed to fetch categories');
  }
  return response.json();
};

const RecipeGrid: React.FC<RecipeGridProps> = ({ searchQuery }) => {
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedRecipe, setSelectedRecipe] = useState<Recipe | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [searchIngredients, setSearchIngredients] = useState<string[]>([]);

  // Parse search query into ingredients
  useEffect(() => {
    if (searchQuery.trim()) {
      const ingredients = searchQuery
        .split(/[,\s]+/)
        .map(ing => ing.trim())
        .filter(ing => ing.length > 0);
      setSearchIngredients(ingredients);
    } else {
      setSearchIngredients([]);
    }
  }, [searchQuery]);

  // Fetch categories
  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: fetchCategories,
  });

  // Fetch recipes based on search
  const { data: recipes = [], isLoading, error } = useQuery({
    queryKey: ['recipes', searchIngredients],
    queryFn: () => {
      if (searchIngredients.length > 0) {
        return searchRecipesByIngredients(searchIngredients);
      } else {
        return fetchRecipes();
      }
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Filter recipes by category
  const filteredRecipes = React.useMemo(() => {
    if (selectedCategory === 'All') {
      return recipes;
    }
    return recipes.filter(recipe => 
      recipe.category?.toLowerCase().includes(selectedCategory.toLowerCase())
    );
  }, [recipes, selectedCategory]);

  const handleRecipeClick = (recipe: Recipe) => {
    setSelectedRecipe(recipe);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedRecipe(null);
  };

  // Prepare categories for display
  const allCategories = ['All', ...categories.slice(0, 10)]; // Limit to 10 categories

  if (error) {
    return (
      <section id="recipes" className="py-20 px-6">
        <div className="max-w-7xl mx-auto text-center">
          <h2 className="text-4xl font-bold mb-6">Error Loading Recipes</h2>
          <p className="text-xl text-muted-foreground">
            Unable to load recipes. Please try again later.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section id="recipes" className="py-20 px-6">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <SplitText
            text={searchIngredients.length > 0 ? "Recipe Recommendations" : "Featured Recipes"}
            tag="h2"
            className="text-4xl font-bold mb-6"
            delay={30}
            duration={0.6}
          />
          <SplitText
            text={
              searchIngredients.length > 0 
                ? `Based on your ingredients: ${searchIngredients.join(', ')}`
                : "Discover culinary masterpieces from around the world"
            }
            tag="p"
            className="text-xl text-muted-foreground max-w-2xl mx-auto"
            delay={20}
            duration={0.5}
          />
        </div>

        {allCategories.length > 1 && (
          <div className="flex flex-wrap justify-center gap-4 mb-12">
            {allCategories.map((category) => (
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
        )}

        {isLoading ? (
          <div className="text-center py-20">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            <p className="mt-4 text-muted-foreground">Loading delicious recipes...</p>
          </div>
        ) : filteredRecipes.length === 0 ? (
          <div className="text-center py-20">
            <h3 className="text-2xl font-bold mb-4">No Recipes Found</h3>
            <p className="text-muted-foreground">
              {searchIngredients.length > 0 
                ? "Try different ingredients or remove some filters."
                : "No recipes available at the moment."}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {filteredRecipes.map((recipe) => (
              <div key={recipe.id} className="animate-fade-up">
                <RecipeCard recipe={recipe} onClick={handleRecipeClick} />
              </div>
            ))}
          </div>
        )}
      </div>

      <RecipeModal
        recipe={selectedRecipe}
        isOpen={isModalOpen}
        onClose={handleCloseModal}
      />
    </section>
  );
};

export default RecipeGrid;

