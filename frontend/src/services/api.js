import axios from 'axios';

// const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';
const API_BASE_URL = 'https://genai-lead-scoring-agent.onrender.com/api';
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Lead Management
export const getLeads = async (page = 1, pageSize = 20, search = null) => {
  const params = { page, page_size: pageSize };
  if (search) params.search = search;
  
  const response = await api.get('/leads', { params });
  return response.data;
};

export const getLead = async (leadId) => {
  const response = await api.get(`/leads/${leadId}`);
  return response.data;
};

// Lead Scoring
export const scoreLeads = async (leadIds) => {
  const response = await api.post('/score', { lead_ids: leadIds });
  return response.data;
};

// AI Questions
export const askQuestion = async (question, leadIds = null) => {
  const payload = { question };
  if (leadIds) payload.lead_ids = leadIds;
  
  const response = await api.post('/question', payload);
  return response.data;
};

// Statistics
export const getStatistics = async () => {
  const response = await api.get('/stats');
  return response.data;
};

// Health Check
export const healthCheck = async () => {
  const response = await api.get('/health');
  return response.data;
};

export default api; 
