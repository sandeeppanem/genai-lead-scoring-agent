import React, { useState } from 'react';
import {
  Box,
  TextField,
  Button,
  Typography,
  Alert,
  Paper,
  CircularProgress
} from '@mui/material';
import api from '../services/api';

const LeadForm = ({ onLeadSubmitted }) => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    company: '',
    job_title: '',
    industry: '',
    phone: '',
    website: '',
    message: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setResult(null);
    
    try {
      const response = await api.post('/leads/web-form', {
        ...formData,
        lead_source: 'Web Form'
      });
      
      const data = response.data;
      setResult(data);
      
      if (onLeadSubmitted) {
        onLeadSubmitted(data);
      }
      
      // Reset form after successful submission
      setTimeout(() => {
        setFormData({
          name: '', email: '', company: '', job_title: '',
          industry: '', phone: '', website: '', message: ''
        });
        setResult(null);
      }, 5000);
    } catch (error) {
      console.error('Error submitting form:', error);
      setError('Failed to submit lead. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Paper sx={{ p: 3, maxWidth: 600, mx: 'auto' }}>
      <Typography variant="h5" gutterBottom>
        Contact Us (Active Lead)
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Submit your information and we'll automatically score and route your lead
      </Typography>
      
      <Box component="form" onSubmit={handleSubmit}>
        <TextField
          label="Name *"
          value={formData.name}
          onChange={(e) => setFormData({...formData, name: e.target.value})}
          required
          fullWidth
          margin="normal"
        />
        
        <TextField
          label="Email *"
          type="email"
          value={formData.email}
          onChange={(e) => setFormData({...formData, email: e.target.value})}
          required
          fullWidth
          margin="normal"
        />
        
        <TextField
          label="Company *"
          value={formData.company}
          onChange={(e) => setFormData({...formData, company: e.target.value})}
          required
          fullWidth
          margin="normal"
        />
        
        <TextField
          label="Job Title"
          value={formData.job_title}
          onChange={(e) => setFormData({...formData, job_title: e.target.value})}
          fullWidth
          margin="normal"
        />
        
        <TextField
          label="Industry"
          value={formData.industry}
          onChange={(e) => setFormData({...formData, industry: e.target.value})}
          fullWidth
          margin="normal"
        />
        
        <TextField
          label="Phone"
          value={formData.phone}
          onChange={(e) => setFormData({...formData, phone: e.target.value})}
          fullWidth
          margin="normal"
        />
        
        <TextField
          label="Website"
          value={formData.website}
          onChange={(e) => setFormData({...formData, website: e.target.value})}
          fullWidth
          margin="normal"
        />
        
        <TextField
          label="Message"
          value={formData.message}
          onChange={(e) => setFormData({...formData, message: e.target.value})}
          multiline
          rows={4}
          fullWidth
          margin="normal"
        />
        
        <Button
          type="submit"
          variant="contained"
          disabled={submitting}
          fullWidth
          sx={{ mt: 2 }}
          startIcon={submitting ? <CircularProgress size={20} /> : null}
        >
          {submitting ? 'Processing...' : 'Submit Lead'}
        </Button>
        
        {error && (
          <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}
        
        {result && (
          <Box sx={{ mt: 2 }}>
            <Alert severity="success" sx={{ mb: 2 }}>
              Lead processed successfully!
            </Alert>
            <Box sx={{ p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
              <Typography variant="subtitle2" gutterBottom>
                Lead Score: <strong>{result.score}/100</strong>
              </Typography>
              {result.routing && (
                <>
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    Next Action: <strong>{result.routing.next_action === 'active_outreach' ? 'Active Outreach' : 'Nurture Campaign'}</strong>
                  </Typography>
                  <Typography variant="body2">
                    Priority: <strong>{result.routing.priority}</strong>
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    Strategy: {result.routing.strategy}
                  </Typography>
                </>
              )}
              {result.email && (
                <Box sx={{ mt: 2, p: 2, bgcolor: 'white', borderRadius: 1 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Generated Email:
                  </Typography>
                  <Typography variant="caption" display="block" sx={{ fontWeight: 'bold' }}>
                    Subject: {result.email.subject}
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 1, whiteSpace: 'pre-wrap' }}>
                    {result.email.body}
                  </Typography>
                </Box>
              )}
            </Box>
          </Box>
        )}
      </Box>
    </Paper>
  );
};

export default LeadForm;

