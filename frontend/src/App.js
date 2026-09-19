import React, { useEffect, useState } from 'react';
import {
  AppBar,
  Box,
  Chip,
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
  Inbox as InboxIcon,
  Psychology as PsychologyIcon,
  Work as WorkIcon,
} from '@mui/icons-material';
import Dashboard from './components/Dashboard';
import LeadTable from './components/LeadTable';
import AIChat from './components/AIChat';
import CRMCommandBar from './components/CRMCommandBar';
import LeadFlowInbox from './components/LeadFlowInbox';
import { getModelCard, getStatistics } from './services/api';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#165dff', dark: '#0d3fb3', light: '#e8f0ff' },
    secondary: { main: '#7c3aed' },
    background: { default: '#f6f8fc', paper: '#ffffff' },
    text: { primary: '#172033', secondary: '#5c667a' },
  },
  shape: { borderRadius: 12 },
  typography: {
    fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h4: { letterSpacing: '-0.035em' },
    h5: { letterSpacing: '-0.025em' },
    button: { textTransform: 'none', fontWeight: 700 },
  },
  components: {
    MuiPaper: { styleOverrides: { root: { backgroundImage: 'none' } } },
    MuiButton: { styleOverrides: { root: { borderRadius: 10 } } },
    MuiChip: { styleOverrides: { root: { fontWeight: 600 } } },
  },
});

function App() {
  const [currentTab, setCurrentTab] = useState(0);
  const [stats, setStats] = useState(null);
  const [modelCard, setModelCard] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedRecordIds, setSelectedRecordIds] = useState([]);
  const [selectedInquiryIds, setSelectedInquiryIds] = useState([]);
  const [queueRefreshToken, setQueueRefreshToken] = useState(0);
  const [leadFlowDraftOpportunity, setLeadFlowDraftOpportunity] = useState(null);

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
    <LeadTable
      key="opportunities"
      selected={selectedRecordIds}
      onSelectionChange={setSelectedRecordIds}
      onCreateInquiry={(opportunity) => {
        setLeadFlowDraftOpportunity(opportunity);
        setCurrentTab(2);
      }}
    />,
    <LeadFlowInbox
      key="leadflow"
      selectedIds={selectedInquiryIds}
      onSelectionChange={setSelectedInquiryIds}
      refreshToken={queueRefreshToken}
      draftOpportunity={leadFlowDraftOpportunity}
    />,
    <AIChat key="analytics" />,
  ][currentTab];

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AppBar
        position="static"
        elevation={0}
        sx={{ background: 'linear-gradient(115deg, #111a2e 0%, #19345f 60%, #174ea6 100%)' }}
      >
        <Toolbar sx={{ minHeight: { xs: 72, md: 82 } }}>
          <Box sx={{ bgcolor: 'rgba(255,255,255,0.12)', borderRadius: 2, p: 1, display: 'flex', mr: 1.5 }}>
            <PsychologyIcon />
          </Box>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h6" fontWeight={750}>
              LeadFlow
            </Typography>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.72)' }}>
              Calibrated ML scoring + intent-to-action workflows
            </Typography>
          </Box>
          <Chip
            size="small"
            label="Public demo · no automated outreach"
            sx={{ color: 'white', bgcolor: 'rgba(255,255,255,0.12)', display: { xs: 'none', sm: 'flex' } }}
          />
        </Toolbar>
      </AppBar>
      <Container maxWidth="xl" sx={{ mt: { xs: 2, md: 3 }, mb: 4 }}>
        <CRMCommandBar
          selectedRecordIds={selectedRecordIds}
          selectedInquiryIds={selectedInquiryIds}
          onMutation={() => setQueueRefreshToken((value) => value + 1)}
        />
        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
          <Tabs
            value={currentTab}
            onChange={(_, value) => setCurrentTab(value)}
            variant="scrollable"
            scrollButtons="auto"
          >
            <Tab icon={<DashboardIcon />} label="Model dashboard" iconPosition="start" />
            <Tab icon={<WorkIcon />} label="Opportunities" iconPosition="start" />
            <Tab icon={<InboxIcon />} label="LeadFlow inbox" iconPosition="start" />
            <Tab icon={<AnalyticsIcon />} label="Verified analytics" iconPosition="start" />
          </Tabs>
        </Box>
        {content}
      </Container>
    </ThemeProvider>
  );
}

export default App;
