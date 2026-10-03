import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, AlertCircle, AlertTriangle, Info, CheckCircle2 } from 'lucide-react';

const Alert = ({ id, type = 'info', message, details, onDismiss }) => {
  const getStyles = () => {
    switch (type) {
      case 'error': return { bg: 'rgba(239, 68, 68, 0.1)', border: 'rgba(239, 68, 68, 0.2)', icon: <AlertCircle size={20} color="#ef4444" />, title: 'Error' };
      case 'warning': return { bg: 'rgba(245, 158, 11, 0.1)', border: 'rgba(245, 158, 11, 0.2)', icon: <AlertTriangle size={20} color="#f59e0b" />, title: 'Warning' };
      case 'success': return { bg: 'rgba(16, 185, 129, 0.1)', border: 'rgba(16, 185, 129, 0.2)', icon: <CheckCircle2 size={20} color="#10b981" />, title: 'Success' };
      default: return { bg: 'rgba(59, 130, 246, 0.1)', border: 'rgba(59, 130, 246, 0.2)', icon: <Info size={20} color="hsl(var(--primary))" />, title: 'Information' };
    }
  };

  const styles = getStyles();

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
      style={{
        padding: '1rem 1.25rem',
        borderRadius: 'var(--radius)',
        backgroundColor: styles.bg,
        border: `1px solid ${styles.border}`,
        display: 'flex',
        gap: '0.75rem',
        alignItems: 'flex-start',
        position: 'relative'
      }}
    >
      <div style={{ marginTop: '2px' }}>{styles.icon}</div>
      <div style={{ flex: 1 }}>
        <p style={{ fontWeight: 600, fontSize: '0.875rem', marginBottom: '0.25rem' }}>{styles.title}</p>
        <p style={{ fontSize: '0.8125rem', lineHeight: 1.5 }}>{message}</p>
        {details && (
          <p style={{ fontSize: '0.75rem', marginTop: '0.5rem', opacity: 0.7, fontFamily: 'monospace' }}>
            {details}
          </p>
        )}
      </div>
      <button 
        onClick={() => onDismiss(id)}
        style={{ border: 'none', background: 'none', cursor: 'pointer', padding: '4px', opacity: 0.5, color: 'white' }}
      >
        <X size={16} />
      </button>
    </motion.div>
  );
};

export default Alert;
