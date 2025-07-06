# GenAI Lead Scoring Assistant

[![Vercel](https://img.shields.io/badge/Vercel-Live-green?logo=vercel)](https://genai-lead-scoring-agent.vercel.app/)
[![Render](https://img.shields.io/badge/Render-API-blue?logo=render)](https://genai-lead-scoring-agent.onrender.com/)
[![MIT License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A GenAI-powered Sales/Lead-Scoring Assistant with a FastAPI backend and React frontend, using Anthropic Claude API for AI lead scoring and insights.

---

## 🖼️ Demo Screenshot

<!-- Replace the link below with your screenshot or GIF -->
![App Screenshot](screenshot.png)

---

## 🚀 Live Demo

- **Frontend (Vercel):** [https://genai-lead-scoring-agent.vercel.app/](https://genai-lead-scoring-agent.vercel.app/)
- **Backend (Render):** [https://genai-lead-scoring-agent.onrender.com/](https://genai-lead-scoring-agent.onrender.com/)
- **API Docs:** [https://genai-lead-scoring-agent.onrender.com/docs](https://genai-lead-scoring-agent.onrender.com/docs)

---

## 📊 Dataset

- **Source:** Kaggle Lead Scoring Dataset  
  [https://www.kaggle.com/datasets/amritachatterjee09/lead-scoring-dataset](https://www.kaggle.com/datasets/amritachatterjee09/lead-scoring-dataset)

---

## 🛠️ Local Development Setup

### 1. **Clone the Repo**
```bash
git clone https://github.com/sandeeppanem/genai-lead-scoring-agent.git
cd genai-lead-scoring-agent
```

### 2. **Backend Setup**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Add your Anthropic API key to .env
cp .env.example .env  # or create .env manually
# Start the backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. **Frontend Setup**
```bash
cd ../frontend
npm install
# (Optional) Create .env with:
# REACT_APP_API_URL=http://localhost:8000/api
npm start
```

---

## ⚡ Features
- Upload and analyze real lead data
- AI-powered lead scoring and insights
- Conversion outcome analytics
- Deployable for free (Vercel + Render)

---

## 📝 Notes
- The backend uses the Kaggle dataset (see above) and expects it at `backend/data/leads.csv`.
- Do **not** commit your `.env` files or API keys to git.
- For production, set environment variables in Vercel/Render dashboards.

---

## 🙏 Credits
- [Kaggle Lead Scoring Dataset](https://www.kaggle.com/datasets/amritachatterjee09/lead-scoring-dataset)
- [Anthropic Claude API](https://www.anthropic.com/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)

## 🚀 Features

### Core Functionality
- **AI-Powered Lead Scoring**: Automatically score leads from 0-100 with detailed explanations
- **Natural Language Queries**: Ask questions about your leads in plain English
- **Lead Management**: View, search, and manage lead data with pagination
- **Analytics Dashboard**: Visual charts and metrics for lead analysis
- **AI Chat Assistant**: Interactive chat interface for lead insights

### Technical Features
- **Public Data Integration**: Uses public datasets or generates synthetic data
- **Real-time Scoring**: Instant AI scoring with confidence levels
- **Responsive UI**: Modern Material-UI interface
- **RESTful API**: FastAPI backend with automatic documentation
- **CORS Support**: Ready for production deployment

## 🛠️ Tech Stack

### Backend
- **Python 3.8+**
- **FastAPI** - Modern web framework
- **Anthropic Claude 3 Sonnet** - AI/LLM integration
- **Pandas** - Data processing
- **Pydantic** - Data validation

### Frontend
- **React 18**
- **Material-UI (MUI)** - UI components
- **Recharts** - Data visualization
- **Axios** - HTTP client

## 📋 Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher
- Anthropic API key

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd genai-lead-scoring-agent
```

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp env.example .env
# Edit .env and add your Anthropic API key
```

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
```

### 4. Environment Configuration

Create a `.env` file in the backend directory:

```env
ANTHROPIC_API_KEY=your-anthropic-api-key
```

### 5. Run the Application

#### Start Backend (Terminal 1)
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Start Frontend (Terminal 2)
```bash
cd frontend
npm start
```

### 6. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 📊 Data Sources

The application uses:
1. **Public Datasets**: Attempts to load from public lead scoring datasets
2. **Synthetic Data**: Generates realistic lead data if public data is unavailable
3. **Custom Data**: Can be extended to use your own lead data

## 🎯 Usage Guide

### Dashboard
- View key metrics and lead statistics
- Analyze lead distribution by industry, source, and company size
- Get AI-powered insights and recommendations

### Lead Management
- Browse all leads with pagination
- Search leads by name, company, email, or industry
- Select leads for AI scoring
- View detailed lead information

### AI Assistant
- Ask natural language questions about your leads
- Get AI-powered insights and analysis
- Examples:
  - "Which leads have the highest potential?"
  - "What are the top industries in our database?"
  - "Show me leads from the technology sector"
  - "What lead sources are performing best?"

### Lead Scoring
- Select one or multiple leads
- Click "Score Selected" to get AI-powered scores
- View detailed explanations for each score
- Scores range from 0-100 with confidence levels

## 🔧 API Endpoints

### Lead Management
- `GET /api/leads` - Get paginated leads
- `GET /api/leads/{id}` - Get specific lead
- `GET /api/stats` - Get lead statistics

### AI Features
- `POST /api/score` - Score leads using AI
- `POST /api/question` - Ask AI questions about leads

### Health
- `GET /api/health` - Health check

## 🚀 Deployment

### Backend Deployment (Heroku)
```bash
# Create Procfile
echo "web: uvicorn app.main:app --host 0.0.0.0 --port \$PORT" > Procfile

# Deploy to Heroku
heroku create your-app-name
heroku config:set ANTHROPIC_API_KEY=your-api-key
git push heroku main
```

### Frontend Deployment (Vercel)
```bash
# Build the application
npm run build

# Deploy to Vercel
vercel --prod
```

### Environment Variables for Production
```env
ANTHROPIC_API_KEY=your-anthropic-api-key
REACT_APP_API_URL=https://your-backend-url.com/api
```

## 🔒 Security Considerations

- Store API keys securely using environment variables
- Implement proper authentication for production use
- Use HTTPS in production
- Consider rate limiting for API endpoints
- Validate and sanitize all user inputs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:
- Check the API documentation at `/docs`
- Review the console logs for error details
- Ensure your Anthropic API key is valid and has sufficient credits

## 🔮 Future Enhancements

- User authentication and authorization
- Custom lead data import
- Advanced filtering and segmentation
- Email integration
- CRM system integration
- Advanced analytics and reporting
- Multi-language support
- Mobile application

---

**Note**: This application uses Anthropic's Claude API which incurs costs based on usage. Monitor your API usage and set appropriate limits in your Anthropic account. 