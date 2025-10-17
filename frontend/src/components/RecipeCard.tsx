
import React from 'react';
import { Clock, Users, Star } from 'lucide-react';

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
}

interface RecipeCardProps {
  recipe: Recipe;
  onClick: (recipe: Recipe) => void;
}

const RecipeCard: React.FC<RecipeCardProps> = ({ recipe, onClick }) => {
  return (
    <div
      className="recipe-card cursor-target group"
      onClick={() => onClick(recipe)}
    >
      <div className="aspect-video overflow-hidden">
        <img
          src={recipe.image}
          alt={recipe.title}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
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

export default RecipeCard;
