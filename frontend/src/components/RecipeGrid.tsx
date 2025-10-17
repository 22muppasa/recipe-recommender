
import React, { useState, useMemo } from 'react';
import RecipeCard, { Recipe } from './RecipeCard';
import RecipeModal from './RecipeModal';
import SplitText from './SplitText';

interface RecipeGridProps {
  searchQuery: string;
}

const SAMPLE_RECIPES: Recipe[] = [
  {
    id: '1',
    title: 'Truffle Risotto with Wild Mushrooms',
    description: 'Creamy arborio rice cooked to perfection with premium truffle oil and fresh wild mushrooms',
    image: 'https://images.unsplash.com/photo-1476124369491-e7addf5db371?w=800&h=600&fit=crop',
    cookTime: 45,
    servings: 4,
    rating: 4.8,
    category: 'Italian',
    difficulty: 'Medium',
    ingredients: [
      '2 cups arborio rice',
      '1 lb mixed wild mushrooms',
      '6 cups warm vegetable broth',
      '1/2 cup white wine',
      '1/4 cup truffle oil',
      '1/2 cup parmesan cheese, grated',
      '2 shallots, finely chopped',
      '3 cloves garlic, minced',
      'Fresh thyme sprigs',
      'Salt and pepper to taste'
    ],
    instructions: [
      'Heat olive oil in a large pan and sauté mushrooms until golden. Set aside.',
      'In the same pan, cook shallots and garlic until fragrant.',
      'Add arborio rice, stirring for 2 minutes until lightly toasted.',
      'Pour in white wine and stir until absorbed.',
      'Add warm broth one ladle at a time, stirring constantly.',
      'Continue until rice is creamy and al dente, about 20 minutes.',
      'Stir in mushrooms, truffle oil, and parmesan.',
      'Season with salt, pepper, and fresh thyme before serving.'
    ]
  },
  {
    id: '2',
    title: 'Mediterranean Grilled Salmon',
    description: 'Fresh Atlantic salmon with Mediterranean herbs, lemon, and olive tapenade',
    image: 'https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=800&h=600&fit=crop',
    cookTime: 25,
    servings: 2,
    rating: 4.9,
    category: 'Mediterranean',
    difficulty: 'Easy',
    ingredients: [
      '2 salmon fillets (6 oz each)',
      '1/4 cup olive oil',
      '2 lemons, juiced and zested',
      '3 cloves garlic, minced',
      '2 tbsp fresh oregano',
      '1 tbsp fresh thyme',
      '1/2 cup kalamata olives',
      '2 tbsp capers',
      '1/2 red onion, thinly sliced',
      'Sea salt and black pepper'
    ],
    instructions: [
      'Preheat grill to medium-high heat.',
      'Mix olive oil, lemon juice, zest, garlic, and herbs in a bowl.',
      'Marinate salmon fillets for 15 minutes.',
      'Season with salt and pepper.',
      'Grill salmon for 4-5 minutes per side until flaky.',
      'Prepare tapenade with olives, capers, and red onion.',
      'Serve salmon with tapenade and lemon wedges.'
    ]
  },
  {
    id: '3',
    title: 'Thai Green Curry with Jasmine Rice',
    description: 'Aromatic green curry with coconut milk, fresh vegetables, and fragrant jasmine rice',
    image: 'https://images.unsplash.com/photo-1455619452474-d2be8b1e70cd?w=800&h=600&fit=crop',
    cookTime: 35,
    servings: 6,
    rating: 4.7,
    category: 'Thai',
    difficulty: 'Medium',
    ingredients: [
      '2 cups jasmine rice',
      '2 cans coconut milk',
      '3 tbsp green curry paste',
      '1 lb chicken thigh, cubed',
      '1 eggplant, cubed',
      '1 bell pepper, sliced',
      '1 cup green beans',
      '1/4 cup fish sauce',
      '2 tbsp brown sugar',
      'Thai basil leaves',
      '2 kaffir lime leaves',
      '1 red chili, sliced'
    ],
    instructions: [
      'Cook jasmine rice according to package instructions.',
      'Heat thick coconut milk in a wok over medium heat.',
      'Add green curry paste and fry until fragrant.',
      'Add chicken and cook until nearly done.',
      'Add remaining coconut milk, vegetables, and seasonings.',
      'Simmer for 15 minutes until vegetables are tender.',
      'Stir in Thai basil and lime leaves.',
      'Serve hot over jasmine rice with fresh chili.'
    ]
  },
  {
    id: '4',
    title: 'French Chocolate Soufflé',
    description: 'Light and airy chocolate soufflé with a molten center and powdered sugar dusting',
    image: 'https://images.unsplash.com/photo-1551024506-0bccd828d307?w=800&h=600&fit=crop',
    cookTime: 40,
    servings: 4,
    rating: 4.6,
    category: 'French',
    difficulty: 'Hard',
    ingredients: [
      '6 oz dark chocolate (70%)',
      '6 large eggs, separated',
      '1/3 cup granulated sugar',
      '2 tbsp butter',
      '2 tbsp all-purpose flour',
      '1 cup whole milk',
      '1 tsp vanilla extract',
      'Pinch of salt',
      'Butter and sugar for ramekins',
      'Powdered sugar for dusting'
    ],
    instructions: [
      'Preheat oven to 375°F. Butter and sugar 4 ramekins.',
      'Melt chocolate in double boiler until smooth.',
      'Make pastry cream with milk, flour, and egg yolks.',
      'Combine chocolate with pastry cream and vanilla.',
      'Whip egg whites with salt until soft peaks form.',
      'Gradually add sugar, whip to stiff peaks.',
      'Fold 1/3 of whites into chocolate, then fold in remaining.',
      'Fill ramekins 3/4 full, bake 12-15 minutes until risen.',
      'Dust with powdered sugar and serve immediately.'
    ]
  },
  {
    id: '5',
    title: 'Korean Bibimbap Bowl',
    description: 'Colorful rice bowl with seasoned vegetables, marinated beef, and gochujang sauce',
    image: 'https://images.unsplash.com/photo-1498654896293-37aacf113fd9?w=800&h=600&fit=crop',
    cookTime: 50,
    servings: 4,
    rating: 4.8,
    category: 'Korean',
    difficulty: 'Medium',
    ingredients: [
      '2 cups short-grain rice',
      '1 lb thinly sliced beef',
      '2 cups spinach',
      '1 large carrot, julienned',
      '1 zucchini, julienned',
      '1 cup bean sprouts',
      '4 shiitake mushrooms, sliced',
      '4 eggs',
      '1/4 cup gochujang',
      '2 tbsp sesame oil',
      '3 tbsp soy sauce',
      '2 tbsp rice vinegar',
      '1 tbsp brown sugar',
      '3 cloves garlic, minced',
      '1 tbsp sesame seeds'
    ],
    instructions: [
      'Cook rice according to package instructions.',
      'Marinate beef in soy sauce, garlic, and sesame oil.',
      'Blanch spinach and season with sesame oil and salt.',
      'Sauté each vegetable separately with light seasoning.',
      'Cook marinated beef until browned and cooked through.',
      'Fry eggs sunny-side up with crispy edges.',
      'Mix gochujang with sesame oil, vinegar, and sugar.',
      'Arrange rice in bowls, top with vegetables and beef.',
      'Top each bowl with fried egg and serve with sauce.',
      'Sprinkle with sesame seeds before serving.'
    ]
  },
  {
    id: '6',
    title: 'Moroccan Lamb Tagine',
    description: 'Slow-cooked lamb with apricots, almonds, and aromatic North African spices',
    image: 'https://images.unsplash.com/photo-1572441713132-51aa6eca671b?w=800&h=600&fit=crop',
    cookTime: 120,
    servings: 6,
    rating: 4.9,
    category: 'Moroccan',
    difficulty: 'Medium',
    ingredients: [
      '3 lbs lamb shoulder, cubed',
      '1 large onion, diced',
      '3 cloves garlic, minced',
      '1 cup dried apricots',
      '1/2 cup almonds, slivered',
      '2 tsp ground cinnamon',
      '1 tsp ground ginger',
      '1 tsp ground cumin',
      '1/2 tsp saffron threads',
      '2 cups beef broth',
      '1 can crushed tomatoes',
      '2 tbsp honey',
      '1/4 cup fresh cilantro',
      'Salt and pepper to taste'
    ],
    instructions: [
      'Heat oil in tagine or heavy pot over medium-high heat.',
      'Brown lamb pieces on all sides, then remove.',
      'Sauté onions until golden, add garlic and spices.',
      'Return lamb to pot with tomatoes and broth.',
      'Add saffron, honey, and apricots.',
      'Bring to boil, then reduce heat and simmer covered.',
      'Cook for 1.5-2 hours until lamb is tender.',
      'Add almonds in last 15 minutes of cooking.',
      'Garnish with fresh cilantro and serve with couscous.'
    ]
  }
];

