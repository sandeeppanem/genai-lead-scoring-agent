import React, { useState, useEffect } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  TextField,
  Box,
  Typography,
  Chip,
  IconButton,
  Tooltip,
  CircularProgress,
  Alert,
  Pagination,
  FormControlLabel,
  Checkbox
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Search as SearchIcon,
  Score as ScoreIcon,
  Info as InfoIcon
} from '@mui/icons-material';
import { default as api, scoreLeads } from '../services/api';

const LeadTable = () => {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [scoring, setScoring] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [selectedLeads, setSelectedLeads] = useState([]);
  const [error, setError] = useState(null);
  const [scores, setScores] = useState({});
  const [scoreAnalytics, setScoreAnalytics] = useState(null);
  const [totalLeads, setTotalLeads] = useState(0);

  const pageSize = 20;

  useEffect(() => {
    const fetchLeads = async () => {
      try {
        setLoading(true);
        const params = {
          page: currentPage,
          page_size: pageSize,
        };
        if (searchTerm) params.search = searchTerm;
        const response = await api.get('/leads', { params });
        const data = response.data;
        setLeads(data.leads);
        setTotalLeads(data.total);
        setTotalPages(Math.ceil(data.total / pageSize));
      } catch (error) {
        console.error('Error fetching leads:', error);
      } finally {
        setLoading(false);
      }
    };

    const fetchCachedScores = async () => {
      try {
        const response = await fetch('/api/scores');
        const data = await response.json();
        const scoresMap = {};
        Object.entries(data.scores).forEach(([leadId, scoreData]) => {
          scoresMap[parseInt(leadId)] = scoreData;
        });
        setScores(scoresMap);
        console.log(`Loaded ${data.total_scored} cached scores`);
      } catch (error) {
        console.error('Error fetching cached scores:', error);
      }
    };

    fetchLeads();
    fetchCachedScores();
  }, [currentPage, pageSize, searchTerm]);

  const calculateScoreAnalytics = () => {
    if (!leads.length || Object.keys(scores).length === 0) {
      console.log('No leads or scores available for analytics');
      return null;
    }

    console.log('Calculating analytics with:', { leadsCount: leads.length, scoresCount: Object.keys(scores).length });

    const scoreRanges = {
      '0-25': { total: 0, converted: 0 },
      '26-45': { total: 0, converted: 0 },
      '46-65': { total: 0, converted: 0 },
      '66-80': { total: 0, converted: 0 },
      '81-100': { total: 0, converted: 0 }
    };

    // Only analyze leads that have been scored
    leads.forEach(lead => {
      if (scores[lead.id] && lead.converted !== undefined) {
        const score = scores[lead.id].score;
        let range;
        if (score <= 25) range = '0-25';
        else if (score <= 45) range = '26-45';
        else if (score <= 65) range = '46-65';
        else if (score <= 80) range = '66-80';
        else range = '81-100';

        scoreRanges[range].total++;
        if (isLeadConverted(lead.converted)) {
          scoreRanges[range].converted++;
        }
        console.log(`Lead ${lead.id}: Score ${score}, Converted ${lead.converted}, Range ${range}`);
      }
    });

    console.log('Final score ranges:', scoreRanges);
    return scoreRanges;
  };

  const calculateOverallAccuracy = () => {
    if (!leads.length || Object.keys(scores).length === 0) {
      return null;
    }

    let accuratePredictions = 0;
    let totalScoredWithConversion = 0;

    leads.forEach(lead => {
      if (scores[lead.id] && lead.converted !== undefined) {
        totalScoredWithConversion++;
        const accuracy = getScoreAccuracy(scores[lead.id].score, lead.converted);
        if (accuracy === 'accurate-high' || accuracy === 'accurate-low') {
          accuratePredictions++;
        }
      }
    });

    if (totalScoredWithConversion === 0) {
      return null;
    }

    return {
      accurate: accuratePredictions,
      total: totalScoredWithConversion,
      percentage: ((accuratePredictions / totalScoredWithConversion) * 100).toFixed(1)
    };
  };

  const handleClearScores = async () => {
    if (window.confirm('Are you sure you want to clear all cached scores? This will require rescoring all leads.')) {
      try {
        const response = await fetch('/api/scores', { method: 'DELETE' });
        if (response.ok) {
          setScores({});
          setScoreAnalytics(null);
          console.log('All scores cleared');
        } else {
          console.error('Failed to clear scores');
        }
      } catch (error) {
        console.error('Error clearing scores:', error);
      }
    }
  };

  const handleScoreLeads = async () => {
    if (selectedLeads.length === 0) {
      setError('Please select leads to score');
      return;
    }

    setScoring(true);
    setError(null);
    try {
      const scoreResults = await scoreLeads(selectedLeads);
      console.log('Score results received:', scoreResults);
      
      // Update scores state
      const newScores = { ...scores };
      scoreResults.forEach(score => {
        newScores[score.lead_id] = score;
      });
      setScores(newScores);
      console.log('Updated scores state:', newScores);
      
      // Calculate analytics
      setTimeout(() => {
        const analytics = calculateScoreAnalytics();
        console.log('Calculated analytics:', analytics);
        setScoreAnalytics(analytics);
      }, 100);
      
      setSelectedLeads([]);
    } catch (err) {
      setError('Failed to score leads');
      console.error('Error scoring leads:', err);
    } finally {
      setScoring(false);
    }
  };

  const handleSelectLead = (leadId) => {
    setSelectedLeads(prev => 
      prev.includes(leadId) 
        ? prev.filter(id => id !== leadId)
        : [...prev, leadId]
    );
  };

  const handleSelectAll = () => {
    if (selectedLeads.length === leads.length) {
      setSelectedLeads([]);
    } else {
      setSelectedLeads(leads.map(lead => lead.id));
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return 'success';
    if (score >= 60) return 'warning';
    if (score >= 40) return 'info';
    return 'error';
  };

  const getScoreAccuracy = (score, converted) => {
    if (!score || converted === undefined) return 'neutral';
    
    // Updated thresholds based on real conversion data analysis
    const isHighScore = score >= 65; // Changed from 60 to 65
    const isConverted = isLeadConverted(converted);
    
    if (isHighScore && isConverted) return 'accurate-high';
    if (!isHighScore && !isConverted) return 'accurate-low';
    if (isHighScore && !isConverted) return 'overestimated';
    if (!isHighScore && isConverted) return 'underestimated';
    
    return 'neutral';
  };

  const isLeadConverted = (converted) => {
    return converted === 1 || converted === true || converted === '1' || converted === 'true' || converted === 'converted';
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  // Calculate overall accuracy
  const overallAccuracy = calculateOverallAccuracy();

  if (loading && leads.length === 0) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h5" component="h2">
          Leads ({totalLeads} total)
        </Typography>
        <Box display="flex" alignItems="center" gap={2}>
          <Typography variant="body2" color="text.secondary">
            {Object.keys(scores).length} leads scored
          </Typography>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={() => {
              setCurrentPage(1);
              setSearchTerm('');
            }}
            disabled={loading}
          >
            Refresh
          </Button>
          <Button
            variant="outlined"
            color="warning"
            onClick={handleClearScores}
            disabled={Object.keys(scores).length === 0}
          >
            Clear Scores
          </Button>
          <Button
            variant="contained"
            startIcon={scoring ? <CircularProgress size={20} /> : <ScoreIcon />}
            onClick={handleScoreLeads}
            disabled={scoring || selectedLeads.length === 0}
          >
            {scoring ? 'Scoring...' : `Score Selected (${selectedLeads.length})`}
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Box display="flex" gap={2} mb={2}>
        <TextField
          placeholder="Search leads..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />
          }}
          sx={{ flexGrow: 1 }}
        />
      </Box>

      {/* Accuracy Legend - Only show if we have scored leads */}
      {Object.keys(scores).length > 0 && (
        <Box display="flex" gap={2} mb={2} alignItems="center">
          <Typography variant="caption" color="text.secondary">
            AI Score Accuracy:
          </Typography>
          <Box display="flex" gap={1} alignItems="center">
            <Chip label="✓" color="success" size="small" sx={{ minWidth: '20px', height: '20px' }} />
            <Typography variant="caption">Accurate</Typography>
          </Box>
          <Box display="flex" gap={1} alignItems="center">
            <Chip label="↑" color="warning" size="small" sx={{ minWidth: '20px', height: '20px' }} />
            <Typography variant="caption">Overestimated</Typography>
          </Box>
          <Box display="flex" gap={1} alignItems="center">
            <Chip label="↓" color="error" size="small" sx={{ minWidth: '20px', height: '20px' }} />
            <Typography variant="caption">Underestimated</Typography>
          </Box>
        </Box>
      )}

      {/* Score Analytics */}
      {scoreAnalytics && (
        <Box mb={2} p={2} bgcolor="grey.50" borderRadius={1}>
          <Typography variant="subtitle2" gutterBottom>
            AI Score vs Conversion Rate Analysis (Scored Leads Only)
          </Typography>
          <Box display="flex" gap={2} flexWrap="wrap">
            {Object.entries(scoreAnalytics).map(([range, data]) => {
              const conversionRate = data.total > 0 ? ((data.converted / data.total) * 100).toFixed(1) : 0;
              return (
                <Box key={range} display="flex" alignItems="center" gap={1}>
                  <Typography variant="caption" fontWeight="bold">
                    {range}:
                  </Typography>
                  <Typography variant="caption">
                    {data.converted}/{data.total} ({conversionRate}%)
                  </Typography>
                </Box>
              );
            })}
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            Based on {Object.values(scoreAnalytics).reduce((sum, data) => sum + data.total, 0)} scored leads with conversion data
          </Typography>
        </Box>
      )}

      {/* Overall Accuracy */}
      {overallAccuracy && (
        <Box mb={2} p={2} bgcolor="blue.50" borderRadius={1}>
          <Typography variant="subtitle2" gutterBottom>
            Overall AI Score Accuracy
          </Typography>
          <Box display="flex" alignItems="center" gap={2}>
            <Typography variant="h6" color="primary" fontWeight="bold">
              {overallAccuracy.percentage}%
            </Typography>
            <Typography variant="body2" color="text.secondary">
              ({overallAccuracy.accurate} accurate out of {overallAccuracy.total} scored leads)
            </Typography>
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            Accuracy based on: AI Score &gt;= 65 and Converted = 1, OR AI Score &lt; 65 and Converted = 0
          </Typography>
        </Box>
      )}

      {/* Debug Info - Remove this after testing */}
      <Box mb={2} p={1} bgcolor="yellow.50" borderRadius={1}>
        <Typography variant="caption" color="text.secondary">
          Debug: {Object.keys(scores).length} scored leads, {leads.filter(l => l.converted !== undefined).length} leads with conversion data
        </Typography>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox">
                <Checkbox
                  checked={selectedLeads.length === leads.length && leads.length > 0}
                  indeterminate={selectedLeads.length > 0 && selectedLeads.length < leads.length}
                  onChange={handleSelectAll}
                />
              </TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Company</TableCell>
              <TableCell>Industry</TableCell>
              <TableCell>Lead Source</TableCell>
              <TableCell>Quality</TableCell>
              <TableCell>Activity Score</TableCell>
              <TableCell>Last Activity</TableCell>
              <TableCell>AI Score</TableCell>
              <TableCell>Conversion Status</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {leads.map((lead) => (
              <TableRow key={lead.id} hover>
                <TableCell padding="checkbox">
                  <Checkbox
                    checked={selectedLeads.includes(lead.id)}
                    onChange={() => handleSelectLead(lead.id)}
                  />
                </TableCell>
                <TableCell>
                  <Box>
                    <Typography variant="subtitle2">{lead.name}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {lead.email}
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell>{lead.company}</TableCell>
                <TableCell>
                  <Chip label={lead.industry} size="small" />
                </TableCell>
                <TableCell>{lead.lead_source}</TableCell>
                <TableCell>
                  <Chip 
                    label={lead.lead_quality || 'Unknown'} 
                    size="small" 
                    color={lead.lead_quality === 'High' ? 'success' : lead.lead_quality === 'Medium' ? 'warning' : 'default'}
                  />
                </TableCell>
                <TableCell>
                  <Typography variant="body2">
                    {lead.activity_score || 0}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="caption" color="text.secondary">
                    {lead.last_activity || 'N/A'}
                  </Typography>
                </TableCell>
                <TableCell>
                  {scores[lead.id] ? (
                    <Tooltip title={
                      <Box>
                        <Typography variant="body2">AI Score: {scores[lead.id].score}/100</Typography>
                        {lead.converted !== undefined && (
                          <Typography variant="body2">Actual: {isLeadConverted(lead.converted) ? 'Converted' : 'Not Converted'}</Typography>
                        )}
                        <Typography variant="caption" color="text.secondary">
                          {scores[lead.id].explanation}
                        </Typography>
                        {scores[lead.id].prefilled_data && Object.keys(scores[lead.id].prefilled_data).length > 0 && (
                          <Box mt={1}>
                            <Typography variant="caption" fontWeight="bold" color="primary">
                              Prefilled Data:
                            </Typography>
                            {Object.entries(scores[lead.id].prefilled_data).map(([key, value]) => (
                              <Typography key={key} variant="caption" display="block">
                                {key}: {typeof value === 'object' ? JSON.stringify(value) : value}
                              </Typography>
                            ))}
                          </Box>
                        )}
                      </Box>
                    }>
                      <Box display="flex" alignItems="center" gap={0.5}>
                        <Chip
                          label={`${scores[lead.id].score}/100`}
                          color={getScoreColor(scores[lead.id].score)}
                          size="small"
                        />
                        {lead.converted !== undefined && scores[lead.id] && (
                          <Chip
                            label={
                              getScoreAccuracy(scores[lead.id].score, lead.converted) === 'accurate-high' ? '✓' :
                              getScoreAccuracy(scores[lead.id].score, lead.converted) === 'accurate-low' ? '✓' :
                              getScoreAccuracy(scores[lead.id].score, lead.converted) === 'overestimated' ? '↑' :
                              getScoreAccuracy(scores[lead.id].score, lead.converted) === 'underestimated' ? '↓' : ''
                            }
                            color={
                              getScoreAccuracy(scores[lead.id].score, lead.converted) === 'accurate-high' ? 'success' :
                              getScoreAccuracy(scores[lead.id].score, lead.converted) === 'accurate-low' ? 'success' :
                              getScoreAccuracy(scores[lead.id].score, lead.converted) === 'overestimated' ? 'warning' :
                              getScoreAccuracy(scores[lead.id].score, lead.converted) === 'underestimated' ? 'error' : 'default'
                            }
                            size="small"
                            sx={{ minWidth: '20px', height: '20px' }}
                          />
                        )}
                      </Box>
                    </Tooltip>
                  ) : (
                    <Typography variant="caption" color="text.secondary">
                      Not scored
                    </Typography>
                  )}
                </TableCell>
                <TableCell>
                  <Chip
                    label={isLeadConverted(lead.converted) ? 'Converted' : 'Not Converted'}
                    color={isLeadConverted(lead.converted) ? 'success' : 'default'}
                    size="small"
                    variant={isLeadConverted(lead.converted) ? 'filled' : 'outlined'}
                  />
                </TableCell>
                <TableCell>
                  <Tooltip title="View details">
                    <IconButton size="small">
                      <InfoIcon />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Box display="flex" justifyContent="center" mt={2}>
        <Pagination
          count={totalPages}
          page={currentPage}
          onChange={(e, newPage) => setCurrentPage(newPage)}
          color="primary"
        />
      </Box>
    </Box>
  );
};

export default LeadTable; 