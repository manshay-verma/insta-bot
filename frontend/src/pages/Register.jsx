import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../services/api';
import { User, Lock, Mail, Loader2, AlertCircle, CheckCircle } from 'lucide-react';

const Register = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const navigate = useNavigate();

  const getErrorMessage = (err) => {
    const data = err?.response?.data;
    if (!data) return err?.message || 'Network error. Is the backend running on http://localhost:8000 ?';

    if (typeof data === 'string') return data;
    if (typeof data?.detail === 'string') return data.detail;
    if (Array.isArray(data?.detail)) return data.detail.join(', ');

    // DRF serializer errors often look like: { field: ["msg1", "msg2"] }
    if (typeof data === 'object') {
      const parts = [];
      for (const [key, value] of Object.entries(data)) {
        if (Array.isArray(value)) parts.push(`${key}: ${value.join(', ')}`);
        else if (typeof value === 'string') parts.push(`${key}: ${value}`);
        else if (value && typeof value === 'object') parts.push(`${key}: ${JSON.stringify(value)}`);
      }
      if (parts.length) return parts.join(' | ');
    }

    return 'An error occurred during registration. Please try again.';
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      setLoading(false);
      return;
    }

    try {
      // Assuming endpoint exists for registration
      await api.post('/register/', {
        username,
        email,
        password,
      });

      setSuccess(true);
      setTimeout(() => navigate('/login'), 2000);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container" style={{ 
      minHeight: '100vh', 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center' 
    }}>
      <div className="glass" style={{ 
        width: '100%', 
        maxWidth: '450px', 
        padding: '2.5rem',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
      }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h2 style={{ fontSize: '1.875rem', fontWeight: 'bold', color: 'hsl(var(--primary))' }}>
            Get Started
          </h2>
          <p style={{ color: 'hsl(var(--muted-foreground))', marginTop: '0.5rem' }}>
            Create your account to start managing bots
          </p>
        </div>

        {error && (
          <div style={{ 
            backgroundColor: 'rgba(220, 38, 38, 0.1)', 
            border: '1px solid rgba(220, 38, 38, 0.2)',
            padding: '0.75rem',
            borderRadius: 'var(--radius)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            color: '#ef4444',
            marginBottom: '1.5rem',
            fontSize: '0.875rem'
          }}>
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div style={{ 
            backgroundColor: 'rgba(16, 185, 129, 0.1)', 
            border: '1px solid rgba(16, 185, 129, 0.2)',
            padding: '0.75rem',
            borderRadius: 'var(--radius)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            color: '#10b981',
            marginBottom: '1.5rem',
            fontSize: '0.875rem'
          }}>
            <CheckCircle size={18} />
            <span>Success! Redirecting to login...</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.25rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', marginBottom: '0.5rem', color: 'hsl(var(--muted-foreground))' }}>
                Username
              </label>
              <div style={{ position: 'relative' }}>
                <User style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'hsl(var(--muted-foreground))' }} size={18} />
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="InstaUser"
                  style={{
                    width: '100%',
                    padding: '0.625rem 0.75rem 0.625rem 2.5rem',
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: 'var(--radius)',
                    color: 'white',
                    outline: 'none',
                  }}
                />
              </div>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', marginBottom: '0.5rem', color: 'hsl(var(--muted-foreground))' }}>
                Email
              </label>
              <div style={{ position: 'relative' }}>
                <Mail style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'hsl(var(--muted-foreground))' }} size={18} />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="john@example.com"
                  style={{
                    width: '100%',
                    padding: '0.625rem 0.75rem 0.625rem 2.5rem',
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: 'var(--radius)',
                    color: 'white',
                    outline: 'none',
                  }}
                />
              </div>
            </div>
          </div>

          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ display: 'block', fontSize: '0.875rem', marginBottom: '0.5rem', color: 'hsl(var(--muted-foreground))' }}>
              Password
            </label>
            <div style={{ position: 'relative' }}>
              <Lock style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'hsl(var(--muted-foreground))' }} size={18} />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                style={{
                  width: '100%',
                  padding: '0.625rem 0.75rem 0.625rem 2.5rem',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: 'var(--radius)',
                  color: 'white',
                  outline: 'none',
                }}
              />
            </div>
          </div>

          <div style={{ marginBottom: '2rem' }}>
            <label style={{ display: 'block', fontSize: '0.875rem', marginBottom: '0.5rem', color: 'hsl(var(--muted-foreground))' }}>
              Confirm Password
            </label>
            <div style={{ position: 'relative' }}>
              <Lock style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'hsl(var(--muted-foreground))' }} size={18} />
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                style={{
                  width: '100%',
                  padding: '0.625rem 0.75rem 0.625rem 2.5rem',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: 'var(--radius)',
                  color: 'white',
                  outline: 'none',
                }}
              />
            </div>
          </div>

          <button 
            type="submit" 
            disabled={loading}
            className="btn btn-primary" 
            style={{ width: '100%', padding: '0.75rem' }}
          >
            {loading ? (
              <Loader2 className="animate-spin" size={20} />
            ) : (
              'Create Account'
            )}
          </button>
        </form>

        <div style={{ marginTop: '1.5rem', textAlign: 'center', fontSize: '0.875rem', color: 'hsl(var(--muted-foreground))' }}>
          Already have an account? <Link to="/login" style={{ color: 'hsl(var(--primary))', textDecoration: 'none' }}>Log in</Link>
        </div>
      </div>
    </div>
  );
};

export default Register;
