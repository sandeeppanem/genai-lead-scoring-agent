import React from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Chip,
  List,
  ListItem,
  ListItemText,
  Divider,
  Button
} from '@mui/material';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { Refresh as RefreshIcon } from '@mui/icons-material';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D'];

const Dashboard = ({ stats, loading, error, lastUpdated, onRefresh }) => {
  const prepareChartData = (data, limit = 5) => {
    if (!data) return [];
    return Object.entries(data)
      .sort(([,a], [,b]) => b - a)
      .slice(0, limit)
      .map(([name, value]) => ({ name, value }));
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => onRefresh()}>
          {error}
        </Alert>
        <Button 
          variant="contained" 
          startIcon={<RefreshIcon />}
          onClick={onRefresh}
        >
          Retry
        </Button>
      </Box>
    );
  }

  if (!stats) {
    return (
      <Alert severity="info">
        No statistics available
      </Alert>
    );
  }

  const industryData = prepareChartData(stats.industries);
  const sourceData = prepareChartData(stats.lead_sources);
  const sizeData = prepareChartData(stats.company_sizes);

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" component="h1">
            Lead Analytics Dashboard
          </Typography>
          {lastUpdated && (
            <Typography variant="caption" color="text.secondary">
              Last updated: {lastUpdated.toLocaleString()}
            </Typography>
          )}
        </Box>
        <Button 
          variant="outlined" 
          startIcon={<RefreshIcon />}
          onClick={onRefresh}
        >
          Refresh Stats
        </Button>
      </Box>

      <Grid container spacing={3}>
        {/* Key Metrics */}
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Leads
              </Typography>
              <Typography variant="h3" component="div">
                {stats.total_leads || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Recent Leads (30 days)
              </Typography>
              <Typography variant="h3" component="div">
                {stats.recent_leads || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Top Industry
              </Typography>
              <Typography variant="h6" component="div">
                {industryData[0]?.name || 'N/A'}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                {industryData[0]?.value || 0} leads
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Best Lead Source
              </Typography>
              <Typography variant="h6" component="div">
                {sourceData[0]?.name || 'N/A'}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                {sourceData[0]?.value || 0} leads
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Charts */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              Lead Distribution by Industry
            </Typography>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={industryData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {industryData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              Lead Sources Performance
            </Typography>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sourceData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#8884d8" />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              Company Size Distribution
            </Typography>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sizeData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#82ca9d" />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* AI Insights */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: 400, overflow: 'auto' }}>
            <Typography variant="h6" gutterBottom>
              AI Insights & Recommendations
            </Typography>
            
            {stats.ai_insights && (
              <Box>
                {stats.ai_insights.top_industries && (
                  <Box mb={2}>
                    <Typography variant="subtitle2" color="primary" gutterBottom>
                      Top Performing Industries
                    </Typography>
                    <Box display="flex" gap={1} flexWrap="wrap">
                      {stats.ai_insights.top_industries.map((industry, index) => (
                        <Chip key={index} label={industry} size="small" />
                      ))}
                    </Box>
                  </Box>
                )}

                {stats.ai_insights.best_lead_sources && (
                  <Box mb={2}>
                    <Typography variant="subtitle2" color="primary" gutterBottom>
                      Best Lead Sources
                    </Typography>
                    <Box display="flex" gap={1} flexWrap="wrap">
                      {stats.ai_insights.best_lead_sources.map((source, index) => (
                        <Chip key={index} label={source} size="small" variant="outlined" />
                      ))}
                    </Box>
                  </Box>
                )}

                {stats.ai_insights.recommendations && (
                  <Box mb={2}>
                    <Typography variant="subtitle2" color="primary" gutterBottom>
                      AI Recommendations
                    </Typography>
                    <List dense>
                      {stats.ai_insights.recommendations.map((rec, index) => (
                        <ListItem key={index} sx={{ py: 0.5 }}>
                          <ListItemText 
                            primary={rec}
                            primaryTypographyProps={{ variant: 'body2' }}
                          />
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                )}

                {stats.ai_insights.trends && (
                  <Box>
                    <Typography variant="subtitle2" color="primary" gutterBottom>
                      Trends Analysis
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      {stats.ai_insights.trends}
                    </Typography>
                  </Box>
                )}
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard; 