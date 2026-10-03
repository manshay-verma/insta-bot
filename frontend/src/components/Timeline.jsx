import React from 'react';
import { motion } from 'framer-motion';

const Timeline = ({ events }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {events.map((event, index) => (
        <motion.div 
          key={index}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: index * 0.1 }}
          style={{ display: 'flex', gap: '1rem', position: 'relative' }}
        >
          {/* Vertical Line */}
          {index !== events.length - 1 && (
            <div style={{
              position: 'absolute',
              left: '7px',
              top: '20px',
              width: '2px',
              height: 'calc(100% + 0.5rem)',
              backgroundColor: 'rgba(255, 255, 255, 0.05)'
            }} />
          )}

          {/* Dot */}
          <div style={{
            width: '16px',
            height: '16px',
            borderRadius: '50%',
            backgroundColor: event.type === 'success' ? '#10b981' : event.type === 'error' ? '#ef4444' : 'hsl(var(--primary))',
            marginTop: '4px',
            zIndex: 1,
            border: '4px solid hsl(var(--background))',
            boxShadow: `0 0 10px ${event.type === 'success' ? '#10b981' : event.type === 'error' ? '#ef4444' : 'hsl(var(--primary))'}`
          }} />

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>{event.title}</span>
              <span style={{ fontSize: '0.75rem', color: 'hsl(var(--muted-foreground))' }}>{event.time}</span>
            </div>
            <p style={{ fontSize: '0.8125rem', color: 'hsl(var(--muted-foreground))', marginTop: '0.25rem' }}>{event.description}</p>
          </div>
        </motion.div>
      ))}
    </div>
  );
};

export default Timeline;
