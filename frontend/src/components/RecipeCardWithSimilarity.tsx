import React from 'react';
import { Clock, Users, Star, Target } from 'lucide-react';

export interface Recipe {
  id: string;
  title: string;
  description: string;
  image: string;
  cookTime: number;
  servings: number;
  rating: number;
  category: string;
  difficulty: 'Easy' | 'Medium' | 'Hard';
  ingredients: string[];
  instructions: string[];
  similarityScore?: number;
}

interface RecipeCardProps {
  recipe: Recipe;
  onClick: (recipe: Recipe) => void;
  showSimilarityScore?: boolean;
}

const RecipeCardWithSimilarity: React.FC<RecipeCardProps> = ({ 
  recipe, 
  onClick, 
  showSimilarityScore = false 
}) => {
  const formatSimilarityScore = (score: number) => {
    return Math.round(score * 100);
  };

  const getSimilarityColor = (score: number) => {
    const percentage = score * 100;
    if (percentage >= 80) return 'text-green-400 bg-green-500/20';
    if (percentage >= 60) return 'text-yellow-400 bg-yellow-500/20';
    if (percentage >= 40) return 'text-orange-400 bg-orange-500/20';
    return 'text-red-400 bg-red-500/20';
  };

  return (
    <div
      className="recipe-card cursor-target group relative"
      onClick={() => onClick(recipe)}
    >
      {showSimilarityScore && recipe.similarityScore && (
        <div className="absolute top-3 right-3 z-10">
          <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getSimilarityColor(recipe.similarityScore)}`}>
            <Target size={12} />
            <span>{formatSimilarityScore(recipe.similarityScore)}% match</span>
          </div>
        </div>
      )}
      
      <div className="aspect-video overflow-hidden">
        <img
          src={recipe.image}
          alt={recipe.title}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
          onError={(e) => {
            // Fallback to placeholder if image fails to load
            e.currentTarget.src = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800&h=600&fit=crop&q=food";
          }}
        />
      </div>
      
      <div className="p-6">
        <div className="flex items-center justify-between mb-3">
          <span className="category-tag text-xs">{recipe.category}</span>
          <div className="flex items-center gap-1">
            <Star size={14} className="text-yellow-400 fill-current" />
            <span className="text-sm font-medium">{recipe.rating}</span>
          </div>
        </div>
        
        <h3 className="text-xl font-bold mb-2 group-hover:text-primary transition-colors">
          {recipe.title}
        </h3>
        
        <p className="text-muted-foreground text-sm mb-4 line-clamp-2">
          {recipe.description}
        </p>

        {/* Show ingredient count */}
        {recipe.ingredients && recipe.ingredients.length > 0 && (
          <div className="mb-3">
            <p className="text-xs text-muted-foreground">
              {recipe.ingredients.length} ingredients • {recipe.instructions?.length || 0} steps
            </p>
          </div>
        )}
        
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <Clock size={14} />
            <span>{recipe.cookTime}min</span>
          </div>
          <div className="flex items-center gap-1">
            <Users size={14} />
            <span>{recipe.servings} servings</span>
          </div>
          <span className={`px-2 py-1 rounded-full text-xs ${
            recipe.difficulty === 'Easy' ? 'bg-green-500/20 text-green-400' :
            recipe.difficulty === 'Medium' ? 'bg-yellow-500/20 text-yellow-400' :
            'bg-red-500/20 text-red-400'
          }`}>
            {recipe.difficulty}
          </span>
        </div>
      </div>
    </div>
  );
};

export default RecipeCardWithSimilarity;

