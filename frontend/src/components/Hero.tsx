
import React from 'react';
import { Search } from 'lucide-react';
import SplitText from './SplitText';

interface HeroProps {
  onSearch: (query: string) => void;
}

const Hero: React.FC<HeroProps> = ({ onSearch }) => {
  const [searchQuery, setSearchQuery] = React.useState('');

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(searchQuery);
  };

  return (
    <section className="min-h-screen flex items-center justify-center px-6 py-20">
      <div className="max-w-4xl mx-auto text-center">
        <SplitText
          text="Discover Your Next Favorite Recipe"
          tag="h1"
          className="hero-title mb-8"
          delay={50}
          duration={0.8}
          from={{ opacity: 0, y: 60, rotateX: 90 }}
          to={{ opacity: 1, y: 0, rotateX: 0 }}
        />
        
        <SplitText
          text="Explore thousands of carefully curated recipes from around the world"
          tag="p"
          className="hero-subtitle mb-12 max-w-2xl mx-auto"
          delay={30}
          duration={0.6}
          from={{ opacity: 0, y: 40 }}
          to={{ opacity: 1, y: 0 }}
        />

        <form onSubmit={handleSearch} className="max-w-md mx-auto mb-8">
          <div className="relative">
            <input
              type="text"
              placeholder="Search for recipes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input w-full pr-12 cursor-target"
            />
            <button
              type="submit"
              className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-primary transition-colors cursor-target"
            >
              <Search size={20} />
            </button>
          </div>
        </form>

        <button
          onClick={() => {
            document.getElementById('recipes')?.scrollIntoView({ behavior: 'smooth' });
          }}
          className="btn-hero cursor-target"
        >
          Explore Recipes
        </button>
      </div>
    </section>
  );
};

export default Hero;
