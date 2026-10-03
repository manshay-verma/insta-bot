import React from 'react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  AreaChart, 
  Area 
} from 'recharts';

const ActivityChart = ({ data = [] }) => {
  return (
    <div className="glass" style={{ 
      padding: '2rem', 
      height: '350px', 
      width: '100%',
      marginBottom: '2.5rem',
      display: 'flex',
      flexDirection: 'column',
      gap: '1rem'
    }}>
      <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>Activity Overview</h3>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{
            top: 10,
            right: 30,
            left: 0,
            bottom: 0,
          }}
        >
          <defs>
            <linearGradient id="colorActions" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="colorDownloads" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255, 255, 255, 0.05)" />
          <XAxis 
            dataKey="name" 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }} 
            dy={10}
          />
          <YAxis 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }} 
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: 'rgba(15, 23, 42, 0.9)', 
              borderColor: 'rgba(255, 255, 255, 0.1)',
              borderRadius: '12px',
              color: 'white'
            }} 
            itemStyle={{ color: 'white' }}
          />
          <Area 
            type="monotone" 
            dataKey="actions" 
            stroke="hsl(var(--primary))" 
            strokeWidth={3}
            fillOpacity={1} 
            fill="url(#colorActions)" 
          />
          <Area 
            type="monotone" 
            dataKey="downloads" 
            stroke="#10b981" 
            strokeWidth={3}
            fillOpacity={1} 
            fill="url(#colorDownloads)" 
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ActivityChart;
