import React from 'react';
import { 
  Users, 
  Activity, 
  DownloadCloud, 
  Clock, 
  ArrowUpRight, 
  ArrowDownRight 
} from 'lucide-react';
import { motion } from 'framer-motion';

const StatCard = ({ title, value, icon, change, isPositive }) => (
  <motion.div 
    whileHover={{ y: -5 }}
    className="glass" 
    style={{ 
      padding: '1.5rem', 
      display: 'flex', 
      flexDirection: 'column', 
      gap: '1rem',
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
    }}
  >
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <div style={{ 
        padding: '10px', 
        borderRadius: '12px', 
        backgroundColor: 'rgba(59, 130, 246, 0.1)', 
        color: 'hsl(var(--primary))' 
      }}>
        {icon}
      </div>
      {change && (
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '4px',
          fontSize: '0.875rem',
          color: isPositive ? '#10b981' : '#ef4444' 
        }}>
          {isPositive ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
          <span>{change}</span>
        </div>
      )}
    </div>
    
    <div>
      <p style={{ color: 'hsl(var(--muted-foreground))', fontSize: '0.875rem' }}>{title}</p>
      <h3 style={{ fontSize: '1.75rem', fontWeight: 'bold', marginTop: '0.25rem' }}>{value}</h3>
    </div>
  </motion.div>
);

const StatsGrid = ({ summary }) => {
  const stats = [
    { title: 'Connected Accounts', value: `${summary?.total_accounts ?? '—'}`, icon: <Users size={24} />, change: null, isPositive: true },
    { title: 'Active Accounts', value: `${summary?.active_accounts ?? '—'}`, icon: <Activity size={24} />, change: null, isPositive: true },
    { title: 'Actions Today', value: `${summary?.total_actions_today ?? '—'}`, icon: <Activity size={24} />, change: null, isPositive: true },
    { title: 'Downloads Today', value: `${summary?.total_downloads_today ?? '—'}`, icon: <DownloadCloud size={24} />, change: null, isPositive: true },
  ];

  return (
    <div style={{ 
      display: 'grid', 
      gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', 
      gap: '1.5rem',
      marginBottom: '2.5rem'
    }}>
      {stats.map((stat, idx) => (
        <StatCard key={idx} {...stat} />
      ))}
    </div>
  );
};

export default StatsGrid;
