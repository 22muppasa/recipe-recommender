
import React, { useState } from 'react';
import TargetCursor from '@/components/TargetCursor';
import Hero from '@/components/Hero';
import RecipeGrid from '@/components/RecipeGridWithBackend';

const Index = () => {
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    // Scroll to recipes section
    setTimeout(() => {
      document.getElementById('recipes')?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <TargetCursor
        targetSelector=".cursor-target"
        spinDuration={3}
        hideDefaultCursor={true}
      />
      
      <Hero onSearch={handleSearch} />
      <RecipeGrid searchQuery={searchQuery} />
    </div>
  );
};

export default Index;
