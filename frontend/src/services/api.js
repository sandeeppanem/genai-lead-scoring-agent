import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

export const getOpportunities = async (page = 1, pageSize = 20, search = null) => {
  const params = { page, page_size: pageSize };
  if (search) params.search = search;
  return (await api.get('/opportunities', { params })).data;
};

export const scoreOpportunities = async (recordIds) => (
  await api.post('/opportunities/score', { record_ids: recordIds })
).data;

export const getScores = async () => (await api.get('/scores')).data;
export const getStatistics = async () => (await api.get('/stats')).data;
export const getModelCard = async () => (await api.get('/model')).data;
export const healthCheck = async () => (await api.get('/health')).data;

export const askQuestion = async (question) => (
  await api.post('/question', { question })
).data;

export default api;
