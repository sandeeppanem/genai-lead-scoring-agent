import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  IconButton,
  Pagination,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import {
  DeleteOutline as DeleteIcon,
  Refresh as RefreshIcon,
  Score as ScoreIcon,
} from '@mui/icons-material';
import {
  clearScores,
  getOpportunities,
  getScores,
  scoreOpportunities,
} from '../services/api';

const pageSize = 20;
const money = (value) => new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
}).format(value || 0);

const scoreColor = (score) => {
  if (score >= 40) return 'success';
  if (score >= 15) return 'warning';
  return 'default';
};

const LeadTable = () => {
  const [opportunities, setOpportunities] = useState([]);
  const [scores, setScores] = useState({});
  const [selected, setSelected] = useState([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [scoring, setScoring] = useState(false);
  const [error, setError] = useState(null);

  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / pageSize)), [total]);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [data, cached] = await Promise.all([
        getOpportunities(page, pageSize, search),
        getScores(),
      ]);
      setOpportunities(data.opportunities);
      setTotal(data.total);
      setScores(cached.scores || {});
      setSelected([]);
    } catch (requestError) {
      console.error(requestError);
      setError('Unable to load opportunities.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, search]);

  const runScoring = async () => {
    if (!selected.length) return;
    setScoring(true);
    setError(null);
    try {
      const results = await scoreOpportunities(selected);
      const updated = { ...scores };
      results.forEach((result) => { updated[result.record_id] = result; });
      setScores(updated);
      setSelected([]);
    } catch (requestError) {
      console.error(requestError);
      setError('ML scoring failed. Check model health and try again.');
    } finally {
      setScoring(false);
    }
  };

  const clearCache = async () => {
    await clearScores();
    setScores({});
  };

  const factorTooltip = (score) => (
    <Box sx={{ maxWidth: 420 }}>
      <Typography variant="body2">{score.explanation}</Typography>
      {(score.factors || []).map((factor) => (
        <Typography key={factor.feature + factor.value} variant="caption" display="block">
          {factor.direction === 'increases' ? '↑' : '↓'} {factor.label}: {String(factor.value)}
        </Typography>
      ))}
      <Typography variant="caption" display="block" sx={{ mt: 1 }}>
        {score.explanation_method}
      </Typography>
    </Box>
  );

  return (
    <Box>
      <Box display="flex" gap={1} alignItems="center" mb={2}>
        <TextField
          size="small"
          label="Search opportunity, product, region, or route"
          value={search}
          onChange={(event) => { setSearch(event.target.value); setPage(1); }}
          sx={{ flexGrow: 1 }}
        />
        <Button
          variant="contained"
          startIcon={scoring ? <CircularProgress size={18} /> : <ScoreIcon />}
          disabled={!selected.length || scoring}
          onClick={runScoring}
        >
          Score selected ({selected.length})
        </Button>
        <Tooltip title="Refresh">
          <IconButton onClick={load}><RefreshIcon /></IconButton>
        </Tooltip>
        <Tooltip title="Clear current-model score cache">
          <IconButton onClick={clearCache}><DeleteIcon /></IconButton>
        </Tooltip>
      </Box>

      <Alert severity="warning" sx={{ mb: 2 }}>
        “Won/Loss” is shown only for portfolio evaluation. It is excluded from the
        feature pipeline and is never sent to XGBoost.
      </Alert>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox">
                <Checkbox
                  checked={selected.length === opportunities.length && opportunities.length > 0}
                  indeterminate={selected.length > 0 && selected.length < opportunities.length}
                  onChange={() => setSelected(
                    selected.length === opportunities.length
                      ? []
                      : opportunities.map((item) => item.record_id)
                  )}
                />
              </TableCell>
              <TableCell>Opportunity</TableCell>
              <TableCell>Product</TableCell>
              <TableCell>Region</TableCell>
              <TableCell>Route</TableCell>
              <TableCell align="right">Amount</TableCell>
              <TableCell>Client bands</TableCell>
              <TableCell>Competitor</TableCell>
              <TableCell>ML score</TableCell>
              <TableCell>Policy</TableCell>
              <TableCell>Actual</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {opportunities.map((item) => {
              const result = scores[item.record_id];
              return (
                <TableRow key={item.record_id} hover>
                  <TableCell padding="checkbox">
                    <Checkbox
                      checked={selected.includes(item.record_id)}
                      onChange={() => setSelected((current) => (
                        current.includes(item.record_id)
                          ? current.filter((id) => id !== item.record_id)
                          : [...current, item.record_id]
                      ))}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="subtitle2">#{item.opportunity_number}</Typography>
                    <Typography variant="caption">Record {item.record_id}</Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{item.supplies_subgroup}</Typography>
                    <Typography variant="caption">{item.supplies_group}</Typography>
                  </TableCell>
                  <TableCell>{item.region}</TableCell>
                  <TableCell>{item.route_to_market}</TableCell>
                  <TableCell align="right">{money(item.opportunity_amount_usd)}</TableCell>
                  <TableCell>
                    <Typography variant="caption" display="block">
                      Revenue: {item.client_size_by_revenue}/5
                    </Typography>
                    <Typography variant="caption" display="block">
                      Employees: {item.client_size_by_employee_count}/5
                    </Typography>
                  </TableCell>
                  <TableCell>{item.competitor_type}</TableCell>
                  <TableCell>
                    {result ? (
                      <Tooltip title={factorTooltip(result)} arrow>
                        <Chip
                          label={result.score + '/100'}
                          color={scoreColor(result.score)}
                          size="small"
                        />
                      </Tooltip>
                    ) : <Typography variant="caption">Not scored</Typography>}
                  </TableCell>
                  <TableCell>
                    {result ? (
                      <Chip label={result.routing.next_action.replace('_', ' ')} size="small" />
                    ) : '—'}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={item.outcome}
                      size="small"
                      color={item.outcome === 'Won' ? 'success' : 'default'}
                      variant="outlined"
                    />
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
        {loading && <Box textAlign="center" py={2}><CircularProgress size={24} /></Box>}
      </TableContainer>
      <Box display="flex" justifyContent="center" mt={2}>
        <Pagination count={totalPages} page={page} onChange={(_, value) => setPage(value)} />
      </Box>
    </Box>
  );
};

export default LeadTable;
