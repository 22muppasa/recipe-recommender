# Recipe Recommendation System

A full-stack web application that provides intelligent recipe recommendations based on available ingredients using machine learning algorithms and real recipe data from Hugging Face.


## ✨ Features

- **🔍 Intelligent Search**: Find recipes by entering available ingredients
- **🎯 ML-Powered Recommendations**: Uses TF-IDF vectorization and cosine similarity for accurate matching
- **📊 Similarity Scoring**: Each recommendation shows how well it matches your ingredients
- **🏷️ Category Filtering**: Browse recipes by cuisine type and meal category
- **📱 Responsive Design**: Beautiful UI that works on desktop and mobile
- **🖼️ Real Images**: Authentic food photography from the dataset
- **📋 Complete Recipe Details**: Ingredients with quantities, step-by-step instructions, cook time, servings, and ratings
- **🗂️ Real Dataset**: Over 10,000 recipes from Hugging Face `untitledwebsite123/food-recipes`

## 🏗️ Architecture

### Frontend
- **React 18** with TypeScript
- **Tailwind CSS** for styling
- **shadcn/ui** components
- **Vite** for build tooling

### Backend
- **Flask** Python web framework
- **Recipe Engine** for fast ingredient matching
- **CSV-based data storage** with in-memory indexing
- **CORS enabled** for frontend-backend communication

### Machine Learning
- **TF-IDF Vectorization** for ingredient analysis
- **Cosine Similarity** for recipe matching
- **Real-time search** with <2 second response times
