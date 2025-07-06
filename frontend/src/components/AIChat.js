import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  List,
  ListItem,
  ListItemText,
  Divider,
  CircularProgress,
  Alert,
  Chip,
  Avatar,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  Send as SendIcon,
  Clear as ClearIcon,
  SmartToy as AIIcon,
  Person as PersonIcon
} from '@mui/icons-material';
import { askQuestion } from '../services/api';

const AIChat = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Add welcome message
  useEffect(() => {
    setMessages([
      {
        id: 1,
        type: 'ai',
        content: 'Hello! I\'m your AI Lead Scoring Assistant. Ask me anything about your leads, such as:\n\n• "Which leads have the highest potential?"\n• "What are the top industries in our lead database?"\n• "Show me leads from the technology sector"\n• "What lead sources are performing best?"\n• "Analyze our lead quality trends"',
        timestamp: new Date()
      }
    ]);
  }, []);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: input.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setError(null);

    try {
      const response = await askQuestion(input.trim());
      
      const aiMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: response.answer,
        sources: response.sources || [],
        timestamp: new Date()
      };

      setMessages(prev => [...prev, aiMessage]);
    } catch (err) {
      setError('Failed to get AI response. Please try again.');
      console.error('Error asking question:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const clearChat = () => {
    setMessages([
      {
        id: Date.now(),
        type: 'ai',
        content: 'Chat cleared. How can I help you with your leads today?',
        timestamp: new Date()
      }
    ]);
    setError(null);
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const renderMessage = (message) => {
    const isAI = message.type === 'ai';
    
    return (
      <ListItem
        key={message.id}
        sx={{
          flexDirection: 'column',
          alignItems: 'flex-start',
          py: 2
        }}
      >
        <Box display="flex" alignItems="center" width="100%" mb={1}>
          <Avatar
            sx={{
              bgcolor: isAI ? 'primary.main' : 'grey.500',
              width: 32,
              height: 32,
              mr: 1
            }}
          >
            {isAI ? <AIIcon /> : <PersonIcon />}
          </Avatar>
          <Typography variant="subtitle2" color="text.secondary">
            {isAI ? 'AI Assistant' : 'You'}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ ml: 'auto' }}>
            {formatTimestamp(message.timestamp)}
          </Typography>
        </Box>
        
        <Box
          sx={{
            ml: 4,
            width: '100%',
            '& pre': {
              whiteSpace: 'pre-wrap',
              fontFamily: 'inherit'
            }
          }}
        >
          <Typography
            component="div"
            sx={{
              whiteSpace: 'pre-wrap',
              lineHeight: 1.6
            }}
          >
            {message.content}
          </Typography>
          
          {message.sources && message.sources.length > 0 && (
            <Box mt={1}>
              <Typography variant="caption" color="text.secondary">
                Referenced leads: 
              </Typography>
              <Box display="flex" gap={0.5} mt={0.5} flexWrap="wrap">
                {message.sources.map((sourceId, index) => (
                  <Chip
                    key={index}
                    label={`Lead #${sourceId}`}
                    size="small"
                    variant="outlined"
                  />
                ))}
              </Box>
            </Box>
          )}
        </Box>
      </ListItem>
    );
  };

  return (
    <Paper sx={{ height: '600px', display: 'flex', flexDirection: 'column' }}>
      <Box
        sx={{
          p: 2,
          borderBottom: 1,
          borderColor: 'divider',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}
      >
        <Typography variant="h6">
          AI Lead Assistant
        </Typography>
        <Tooltip title="Clear chat">
          <IconButton onClick={clearChat} size="small">
            <ClearIcon />
          </IconButton>
        </Tooltip>
      </Box>

      <Box
        sx={{
          flex: 1,
          overflow: 'auto',
          p: 1
        }}
      >
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <List sx={{ p: 0 }}>
          {messages.map(renderMessage)}
          
          {loading && (
            <ListItem sx={{ flexDirection: 'column', alignItems: 'flex-start', py: 2 }}>
              <Box display="flex" alignItems="center" width="100%" mb={1}>
                <Avatar sx={{ bgcolor: 'primary.main', width: 32, height: 32, mr: 1 }}>
                  <AIIcon />
                </Avatar>
                <Typography variant="subtitle2" color="text.secondary">
                  AI Assistant
                </Typography>
                <CircularProgress size={16} sx={{ ml: 1 }} />
              </Box>
              <Box ml={4}>
                <Typography variant="body2" color="text.secondary">
                  Thinking...
                </Typography>
              </Box>
            </ListItem>
          )}
        </List>
        <div ref={messagesEndRef} />
      </Box>

      <Box
        sx={{
          p: 2,
          borderTop: 1,
          borderColor: 'divider'
        }}
      >
        <Box display="flex" gap={1}>
          <TextField
            fullWidth
            multiline
            maxRows={4}
            placeholder="Ask me about your leads..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={loading}
            variant="outlined"
            size="small"
          />
          <Button
            variant="contained"
            onClick={handleSend}
            disabled={!input.trim() || loading}
            sx={{ minWidth: 'auto', px: 2 }}
          >
            <SendIcon />
          </Button>
        </Box>
      </Box>
    </Paper>
  );
};

export default AIChat; 