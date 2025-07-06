import React, { useState, useEffect } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Box,
  Container,
  Tabs,
  Tab,
  CssBaseline,
  ThemeProvider,
  createTheme,
  Alert
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  People as PeopleIcon,
  Chat as ChatIcon
} from '@mui/icons-material';
import Dashboard from './components/Dashboard';
import LeadTable from './components/LeadTable';
import AIChat from './components/AIChat';
import { getStatistics } from './services/api';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

function App() {
  const [currentTab, setCurrentTab] = useState(0);
  const [apiError, setApiError] = useState(null);
  const [dashboardStats, setDashboardStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(false);
  const [statsError, setStatsError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Fetch stats once when app loads
  useEffect(() => {
    fetchDashboardStats();
  }, []);

  const fetchDashboardStats = async (forceRefresh = false) => {
    if (dashboardStats && !forceRefresh) return; // Don't fetch if we already have stats and not forcing refresh
    
    setStatsLoading(true);
    setStatsError(null);
    try {
      const data = await getStatistics();
      setDashboardStats(data);
      setLastUpdated(new Date());
    } catch (err) {
      setStatsError('Failed to fetch statistics');
      console.error('Error fetching stats:', err);
    } finally {
      setStatsLoading(false);
    }
  };

  const handleTabChange = (event, newValue) => {
    setCurrentTab(newValue);
  };

  const renderTabContent = () => {
    switch (currentTab) {
      case 0:
        return <Dashboard 
          stats={dashboardStats} 
          loading={statsLoading} 
          error={statsError}
          lastUpdated={lastUpdated}
          onRefresh={() => fetchDashboardStats(true)}
        />;
      case 1:
        return <LeadTable />;
      case 2:
        return <AIChat />;
      default:
        return <Dashboard 
          stats={dashboardStats} 
          loading={statsLoading} 
          error={statsError}
          lastUpdated={lastUpdated}
          onRefresh={() => fetchDashboardStats(true)}
        />;
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ flexGrow: 1 }}>
        <AppBar position="static">
          <Toolbar>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              GenAI Lead Scoring Assistant
            </Typography>
          </Toolbar>
        </AppBar>
        
        <Container maxWidth="xl" sx={{ mt: 3, mb: 3 }}>
          {apiError && (
            <Alert 
              severity="error" 
              sx={{ mb: 2 }} 
              onClose={() => setApiError(null)}
            >
              {apiError}
            </Alert>
          )}
          
          <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
            <Tabs 
              value={currentTab} 
              onChange={handleTabChange}
              aria-label="main navigation tabs"
            >
              <Tab 
                icon={<DashboardIcon />} 
                label="Dashboard" 
                iconPosition="start"
              />
              <Tab 
                icon={<PeopleIcon />} 
                label="Leads" 
                iconPosition="start"
              />
              <Tab 
                icon={<ChatIcon />} 
                label="AI Assistant" 
                iconPosition="start"
              />
            </Tabs>
          </Box>
          
          <Box role="tabpanel">
            {renderTabContent()}
          </Box>
        </Container>
      </Box>
    </ThemeProvider>
  );
}

export default App; 