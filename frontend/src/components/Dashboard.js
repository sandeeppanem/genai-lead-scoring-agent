import React from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Grid,
  Paper,
  Typography,
} from '@mui/material';
import { Refresh as RefreshIcon } from '@mui/icons-material';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

const formatCurrency = (value) => new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
}).format(value || 0);

const Metric = ({ label, value, note }) => (
  <Grid item xs={12} sm={6} md={3}>
    <Card>
      <CardContent>
        <Typography color="text.secondary" gutterBottom>{label}</Typography>
        <Typography variant="h4">{value}</Typography>
        {note && <Typography variant="caption" color="text.secondary">{note}</Typography>}
      </CardContent>
    </Card>
  </Grid>
);

const Dashboard = ({ stats, modelCard, loading, error, onRefresh }) => {
  if (loading && !stats) {
    return <Box display="flex" justifyContent="center" py={8}><CircularProgress /></Box>;
  }
  if (error) return <Alert severity="error">{error}</Alert>;
  if (!stats) return null;

  const testMetrics = modelCard?.metrics?.xgboost?.test;
  const regionData = Object.entries(stats.regions || {}).map(([name, value]) => ({
    name,
    opportunities: value.opportunities,
    winRate: value.win_rate,
  }));

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4">B2B opportunity model</Typography>
          <Typography color="text.secondary">
            Outcome propensity from leakage-screened qualification fields
          </Typography>
        </Box>
        <Button startIcon={<RefreshIcon />} onClick={onRefresh}>Refresh</Button>
      </Box>

      <Alert severity="info" sx={{ mb: 3 }}>
        This is a public sample without event dates. The test split keeps repeated
        opportunity IDs together, but it is not a temporal production validation.
      </Alert>

      <Grid container spacing={2} mb={3}>
        <Metric label="Opportunities" value={stats.total_opportunities.toLocaleString()} />
        <Metric label="Observed win rate" value={stats.win_rate + '%'} />
        <Metric label="Average amount" value={formatCurrency(stats.average_opportunity_amount_usd)} />
        <Metric
          label="Held-out ROC-AUC"
          value={testMetrics ? testMetrics.roc_auc.toFixed(3) : 'N/A'}
          note={testMetrics ? 'Top-decile lift ' + testMetrics.lift_at_top_10_percent.toFixed(2) + '×' : ''}
        />
      </Grid>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>Regional volume and observed win rate</Typography>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={regionData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis yAxisId="left" />
            <YAxis yAxisId="right" orientation="right" unit="%" />
            <Tooltip />
            <Legend />
            <Bar yAxisId="left" dataKey="opportunities" fill="#0b5cab" />
            <Bar yAxisId="right" dataKey="winRate" fill="#6b4eff" />
          </BarChart>
        </ResponsiveContainer>
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>Model contract</Typography>
        <Typography variant="body2">
          <strong>Champion:</strong> {modelCard?.model_type || 'Unavailable'}
        </Typography>
        <Typography variant="body2">
          <strong>Score:</strong> 100 × calibrated probability of Won
        </Typography>
        <Typography variant="body2">
          <strong>Factors:</strong> {modelCard?.explanation_method || 'Unavailable'}
        </Typography>
        <Typography variant="body2">
          <strong>Model version:</strong> {modelCard?.model_version || 'Unavailable'}
        </Typography>
      </Paper>
    </Box>
  );
};

export default Dashboard;