const CATEGORIES = ['All', 'Italian', 'Mediterranean', 'Thai', 'French', 'Korean', 'Moroccan'];

const RecipeGrid: React.FC<RecipeGridProps> = ({ searchQuery }) => {
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedRecipe, setSelectedRecipe] = useState<Recipe | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const filteredRecipes = useMemo(() => {
    return SAMPLE_RECIPES.filter(recipe => {
      const matchesSearch = recipe.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                           recipe.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
                           recipe.category.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesCategory = selectedCategory === 'All' || recipe.category === selectedCategory;
      return matchesSearch && matchesCategory;
    });
  }, [searchQuery, selectedCategory]);

  const handleRecipeClick = (recipe: Recipe) => {
    setSelectedRecipe(recipe);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedRecipe(null);
  };

  return (
    <section id="recipes" className="py-20 px-6">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <SplitText
            text="Featured Recipes"
            tag="h2"
            className="text-4xl font-bold mb-6"
            delay={30}
            duration={0.6}
          />
          <SplitText
            text="Discover culinary masterpieces from around the world"
            tag="p"
            className="text-xl text-muted-foreground max-w-2xl mx-auto"
            delay={20}
            duration={0.5}
          />
        </div>

        <div className="flex flex-wrap justify-center gap-4 mb-12">
          {CATEGORIES.map((category) => (
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

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {filteredRecipes.map((recipe) => (
            <div key={recipe.id} className="animate-fade-up">
              <RecipeCard recipe={recipe} onClick={handleRecipeClick} />
            </div>
          ))}
        </div>
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
