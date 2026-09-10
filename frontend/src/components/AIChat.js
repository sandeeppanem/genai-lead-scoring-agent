import React, { useEffect, useRef, useState } from 'react';
import {
  Alert,
  Avatar,
  Box,
  Button,
  Chip,
  CircularProgress,
  List,
  ListItem,
  Paper,
  TextField,
  Typography,
} from '@mui/material';
import {
  Analytics as AnalyticsIcon,
  Person as PersonIcon,
  Send as SendIcon,
} from '@mui/icons-material';
import { askQuestion } from '../services/api';

const AIChat = () => {
  const [messages, setMessages] = useState([{
    id: 1,
    role: 'assistant',
    content: 'Ask for verified win-rate aggregations by region, route to market, product group, or competitor status. You can also ask for the highest-value opportunities.',
  }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const send = async () => {
    const question = input.trim();
    if (!question || loading) return;
    setMessages((items) => [...items, { id: Date.now(), role: 'user', content: question }]);
    setInput('');
    setLoading(true);
    setError(null);
    try {
      const result = await askQuestion(question);
      setMessages((items) => [...items, {
        id: Date.now() + 1,
        role: 'assistant',
        content: result.answer,
        population: result.population_size,
        filters: result.filters,
        timeWindow: result.time_window,
        sources: result.sources,
      }]);
    } catch (requestError) {
      console.error(requestError);
      setError('The analytics request failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Paper sx={{ maxWidth: 900, mx: 'auto', height: 650, display: 'flex', flexDirection: 'column' }}>
      <Box p={2} borderBottom={1} borderColor="divider">
        <Typography variant="h6">Verified conversational analytics</Typography>
        <Typography variant="caption" color="text.secondary">
          Approved aggregation tools execute over all matching records; the response reports scope.
        </Typography>
      </Box>
      <Box sx={{ flexGrow: 1, overflow: 'auto', p: 2 }}>
        {error && <Alert severity="error">{error}</Alert>}
        <List>
          {messages.map((message) => (
            <ListItem key={message.id} alignItems="flex-start">
              <Avatar sx={{ mr: 2, bgcolor: message.role === 'assistant' ? 'primary.main' : 'grey.600' }}>
                {message.role === 'assistant' ? <AnalyticsIcon /> : <PersonIcon />}
              </Avatar>
              <Box>
                <Typography sx={{ whiteSpace: 'pre-wrap' }}>{message.content}</Typography>
                {message.population !== undefined && (
                  <Box mt={1} display="flex" gap={1} flexWrap="wrap">
                    <Chip size="small" label={'Population: ' + message.population.toLocaleString()} />
                    <Chip size="small" label={message.timeWindow} variant="outlined" />
                    {Object.entries(message.filters || {}).map(([key, value]) => (
                      <Chip key={key} size="small" label={key + ': ' + value} variant="outlined" />
                    ))}
                  </Box>
                )}
              </Box>
            </ListItem>
          ))}
          {loading && <CircularProgress size={22} />}
          <div ref={endRef} />
        </List>
      </Box>
      <Box p={2} borderTop={1} borderColor="divider" display="flex" gap={1}>
        <TextField
          fullWidth
          size="small"
          value={input}
          placeholder="Which routes to market have the best observed win rate?"
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault();
              send();
            }
          }}
        />
        <Button variant="contained" onClick={send} disabled={loading || !input.trim()}>
          <SendIcon />
        </Button>
      </Box>
    </Paper>
  );
};

export default AIChat;
