import React, { useEffect, useState } from 'react';
import {
  AppBar,
  Box,
  Container,
  CssBaseline,
  Tab,
  Tabs,
  ThemeProvider,
  Toolbar,
  Typography,
  createTheme,
} from '@mui/material';
import {
  Analytics as AnalyticsIcon,
  Dashboard as DashboardIcon,
  Work as WorkIcon,
} from '@mui/icons-material';
import Dashboard from './components/Dashboard';
import LeadTable from './components/LeadTable';
import AIChat from './components/AIChat';
import { getModelCard, getStatistics } from './services/api';

const theme = createTheme({
  palette: {
    primary: { main: '#0b5cab' },
    secondary: { main: '#6b4eff' },
  },
});

function App() {
  const [currentTab, setCurrentTab] = useState(0);
  const [stats, setStats] = useState(null);
  const [modelCard, setModelCard] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statistics, model] = await Promise.all([
        getStatistics(),
        getModelCard(),
      ]);
      setStats(statistics);
      setModelCard(model);
    } catch (requestError) {
      console.error(requestError);
      setError('Unable to load the B2B opportunity service.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  const content = [
    <Dashboard
      key="dashboard"
      stats={stats}
      modelCard={modelCard}
      loading={loading}
      error={error}
      onRefresh={loadDashboard}
    />,
    <LeadTable key="opportunities" />,
    <AIChat key="analytics" />,
  ][currentTab];

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Hybrid B2B Opportunity Prioritization
          </Typography>
          <Typography variant="caption">
            Calibrated XGBoost + grounded GenAI
          </Typography>
        </Toolbar>
      </AppBar>
      <Container maxWidth="xl" sx={{ mt: 3, mb: 3 }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
          <Tabs value={currentTab} onChange={(_, value) => setCurrentTab(value)}>
            <Tab icon={<DashboardIcon />} label="Model dashboard" iconPosition="start" />
            <Tab icon={<WorkIcon />} label="Opportunities" iconPosition="start" />
            <Tab icon={<AnalyticsIcon />} label="Verified analytics" iconPosition="start" />
          </Tabs>
        </Box>
        {content}
      </Container>
    </ThemeProvider>
  );
}

export default App;
