import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useSocketStore } from '../store/useSocketStore';
import { Bell, X, Info, CheckCircle, AlertTriangle, ShieldCheck } from 'lucide-react';

const NotificationToast = ({ id, type, message, onDismiss }) => {
  const getIcon = () => {
    switch (type) {
      case 'success': return <CheckCircle size={18} color="#10b981" />;
      case 'warning': return <AlertTriangle size={18} color="#f59e0b" />;
      case 'error': return <AlertTriangle size={18} color="#ef4444" />;
      default: return <Info size={18} color="hsl(var(--primary))" />;
    }
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 50, scale: 0.9 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 20, scale: 0.95 }}
      className="glass"
      style={{
        padding: '1rem',
        width: '320px',
        display: 'flex',
        gap: '0.75rem',
        alignItems: 'flex-start',
        boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)',
        backgroundColor: 'rgba(15, 23, 42, 0.95)',
        border: '1px solid rgba(255, 255, 255, 0.1)'
      }}
    >
      <div style={{ marginTop: '2px' }}>{getIcon()}</div>
      <div style={{ flex: 1 }}>
        <p style={{ fontSize: '0.875rem', fontWeight: 500 }}>{message}</p>
        <span style={{ fontSize: '0.75rem', color: 'hsl(var(--muted-foreground))' }}>Just now</span>
      </div>
      <button 
        onClick={() => onDismiss(id)}
        style={{ border: 'none', background: 'none', color: 'hsl(var(--muted-foreground))', cursor: 'pointer', padding: '2px' }}
      >
        <X size={16} />
      </button>
    </motion.div>
  );
};

const NotificationCenter = () => {
  const { notifications, clearNotifications } = useSocketStore();
  const [showPanel, setShowPanel] = React.useState(false);

  const dismiss = (id) => {
    // In a real app we'd have a remove method in store
    // For now we'll just let them accumulate and clear all
  };

  return (
    <>
      {/* Toast Overlay */}
      <div style={{
        position: 'fixed',
        top: '1.5rem',
        right: '1.5rem',
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem',
        pointerEvents: 'none'
      }}>
        <AnimatePresence>
          {notifications.slice(0, 3).map(n => (
            <div key={n.id} style={{ pointerEvents: 'auto' }}>
              <NotificationToast {...n} onDismiss={dismiss} />
            </div>
          ))}
        </AnimatePresence>
      </div>

      {/* Connectivity Indicator and Bell */}
      <div style={{ 
        position: 'fixed', 
        bottom: '1.5rem', 
        right: '1.5rem', 
        zIndex: 500,
        display: 'flex',
        gap: '1rem'
      }}>
        <motion.button
          whileTap={{ scale: 0.95 }}
          onClick={() => setShowPanel(!showPanel)}
          className="glass"
          style={{
            padding: '0.75rem',
            position: 'relative',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            border: '1px solid rgba(255, 255, 255, 0.1)'
          }}
        >
          <Bell size={24} />
          {notifications.length > 0 && (
            <span style={{
              position: 'absolute',
              top: '-4px',
              right: '-4px',
              width: '18px',
              height: '18px',
              backgroundColor: '#ef4444',
              borderRadius: '50%',
              fontSize: '0.625rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 'bold',
              border: '2px solid hsl(var(--background))'
            }}>
              {notifications.length}
            </span>
          )}
        </motion.button>
      </div>
    </>
  );
};

export default NotificationCenter;
