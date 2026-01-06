# AI-Powered Lead Scoring Agent and Analytics Dashboard

A comprehensive multi-agent system for B2B lead scoring, enrichment, routing, and automated outreach. This application leverages Generative AI (Claude/Anthropic) to automatically score leads, determine engagement strategies, and generate personalized outreach emails.

## 🎯 Project Overview

This project is an intelligent lead management system that combines:
- **AI-Powered Lead Scoring**: Automatically scores leads from 0-100 based on multiple factors
- **Lead Enrichment**: Enhances lead data with AI-generated research reports
- **Intelligent Routing**: Determines whether leads should receive active outreach or nurture campaigns
- **Email Generation**: Creates personalized outreach emails for high-scoring leads
- **Analytics Dashboard**: Provides insights into lead quality, conversion rates, and performance metrics
- **AI Chat Assistant**: Natural language interface for querying lead data

## 🏗️ Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Dashboard   │  │  LeadTable   │  │  LeadForm    │          │
│  │  Component   │  │  Component   │  │  Component   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                  │                   │
│  ┌──────┴─────────────────┴──────────────────┴───────┐          │
│  │              API Service Layer                     │          │
│  │              (api.js)                             │          │
│  └───────────────────────┬───────────────────────────┘          │
└───────────────────────────┼──────────────────────────────────────┘
                            │ HTTP/REST
┌───────────────────────────┼──────────────────────────────────────┐
│                    BACKEND (FastAPI)                             │
├───────────────────────────┼──────────────────────────────────────┤
│                            │                                       │
│  ┌─────────────────────────┴─────────────────────────┐         │
│  │              API Routes (routes.py)                  │         │
│  │  • GET  /api/leads                                   │         │
│  │  • POST /api/score                                   │         │
│  │  • POST /api/leads/web-form                          │         │
│  │  • POST /api/leads/discover                          │         │
│  │  • POST /api/question                                │         │
│  │  • GET  /api/stats                                   │         │
│  └────────────────────┬────────────────────────────────┘         │
│                       │                                            │
│  ┌────────────────────┴────────────────────────────────┐         │
│  │              Service Layer                            │         │
│  │                                                       │         │
│  │  ┌──────────────────────────────────────────────┐    │         │
│  │  │  DataService                                  │    │         │
│  │  │  • Lead data management                       │    │         │
│  │  │  • CSV/Data loading                           │    │         │
│  │  │  • Statistics calculation                      │    │         │
│  │  └──────────────────────────────────────────────┘    │         │
│  │                                                       │         │
│  │  ┌──────────────────────────────────────────────┐    │         │
│  │  │  LeadEnrichmentService                       │    │         │
│  │  │  • AI-powered lead enrichment                │    │         │
│  │  │  • Research report generation                │    │         │
│  │  └──────────────────────────────────────────────┘    │         │
│  │                                                       │         │
│  │  ┌──────────────────────────────────────────────┐    │         │
│  │  │  LLMService                                   │    │         │
│  │  │  • Lead scoring (0-100)                       │    │         │
│  │  │  • Routing decisions                          │    │         │
│  │  │  • Question answering                         │    │         │
│  │  │  • Lead insights                              │    │         │
│  │  └──────────────────────────────────────────────┘    │         │
│  │                                                       │         │
│  │  ┌──────────────────────────────────────────────┐    │         │
│  │  │  EmailGenerationService                      │    │         │
│  │  │  • Personalized email generation             │    │         │
│  │  │  • Subject line creation                      │    │         │
│  │  │  • CTA generation                             │    │         │
│  │  └──────────────────────────────────────────────┘    │         │
│  │                                                       │         │
│  │  ┌──────────────────────────────────────────────┐    │         │
│  │  │  ScoreStorage                                 │    │         │
│  │  │  • Score persistence (JSON)                   │    │         │
│  │  │  • Cache management                           │    │         │
│  │  └──────────────────────────────────────────────┘    │         │
│  └───────────────────────────────────────────────────────┘         │
│                                                                     │
│  ┌───────────────────────────────────────────────────────┐       │
│  │              External Services                          │       │
│  │  • Anthropic Claude API (AI/LLM)                       │       │
│  │  • Data Storage (CSV files, JSON)                      │       │
│  └───────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────┘
```

### Lead Processing Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    LEAD PROCESSING WORKFLOW                      │
└─────────────────────────────────────────────────────────────────┘

ACTIVE LEADS (Web Form)              PASSIVE LEADS (Discovery)
        │                                      │
        ▼                                      ▼
┌───────────────┐                    ┌───────────────┐
│  Lead Input   │                    │  Lead Input   │
│  (Web Form)   │                    │  (Discovery)  │
└───────┬───────┘                    └───────┬───────┘
        │                                      │
        └──────────────┬───────────────────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │  Lead Enrichment     │
            │  Service             │
            │  • Research Report   │
            │  • Company Insights  │
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │  Lead Scoring        │
            │  Service             │
            │  • Score (0-100)     │
            │  • Explanation       │
            │  • Confidence        │
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │  Routing Decision    │
            │  • Score >= 65       │
            │    → Active Outreach │
            │  • Score 40-64       │
            │    → Nurture         │
            │  • Score < 40        │
            │    → Long-term       │
            └──────────┬───────────┘
                       │
        ┌───────────────┴───────────────┐
        │                               │
        ▼                               ▼
┌───────────────┐            ┌───────────────┐
│ Active        │            │ Nurture      │
│ Outreach      │            │ Campaign      │
│ • Email Gen   │            │ • Sequence    │
│ • Immediate   │            │ • Staggered   │
└───────────────┘            └───────────────┘
```

