import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  CircularProgress,
  Divider,
  FormControl,
  Grid,
  InputLabel,
  LinearProgress,
  List,
  ListItemButton,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import {
  Add as AddIcon,
  ArrowForward as ArrowIcon,
  Psychology as PsychologyIcon,
  Refresh as RefreshIcon,
  Rule as RuleIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material';
import { createInquiry, getActionQueue, updateInquiryStatus } from '../services/api';

const actions = [
  'quote_request', 'qualification', 'nurture', 'support', 'do_not_contact', 'human_review',
];
const statuses = ['new', 'in_review', 'reviewed', 'resolved'];
const examples = [
  'Please quote 200 replacement batteries; we need delivery next month.',
  'We are comparing tire suppliers for next year.',
  'The car electronics delivered to us are defective.',
  'Can you confirm which vehicle models these parts fit?',
  'Please stop contacting me.',
];
const labels = {
  quote_request: 'Quote request',
  qualification: 'Qualification',
  nurture: 'Nurture',
  support: 'Support',
  do_not_contact: 'Do not contact',
  human_review: 'Human review',
  in_review: 'In review',
};
const actionColor = {
  quote_request: 'success', qualification: 'info', nurture: 'secondary', support: 'warning', do_not_contact: 'error', human_review: 'default',
};
const probability = (value) => `${Math.round((value || 0) * 100)}%`;
const label = (value) => labels[value] || String(value || '').replaceAll('_', ' ');

const DecisionCard = ({ icon, eyebrow, title, color, children }) => (
  <Card variant="outlined" sx={{ height: '100%', borderTop: '4px solid', borderTopColor: color }}>
    <CardContent>
      <Box display="flex" alignItems="center" gap={1} mb={1} color={color}>
        {icon}
        <Typography variant="overline" fontWeight={800}>{eyebrow}</Typography>
      </Box>
      <Typography variant="h6" gutterBottom>{title}</Typography>
      {children}
    </CardContent>
  </Card>
);

const LeadFlowInbox = ({ selectedIds, onSelectionChange, refreshToken = 0 }) => {
  const [items, setItems] = useState([]);
  const [counts, setCounts] = useState({});
  const [activeId, setActiveId] = useState(null);
  const [action, setAction] = useState('');
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [composerOpen, setComposerOpen] = useState(true);
  const [recordId, setRecordId] = useState('1');
  const [inquiryText, setInquiryText] = useState(examples[0]);

  const active = useMemo(
    () => items.find((item) => item.id === activeId) || items[0] || null,
    [items, activeId],
  );

  const load = async (overrides = {}) => {
    const nextAction = Object.prototype.hasOwnProperty.call(overrides, 'action')
      ? overrides.action
      : action;
    const nextStatus = Object.prototype.hasOwnProperty.call(overrides, 'status')
      ? overrides.status
      : status;
    setLoading(true);
    setError(null);
    try {
      const result = await getActionQueue({ action: nextAction || null, status: nextStatus || null });
      setItems(result.items);
      setCounts(result.counts || {});
      setActiveId((current) => (result.items.some((item) => item.id === current)
        ? current
        : result.items[0]?.id || null));
      onSelectionChange(selectedIds.filter((id) => result.items.some((item) => item.id === id)));
    } catch (requestError) {
      console.error(requestError);
      setError(requestError.response?.data?.detail || 'Unable to load the LeadFlow inbox.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [action, status, refreshToken]);

  const create = async () => {
    if (!recordId || !inquiryText.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const created = await createInquiry(Number(recordId), inquiryText.trim());
      setAction('');
      setStatus('');
      await load({ action: '', status: '' });
      setActiveId(created.id);
      setComposerOpen(false);
    } catch (requestError) {
      console.error(requestError);
      setError(requestError.response?.data?.detail || 'The inquiry could not be classified.');
    } finally {
      setSaving(false);
    }
  };

  const changeStatus = async (newStatus) => {
    if (!active) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await updateInquiryStatus(active.id, newStatus);
      setItems((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (requestError) {
      console.error(requestError);
      setError(requestError.response?.data?.detail || 'The workflow status could not be updated.');
    } finally {
      setSaving(false);
    }
  };

  const toggleSelected = (id) => onSelectionChange(
    selectedIds.includes(id) ? selectedIds.filter((value) => value !== id) : [...selectedIds, id],
  );

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="flex-start" gap={2} mb={2.5}>
        <Box>
          <Typography variant="h4" fontWeight={750}>LeadFlow action inbox</Typography>
          <Typography color="text.secondary">
            Turn customer inquiries into inspectable, policy-owned work queues.
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setComposerOpen((value) => !value)}>
          Add inquiry
        </Button>
      </Box>

      {composerOpen && (
        <Paper variant="outlined" sx={{ p: 2.5, mb: 2.5, borderRadius: 3 }}>
          <Grid container spacing={2} alignItems="flex-start">
            <Grid item xs={12} md={2}>
              <TextField
                fullWidth
                type="number"
                label="Opportunity record ID"
                value={recordId}
                onChange={(event) => setRecordId(event.target.value)}
                inputProps={{ min: 1 }}
              />
            </Grid>
            <Grid item xs={12} md={8}>
              <TextField
                fullWidth
                multiline
                minRows={2}
                label="Customer inquiry"
                value={inquiryText}
                onChange={(event) => setInquiryText(event.target.value)}
                helperText="Use non-sensitive demo text. The historical dataset itself contains no emails or inquiry text."
              />
            </Grid>
            <Grid item xs={12} md={2}>
              <Button fullWidth variant="contained" onClick={create} disabled={saving || inquiryText.trim().length < 4} sx={{ height: 56 }}>
                {saving ? <CircularProgress size={20} color="inherit" /> : 'Classify & route'}
              </Button>
            </Grid>
          </Grid>
          <Stack direction="row" spacing={1} mt={1.5} useFlexGap flexWrap="wrap">
            {examples.map((example, index) => (
              <Chip key={example} size="small" variant="outlined" label={`Example ${index + 1}`} onClick={() => setInquiryText(example)} />
            ))}
          </Stack>
        </Paper>
      )}

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Grid container spacing={1.25} mb={2.5}>
        {actions.map((queue) => (
          <Grid item xs={6} sm={4} md={2} key={queue}>
            <Paper
              variant="outlined"
              onClick={() => setAction(action === queue ? '' : queue)}
              sx={{
                p: 1.5,
                cursor: 'pointer',
                borderColor: action === queue ? 'primary.main' : 'divider',
                bgcolor: action === queue ? 'primary.50' : 'background.paper',
              }}
            >
              <Typography variant="h5" fontWeight={750}>{counts[queue] || 0}</Typography>
              <Typography variant="caption" color="text.secondary">{label(queue)}</Typography>
            </Paper>
          </Grid>
        ))}
      </Grid>

      <Box display="flex" gap={1.5} mb={2} alignItems="center">
        <FormControl size="small" sx={{ minWidth: 190 }}>
          <InputLabel>Action queue</InputLabel>
          <Select value={action} label="Action queue" onChange={(event) => setAction(event.target.value)}>
            <MenuItem value="">All queues</MenuItem>
            {actions.map((value) => <MenuItem key={value} value={value}>{label(value)}</MenuItem>)}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel>Status</InputLabel>
          <Select value={status} label="Status" onChange={(event) => setStatus(event.target.value)}>
            <MenuItem value="">All statuses</MenuItem>
            {statuses.map((value) => <MenuItem key={value} value={value}>{label(value)}</MenuItem>)}
          </Select>
        </FormControl>
        <Button startIcon={<RefreshIcon />} onClick={load}>Refresh</Button>
        <Typography variant="body2" color="text.secondary" sx={{ ml: 'auto' }}>
          {items.length} shown · {selectedIds.length} selected
        </Typography>
      </Box>

      {loading && <LinearProgress sx={{ mb: 1 }} />}
      <Grid container spacing={2.5}>
        <Grid item xs={12} md={4}>
          <Paper variant="outlined" sx={{ borderRadius: 3, overflow: 'hidden', minHeight: 520 }}>
            {!items.length && !loading ? (
              <Box textAlign="center" p={5}>
                <Typography variant="h6">Your inbox is empty</Typography>
                <Typography variant="body2" color="text.secondary" mt={1}>
                  Add an example inquiry to see classification, policy routing, and ML context together.
                </Typography>
              </Box>
            ) : (
              <List disablePadding>
                {items.map((item) => (
                  <React.Fragment key={item.id}>
                    <ListItemButton
                      selected={active?.id === item.id}
                      onClick={() => setActiveId(item.id)}
                      sx={{ alignItems: 'flex-start', py: 1.5 }}
                    >
                      <Checkbox
                        size="small"
                        edge="start"
                        checked={selectedIds.includes(item.id)}
                        onClick={(event) => event.stopPropagation()}
                        onChange={() => toggleSelected(item.id)}
                      />
                      <Box minWidth={0} flexGrow={1}>
                        <Box display="flex" gap={0.75} alignItems="center" mb={0.5}>
                          <Chip size="small" color={actionColor[item.workflow_decision.action]} label={label(item.workflow_decision.action)} />
                          <Chip size="small" variant="outlined" label={item.workflow_decision.priority} />
                        </Box>
                        <Typography variant="body2" fontWeight={650} noWrap>{item.inquiry_text}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          Inquiry {item.id} · Record {item.record_id} · {label(item.status)}
                        </Typography>
                      </Box>
                      <ArrowIcon fontSize="small" sx={{ mt: 1, color: 'text.disabled' }} />
                    </ListItemButton>
                    <Divider />
                  </React.Fragment>
                ))}
              </List>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={8}>
          {active ? (
            <Paper variant="outlined" sx={{ borderRadius: 3, p: { xs: 2, md: 3 } }}>
              <Box display="flex" justifyContent="space-between" gap={2} alignItems="flex-start">
                <Box>
                  <Typography variant="overline" color="text.secondary">Original customer inquiry</Typography>
                  <Typography variant="h6" sx={{ maxWidth: 760 }}>“{active.inquiry_text}”</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Linked to opportunity #{active.opportunity_number} · Record {active.record_id} · {active.opportunity.region}
                  </Typography>
                </Box>
                <FormControl size="small" sx={{ minWidth: 145 }}>
                  <InputLabel>Status</InputLabel>
                  <Select value={active.status} label="Status" disabled={saving} onChange={(event) => changeStatus(event.target.value)}>
                    {statuses.map((value) => <MenuItem key={value} value={value}>{label(value)}</MenuItem>)}
                  </Select>
                </FormControl>
              </Box>

              {active.semantic_decision.provider_mode === 'demo' && (
                <Alert severity="warning" sx={{ mt: 2 }}>
                  Demo decision provider — these are deterministic offline judgments, not live Jev results.
                </Alert>
              )}
              {active.workflow_decision.disagreement && (
                <Alert severity="info" sx={{ mt: 2 }}>{active.workflow_decision.disagreement}</Alert>
              )}

              <Grid container spacing={2} mt={0.25}>
                <Grid item xs={12} md={4}>
                  <DecisionCard icon={<SpeedIcon />} eyebrow="Calibrated ML" title={`${active.ml_score.score}/100`} color="#1463ff">
                    <Typography variant="body2" color="text.secondary">
                      {probability(active.ml_score.probability)} predicted win probability
                    </Typography>
                    <Chip size="small" sx={{ mt: 1 }} label={label(active.ml_score.routing.next_action)} />
                  </DecisionCard>
                </Grid>
                <Grid item xs={12} md={4}>
                  <DecisionCard icon={<PsychologyIcon />} eyebrow="Semantic judgment" title={label(active.semantic_decision.main_intent.value)} color="#7c3aed">
                    <Typography variant="body2" color="text.secondary">
                      {probability(active.semantic_decision.main_intent.confidence)} classification confidence
                    </Typography>
                    <Typography variant="caption" display="block" mt={1}>
                      Intent probability is not conversion probability.
                    </Typography>
                  </DecisionCard>
                </Grid>
                <Grid item xs={12} md={4}>
                  <DecisionCard icon={<RuleIcon />} eyebrow="Workflow policy" title={label(active.workflow_decision.action)} color="#087f5b">
                    <Typography variant="body2" color="text.secondary">
                      {active.workflow_decision.priority} priority · outreach disabled
                    </Typography>
                    <Typography variant="caption" display="block" mt={1}>{active.workflow_decision.policy_version}</Typography>
                  </DecisionCard>
                </Grid>
              </Grid>

              <Paper sx={{ bgcolor: 'grey.50', p: 2, mt: 2 }} elevation={0}>
                <Typography variant="subtitle2" gutterBottom>Why this action</Typography>
                <Typography variant="body2">{active.workflow_decision.reason}</Typography>
              </Paper>

              <Typography variant="subtitle1" fontWeight={700} mt={2.5} mb={1}>Decision inspector</Typography>
              <Grid container spacing={1.5}>
                {[
                  ['Product interest', active.semantic_decision.product_interest.value, probability(active.semantic_decision.product_interest.confidence)],
                  ['Purchase timeline', label(active.semantic_decision.purchase_timeline.value), probability(active.semantic_decision.purchase_timeline.confidence)],
                  ['Explicit urgency', probability(active.semantic_decision.explicit_urgency.probability), 'Noul/boolean probability'],
                  ['Concrete requirement', probability(active.semantic_decision.concrete_purchase_requirement.probability), 'Noul/boolean probability'],
                  ['Qualification missing', probability(active.semantic_decision.qualification_information_missing.probability), 'Noul/boolean probability'],
                  ['Decision model', active.semantic_decision.model, active.semantic_decision.cache_hit ? 'semantic cache hit' : active.semantic_decision.question_version],
                ].map(([title, value, note]) => (
                  <Grid item xs={12} sm={6} md={4} key={title}>
                    <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 1.5, height: '100%' }}>
                      <Typography variant="caption" color="text.secondary">{title}</Typography>
                      <Typography variant="body1" fontWeight={650}>{value}</Typography>
                      <Typography variant="caption" color="text.secondary">{note}</Typography>
                    </Box>
                  </Grid>
                ))}
              </Grid>

              {!!active.workflow_decision.uncertainty.length && (
                <Alert severity="warning" sx={{ mt: 2 }}>
                  {active.workflow_decision.uncertainty.join(' · ')}
                </Alert>
              )}
            </Paper>
          ) : (
            <Paper variant="outlined" sx={{ borderRadius: 3, p: 6, textAlign: 'center', minHeight: 520 }}>
              <Typography variant="h6">Select an inquiry to inspect its decision trail.</Typography>
            </Paper>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};

export default LeadFlowInbox;
