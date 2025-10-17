
import React from 'react';
import { X, Clock, Users, Star, ChefHat } from 'lucide-react';
import { Recipe } from './RecipeCard';

interface RecipeModalProps {
  recipe: Recipe | null;
  isOpen: boolean;
  onClose: () => void;
}

const RecipeModal: React.FC<RecipeModalProps> = ({ recipe, isOpen, onClose }) => {
  if (!isOpen || !recipe) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="bg-card max-w-4xl w-full max-h-[90vh] overflow-y-auto rounded-2xl border border-border animate-scale-in">
        <div className="relative">
          <img
            src={recipe.image}
            alt={recipe.title}
            className="w-full h-80 object-cover"
          />
          <button
            onClick={onClose}
            className="absolute top-4 right-4 bg-black/50 hover:bg-black/70 rounded-full p-2 text-white transition-colors cursor-target"
          >
            <X size={20} />
          </button>
        </div>
        
        <div className="p-8">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h1 className="text-3xl font-bold mb-2">{recipe.title}</h1>
              <p className="text-muted-foreground text-lg">{recipe.description}</p>
            </div>
            <div className="flex items-center gap-1 ml-4">
              <Star size={16} className="text-yellow-400 fill-current" />
              <span className="text-lg font-medium">{recipe.rating}</span>
            </div>
          </div>
          
          <div className="grid grid-cols-4 gap-4 mb-8">
            <div className="text-center">
              <Clock className="mx-auto mb-2 text-primary" size={24} />
              <div className="text-sm text-muted-foreground">Cook Time</div>
              <div className="font-semibold">{recipe.cookTime}min</div>
            </div>
            <div className="text-center">
              <Users className="mx-auto mb-2 text-primary" size={24} />
              <div className="text-sm text-muted-foreground">Servings</div>
              <div className="font-semibold">{recipe.servings}</div>
            </div>
            <div className="text-center">
              <ChefHat className="mx-auto mb-2 text-primary" size={24} />
              <div className="text-sm text-muted-foreground">Difficulty</div>
              <div className="font-semibold">{recipe.difficulty}</div>
            </div>
            <div className="text-center">
              <div className="w-6 h-6 mx-auto mb-2 bg-primary rounded-full flex items-center justify-center">
                <span className="text-xs font-bold text-primary-foreground">C</span>
              </div>
              <div className="text-sm text-muted-foreground">Category</div>
              <div className="font-semibold">{recipe.category}</div>
            </div>
          </div>
          
          <div className="grid md:grid-cols-2 gap-8">
            <div>
              <h3 className="text-xl font-bold mb-4">Ingredients</h3>
              <ul className="space-y-2">
                {recipe.ingredients.map((ingredient, index) => (
                  <li key={index} className="flex items-start gap-3">
                    <div className="w-2 h-2 bg-primary rounded-full mt-2 flex-shrink-0" />
                    <span className="text-muted-foreground">{ingredient}</span>
                  </li>
                ))}
              </ul>
            </div>
            
            <div>
              <h3 className="text-xl font-bold mb-4">Instructions</h3>
              <ol className="space-y-4">
                {recipe.instructions.map((instruction, index) => (
                  <li key={index} className="flex gap-4">
                    <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center flex-shrink-0">
                      <span className="text-sm font-bold text-primary-foreground">{index + 1}</span>
                    </div>
                    <p className="text-muted-foreground leading-relaxed">{instruction}</p>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RecipeModal;