## 📁 Project Structure

```
genai-lead-scoring-agent/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application entry point
│   │   ├── models.py               # Pydantic models (Lead, LeadScore, etc.)
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py           # API endpoints
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── data_service.py     # Lead data management
│   │       ├── llm_service.py      # AI scoring & routing
│   │       ├── lead_enrichment_service.py  # Lead enrichment
│   │       ├── email_generation_service.py  # Email generation
│   │       └── score_storage.py    # Score persistence
│   ├── data/
│   │   ├── leads.csv               # Lead dataset
│   │   └── sample_leads.csv
│   ├── requirements.txt            # Python dependencies
│   ├── env.example                  # Environment variables template
│   └── scores.json                 # Stored scores (generated)
│
├── frontend/
│   ├── src/
│   │   ├── App.js                  # Main app component
│   │   ├── index.js                # React entry point
│   │   ├── components/
│   │   │   ├── Dashboard.js        # Analytics dashboard
│   │   │   ├── LeadTable.js        # Lead management table
│   │   │   ├── LeadForm.js         # Web form for active leads
│   │   │   └── AIChat.js           # AI chat assistant
│   │   └── services/
│   │       └── api.js              # API client
│   ├── package.json                # Node dependencies
│   └── public/
│       └── index.html
│
├── README.md                       # This file
├── LICENSE
└── .env                            # Environment variables (create from env.example)
```

## 🚀 Features

### 1. **AI-Powered Lead Scoring**
- Automatically scores leads from 0-100 based on:
  - Engagement metrics (visits, time on site, page views)
  - Lead source quality
  - Job title and decision-making authority
  - Industry fit
  - Activity scores
  - Communication preferences
- Provides detailed explanations and confidence scores
- Prefills missing data with intelligent estimates

### 2. **Lead Enrichment**
- AI-generated research reports for each lead
- Company profile analysis
- Industry insights
- Decision-maker identification
- Technology stack analysis (for tech companies)

### 3. **Intelligent Routing**
- Automatically determines next action:
  - **Active Outreach** (Score 65+): Immediate personalized email
  - **Nurture Campaign** (Score 40-64): Email sequence
  - **Long-term Nurture** (Score <40): Educational content
- Provides engagement strategy and talking points

### 4. **Email Generation**
- Generates personalized outreach emails for high-scoring leads
- Creates compelling subject lines
- Writes value-focused email bodies
- Includes clear call-to-action

### 5. **Dual Lead Sources**
- **Active Leads**: Web form submissions (users coming to you)
- **Passive Leads**: Discovered leads (you finding them online)
- Tracks lead source type for analytics

### 6. **Analytics Dashboard**
- Lead statistics and metrics
- Conversion rate analysis
- Industry and source distribution
- AI-generated insights
- Visual charts and graphs

### 7. **AI Chat Assistant**
- Natural language queries about leads
- Ask questions like:
  - "Which leads have the highest potential?"
  - "What are the top industries?"
  - "Show me leads from technology sector"
- Provides actionable insights

### 8. **Lead Management**
- Paginated lead table
- Search functionality
- Bulk lead scoring
- Score analytics and accuracy tracking
- Conversion status tracking

## 🛠️ Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **Anthropic Claude**: AI/LLM for scoring and generation
- **Pandas**: Data processing
- **Pydantic**: Data validation
- **Uvicorn**: ASGI server

### Frontend
- **React**: UI framework
- **Material-UI (MUI)**: Component library
- **Axios**: HTTP client
- **Recharts**: Data visualization

## 📦 Installation & Setup

### Prerequisites
- Python 3.9+
- Node.js 16+
- Anthropic API key

### Backend Setup

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp env.example .env
   ```
   Edit `.env` and add your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=your-api-key-here
   ```

