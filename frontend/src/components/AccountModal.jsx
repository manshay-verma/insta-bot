import React, { useState } from 'react';
import { X, User, Lock, Globe, Loader2, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ThemedSelect from './ThemedSelect';

const AccountModal = ({ isOpen, onClose, onSave, mode = 'add', initialData = {} }) => {
  const [formData, setFormData] = useState({
    username: initialData.username || '',
    password: '',
    proxy: initialData.proxy || '',
    status: initialData.status || 'active',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      await onSave(formData);
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save account. Please check your inputs.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem'
      }}>
        {/* Backdrop */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          style={{
            position: 'absolute',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            backdropFilter: 'blur(4px)'
          }}
        />

        {/* Modal Content */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: 20 }}
          className="glass"
          style={{
            width: '100%',
            maxWidth: '500px',
            position: 'relative',
            padding: '2.5rem',
            backgroundColor: 'hsl(var(--background))',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
            border: '1px solid rgba(255, 255, 255, 0.1)'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>
              {mode === 'add' ? 'Add New Account' : 'Edit Account'}
            </h2>
            <button onClick={onClose} className="btn" style={{ padding: '4px', minHeight: 'unset' }}>
              <X size={24} />
            </button>
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

          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ display: 'block', fontSize: '0.875rem', marginBottom: '0.5rem', color: 'hsl(var(--muted-foreground))' }}>
                Instagram Username
              </label>
              <div style={{ position: 'relative' }}>
                <User style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'hsl(var(--muted-foreground))' }} size={18} />
                <input
                  type="text"
                  required
                  value={formData.username}
                  onChange={(e) => setFormData({...formData, username: e.target.value})}
                  placeholder="instabot_user"
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

            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ display: 'block', fontSize: '0.875rem', marginBottom: '0.5rem', color: 'hsl(var(--muted-foreground))' }}>
                {mode === 'add' ? 'Instagram Password' : 'New Password (Optional)'}
              </label>
              <div style={{ position: 'relative' }}>
                <Lock style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'hsl(var(--muted-foreground))' }} size={18} />
                <input
                  type="password"
                  required={mode === 'add'}
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})}
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
                Proxy Configuration (Optional)
              </label>
              <div style={{ position: 'relative' }}>
                <Globe style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'hsl(var(--muted-foreground))' }} size={18} />
                <input
                  type="text"
                  value={formData.proxy}
                  onChange={(e) => setFormData({...formData, proxy: e.target.value})}
                  placeholder="Proxy ID (number) or leave empty"
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
                Status
              </label>
              <ThemedSelect
                value={formData.status}
                onChange={(v) => setFormData({ ...formData, status: v })}
                ariaLabel="Account Status"
                options={[
                  { value: 'active', label: 'Active' },
                  { value: 'paused', label: 'Paused' },
                  { value: 'inactive', label: 'Inactive' },
                  { value: 'checkpoint', label: 'Checkpoint' },
                  { value: 'banned', label: 'Banned' },
                ]}
              />
            </div>

            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
              <button 
                type="button" 
                onClick={onClose}
                className="btn" 
                style={{ flex: 1, border: '1px solid hsl(var(--border))' }}
              >
                Cancel
              </button>
              <button 
                type="submit" 
                disabled={loading}
                className="btn btn-primary" 
                style={{ flex: 1 }}
              >
                {loading ? <Loader2 className="animate-spin" size={20} /> : (mode === 'add' ? 'Add Account' : 'Save Changes')}
              </button>
            </div>
          </form>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default AccountModal;
