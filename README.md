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
- **Simple Recipe Engine** for fast ingredient matching
- **CSV-based data storage** with in-memory indexing
- **CORS enabled** for frontend-backend communication

### Machine Learning
- **TF-IDF Vectorization** for ingredient analysis
- **Cosine Similarity** for recipe matching
- **Real-time search** with <2 second response times

## 📁 Project Structure

```
recipe-recommendation-system/
├── frontend/                 # React frontend application
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/          # Page components
│   │   └── lib/            # Utility functions
│   ├── public/             # Static assets
│   └── package.json        # Frontend dependencies
├── backend/                # Flask backend application
│   ├── src/
│   │   ├── routes/         # API route handlers
│   │   ├── data/           # Dataset files
│   │   ├── static/         # Built frontend files
│   │   └── main.py         # Flask application entry point
│   ├── venv/               # Python virtual environment
│   └── requirements.txt    # Python dependencies
└── README.md              # This file
```

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.8+
- **Git**

### 1. Clone the Repository

```bash
git clone <repository-url>
cd recipe-recommendation-system
```

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the backend server
python src/main.py
```

The backend will start on `http://localhost:5002`

### 3. Frontend Setup (Development)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will start on `http://localhost:5173`

### 4. Production Build

```bash
# Build frontend for production
cd frontend
npm run build

# Copy built files to backend static directory
cp -r dist/* ../backend/src/static/

# Start production server
cd ../backend
python src/main.py
```

Access the application at `http://localhost:5002`

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
FLASK_ENV=production
FLASK_DEBUG=False
PORT=5002
```

### Dataset Configuration

The application uses a curated dataset from Hugging Face. The dataset file should be placed in `backend/src/data/recipes_deploy_10k.csv`.

## 📊 API Endpoints

### Recipe Search
```http
POST /api/recipes/search
Content-Type: application/json

{
  "ingredients": ["chicken", "rice", "onion"],
  "top_n": 6
}
```

### Get Random Recipes
```http
GET /api/recipes/random?count=20
```

### Get Recipes by Category
```http
GET /api/recipes/by-category/Chicken%20Breast
```

### Get Categories
```http
GET /api/recipes/categories
```

### Health Check
```http
GET /api/health
```

## 🧪 Testing

### Backend Testing

```bash
cd backend
source venv/bin/activate

# Test the API endpoints
curl http://localhost:5002/api/health
curl -X POST http://localhost:5002/api/recipes/search \
  -H "Content-Type: application/json" \
  -d '{"ingredients": ["chicken", "rice"], "top_n": 3}'
```

### Frontend Testing

```bash
cd frontend
npm test
```

## 🔍 How It Works

### 1. Data Processing
- Recipes are loaded from CSV format
- R-style list notation `c("item1", "item2")` is parsed into Python lists
- Ingredient indexing creates fast lookup tables

### 2. Search Algorithm
- User ingredients are tokenized and cleaned
- TF-IDF-like scoring matches ingredients to recipes
- Results are ranked by similarity score
- Top matches are returned with metadata

### 3. Category Filtering
- Recipes are grouped by category from the dataset
- Dynamic category buttons are generated
- Filtering works in combination with search

## 🚀 Deployment

### Local Deployment
```bash
# Build and start the application
cd frontend && npm run build
cp -r dist/* ../backend/src/static/
cd ../backend && python src/main.py
```

### Production Deployment
The application is designed to be deployed on platforms like:
- **Heroku**
- **Railway**
- **DigitalOcean App Platform**
- **AWS Elastic Beanstalk**

Ensure the following for production:
- Set `FLASK_ENV=production`
- Use a production WSGI server like Gunicorn
- Configure proper CORS settings
- Set up proper logging

## 🛠️ Development

### Adding New Features

1. **Backend**: Add new routes in `backend/src/routes/`
2. **Frontend**: Add new components in `frontend/src/components/`
3. **Styling**: Use Tailwind CSS classes
4. **State Management**: Use React hooks

### Code Style

- **Python**: Follow PEP 8
- **TypeScript**: Use ESLint and Prettier
- **CSS**: Use Tailwind CSS utilities

## 📈 Performance

- **Search Speed**: <2 seconds for ingredient matching
- **Dataset Size**: 10,000+ recipes optimized for deployment
- **Memory Usage**: Efficient in-memory indexing
- **Response Times**: Fast API responses with proper caching

## 🐛 Troubleshooting

### Common Issues

1. **Backend not starting**
   - Check Python version (3.8+ required)
   - Ensure virtual environment is activated
   - Verify all dependencies are installed

2. **Frontend build fails**
   - Check Node.js version (18+ required)
   - Clear node_modules and reinstall: `rm -rf node_modules && npm install`

3. **Search not working**
   - Check backend is running on correct port
   - Verify CORS configuration
   - Check browser console for errors

4. **No recipes found**
   - Ensure dataset file exists in `backend/src/data/`
   - Check dataset format and parsing

### Logs

Backend logs are available in the console when running `python src/main.py`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Hugging Face** for the recipe dataset
- **Food.com** for the original recipe data
- **React** and **Flask** communities for excellent documentation
- **Tailwind CSS** for the utility-first CSS framework

## 📞 Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the API documentation

---

**Built with ❤️ using React, Flask, and Machine Learning**