5. **Run the backend**
   ```bash
   uvicorn app.main:app --reload
   ```
   Backend will run on `http://localhost:8000`

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Update API URL** (if needed)
   Edit `src/services/api.js` and update `API_BASE_URL` if your backend is on a different URL.

4. **Run the frontend**
   ```bash
   npm start
   ```
   Frontend will run on `http://localhost:3000`

## 📡 API Endpoints

### Lead Management
- `GET /api/leads` - Get paginated leads (with optional search)
- `GET /api/leads/{lead_id}` - Get specific lead
- `GET /api/leads/{lead_id}/details` - Get detailed lead information

### Lead Scoring
- `POST /api/score` - Score multiple leads
  ```json
  {
    "lead_ids": [1, 2, 3]
  }
  ```

### Active Lead Submission
- `POST /api/leads/web-form` - Submit active lead from web form
  ```json
  {
    "name": "John Doe",
    "email": "john@example.com",
    "company": "Example Corp",
    "job_title": "CEO",
    "industry": "Technology",
    "website": "https://example.com",
    "message": "Interested in your services"
  }
  ```

### Passive Lead Discovery
- `POST /api/leads/discover` - Submit discovered lead
  ```json
  {
    "name": "Jane Smith",
    "email": "jane@company.com",
    "company": "Company Inc",
    "discovery_source": "LinkedIn",
    "context": "Found on LinkedIn company page"
  }
  ```

### Lead Enrichment & Scoring
- `POST /api/leads/{lead_id}/enrich-and-score` - Enrich and score existing lead

### AI Features
- `POST /api/question` - Ask AI questions about leads
  ```json
  {
    "question": "Which leads have the highest potential?",
    "lead_ids": [1, 2, 3]  // optional
  }
  ```

### Analytics
- `GET /api/stats` - Get lead statistics and AI insights
- `GET /api/scores` - Get all stored scores
- `DELETE /api/scores` - Clear all scores

### Health Check
- `GET /api/health` - Health check endpoint

## 🎨 Frontend Components

### Dashboard Component
- Displays lead statistics
- Shows conversion rates
- Industry and source distribution charts
- AI-generated insights
- Real-time data refresh

### LeadTable Component
- Paginated lead table
- Search functionality
- Bulk lead selection and scoring
- Score display with color coding
- Routing decision display
- Conversion status tracking
- Score accuracy indicators

### LeadForm Component
- Web form for active lead submission
- Real-time lead processing
- Displays score and routing decision
- Shows generated email (if high score)
- Form validation

### AIChat Component
- Natural language interface
- Ask questions about leads
- Get AI-powered insights
- Chat history
- Real-time responses

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the `backend` directory:

```env
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

### API Configuration

Update `frontend/src/services/api.js` to point to your backend:

```javascript
const API_BASE_URL = 'http://localhost:8000/api';  // Local
// or
const API_BASE_URL = 'https://your-backend-url.com/api';  // Production
```

## 📊 Data Flow

1. **Lead Ingestion**
   - Active: Web form → API → Enrichment → Scoring
   - Passive: Discovery → API → Enrichment → Scoring

2. **Enrichment Process**
   - AI analyzes lead data
   - Generates research report
   - Enhances lead with insights

3. **Scoring Process**
   - AI evaluates lead on multiple factors
   - Generates score (0-100)
   - Provides explanation and confidence

4. **Routing Decision**
   - Based on score, determines next action
   - Generates engagement strategy
   - Creates talking points

5. **Email Generation** (if high score)
   - Generates personalized email
   - Creates subject line
   - Writes body and CTA

6. **Storage**
   - Scores stored in `scores.json`
   - Lead data in memory/CSV
   - Analytics cached for performance

## 🧪 Testing

### Backend API Testing
Visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI)

### Frontend Testing
```bash
cd frontend
npm test
```

## 🚢 Deployment

### Backend Deployment
1. Set environment variables on hosting platform
2. Install dependencies: `pip install -r requirements.txt`
3. Run with: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

### Frontend Deployment
1. Build: `npm run build`
2. Deploy `build/` folder to hosting platform
3. Update API URL in production

## 📈 Future Enhancements

- [ ] Email sending integration (SendGrid/Mailgun)
- [ ] Nurture campaign email sequence generation
- [ ] CRM integration (Salesforce/HubSpot)
- [ ] Real-time lead discovery from web scraping
- [ ] Advanced analytics and reporting
- [ ] Multi-user support with authentication
- [ ] Webhook support for external integrations
- [ ] A/B testing for email templates

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👤 Author

**Sandeep**

## 🙏 Acknowledgments

- Anthropic for Claude AI
- FastAPI community
- React and Material-UI communities

---

**Note**: This project is a demonstration of AI-powered lead scoring and management. For production use, consider adding authentication, rate limiting, and proper database integration.
