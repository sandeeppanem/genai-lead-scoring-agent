import React, { useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Collapse,
  Divider,
  Grid,
  InputAdornment,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import {
  Bolt as BoltIcon,
  CheckCircle as CheckIcon,
  ExpandLess as ExpandLessIcon,
  ExpandMore as ExpandMoreIcon,
  Search as SearchIcon,
} from '@mui/icons-material';
import { confirmCommand, executeCommand } from '../services/api';

const examples = [
  'Show Pacific opportunities for Tires & Wheels.',
  'Show urgent quote requests.',
  'Score the selected opportunities.',
  'Compare observed win rates by sales channel.',
  'Mark the selected inquiry as reviewed.',
];

const humanize = (value) => String(value || '').replaceAll('_', ' ');
const formatScope = (value) => {
  if (typeof value === 'boolean') return value ? 'yes' : 'no';
  if (typeof value === 'number') return value.toLocaleString();
  return String(value);
};

const ResultPreview = ({ result }) => {
  if (!result) return null;
  if (!Array.isArray(result)) {
    return (
      <Box sx={{ bgcolor: 'grey.50', borderRadius: 2, p: 1.5 }}>
        {result.score !== undefined && (
          <Typography variant="h6">ML score {result.score}/100</Typography>
        )}
        {result.explanation && <Typography variant="body2">{result.explanation}</Typography>}
        {result.side_effects && <Typography variant="body2">{result.side_effects}</Typography>}
        {result.status && <Typography variant="body2">New status: {humanize(result.status)}</Typography>}
      </Box>
    );
  }
  if (!result.length) return <Typography color="text.secondary">No matching records.</Typography>;
  return (
    <Grid container spacing={1}>
      {result.map((item, index) => (
        <Grid item xs={12} sm={6} md={3} key={item.id || item.record_id || item.value || index}>
          <Box sx={{ bgcolor: 'grey.50', border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 1.25, height: '100%' }}>
            <Typography variant="subtitle2">
              {item.inquiry_text
                ? `Inquiry ${item.id}`
                : item.value || `Record ${item.record_id}`}
            </Typography>
            {item.opportunity_number && (
              <Typography variant="caption" color="text.secondary">Opportunity #{item.opportunity_number}</Typography>
            )}
            {item.inquiry_text && (
              <Typography variant="body2" sx={{ mt: 0.5 }}>{item.inquiry_text}</Typography>
            )}
            {item.supplies_group && <Typography variant="body2">{item.supplies_group}</Typography>}
            {item.region && <Typography variant="caption">{item.region} · {item.route_to_market}</Typography>}
            {item.score !== undefined && <Chip size="small" label={`ML ${item.score}/100`} sx={{ mt: 0.75 }} />}
            {item.win_rate !== undefined && (
              <Typography variant="body2">{item.win_rate}% win rate · {item.opportunities.toLocaleString()} records</Typography>
            )}
            {item.workflow_decision && (
              <Chip size="small" label={humanize(item.workflow_decision.action)} sx={{ mt: 0.75 }} />
            )}
          </Box>
        </Grid>
      ))}
    </Grid>
  );
};

const CRMCommandBar = ({ selectedRecordIds, selectedInquiryIds, onMutation }) => {
  const [command, setCommand] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [response, setResponse] = useState(null);
  const [expanded, setExpanded] = useState(true);

  const run = async (value = command) => {
    const text = value.trim();
    if (!text || loading) return;
    setCommand(text);
    setLoading(true);
    setError(null);
    try {
      setResponse(await executeCommand(text, selectedRecordIds, selectedInquiryIds));
      setExpanded(true);
    } catch (requestError) {
      console.error(requestError);
      setError(requestError.response?.data?.detail || 'The command could not be executed.');
    } finally {
      setLoading(false);
    }
  };

  const apply = async () => {
    if (!response?.confirmation_id) return;
    setLoading(true);
    setError(null);
    try {
      const confirmed = await confirmCommand(response.confirmation_id);
      setResponse(confirmed);
      onMutation?.();
    } catch (requestError) {
      console.error(requestError);
      setError(requestError.response?.data?.detail || 'The status change could not be applied.');
    } finally {
      setLoading(false);
    }
  };

  const selectionLabel = [
    selectedRecordIds.length ? `${selectedRecordIds.length} opportunities` : null,
    selectedInquiryIds.length ? `${selectedInquiryIds.length} inquiries` : null,
  ].filter(Boolean).join(' · ');

  return (
    <Paper
      elevation={0}
      sx={{
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 3,
        p: { xs: 2, md: 2.5 },
        mb: 3,
        background: 'linear-gradient(135deg, #ffffff 0%, #f4f7ff 100%)',
      }}
    >
      <Box display="flex" alignItems="center" gap={1} mb={1.5}>
        <Box sx={{ bgcolor: 'primary.main', color: 'white', borderRadius: 2, p: 0.75, display: 'flex' }}>
          <BoltIcon fontSize="small" />
        </Box>
        <Box flexGrow={1}>
          <Typography variant="subtitle1" fontWeight={700}>CRM command bar</Typography>
          <Typography variant="caption" color="text.secondary">
            Natural language is mapped to six approved, validated application tools.
          </Typography>
        </Box>
        {selectionLabel && <Chip size="small" color="primary" variant="outlined" label={`Selected: ${selectionLabel}`} />}
      </Box>

      <Box display="flex" gap={1}>
        <TextField
          fullWidth
          size="small"
          value={command}
          placeholder="Try: Explain the score for record 12"
          onChange={(event) => setCommand(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault();
              run();
            }
          }}
          InputProps={{
            startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment>,
          }}
        />
        <Button
          variant="contained"
          onClick={() => run()}
          disabled={loading || !command.trim()}
          sx={{ minWidth: 100 }}
        >
          {loading ? <CircularProgress size={20} color="inherit" /> : 'Run'}
        </Button>
      </Box>
      <Stack direction="row" spacing={1} mt={1.25} useFlexGap flexWrap="wrap">
        {examples.map((example) => (
          <Chip key={example} size="small" label={example} onClick={() => run(example)} variant="outlined" />
        ))}
      </Stack>

      {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
      {response && (
        <Box mt={2}>
          <Divider sx={{ mb: 1.5 }} />
          <Box display="flex" alignItems="center" gap={1}>
            <Chip
              size="small"
              color={response.provider_mode === 'live' ? 'success' : 'warning'}
              label={response.provider_mode === 'live' ? `Live Jev · ${response.model}` : 'Demo decision provider'}
            />
            {response.tool && <Chip size="small" label={humanize(response.tool)} />}
            <Chip size="small" variant="outlined" label={`Confidence ${Math.round(response.confidence * 100)}%`} />
            <Button
              size="small"
              sx={{ ml: 'auto' }}
              endIcon={expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              onClick={() => setExpanded((value) => !value)}
            >
              Details
            </Button>
          </Box>
          <Typography variant="body1" fontWeight={600} mt={1}>{response.message}</Typography>
          <Collapse in={expanded}>
            <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" mt={1.25} mb={1.5}>
              {Object.entries(response.scope || {}).map(([key, value]) => (
                <Chip key={key} size="small" variant="outlined" label={`${humanize(key)}: ${formatScope(value)}`} />
              ))}
              {Object.keys(response.interpreted_arguments || {}).length > 0 && (
                <Chip
                  size="small"
                  variant="outlined"
                  label={`Interpreted: ${JSON.stringify(response.interpreted_arguments)}`}
                />
              )}
            </Stack>
            <ResultPreview result={response.result} />
          </Collapse>
          {response.requires_confirmation && (
            <Alert
              severity="warning"
              sx={{ mt: 1.5 }}
              action={(
                <Button color="warning" size="small" startIcon={<CheckIcon />} onClick={apply} disabled={loading}>
                  Confirm change
                </Button>
              )}
            >
              This command changes workflow data. Review the preview before confirming.
            </Alert>
          )}
        </Box>
      )}
    </Paper>
  );
};

export default CRMCommandBar;
