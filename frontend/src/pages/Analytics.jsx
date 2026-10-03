import React, { useState, useEffect } from 'react';
import Sidebar from '../components/Sidebar';
import api from '../services/api';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  PieChart, 
  Pie, 
  Cell,
  Legend,
  AreaChart,
  Area
} from 'recharts';
import { 
  TrendingUp, 
  Users, 
  Heart, 
  MessageSquare, 
  Download, 
  Eye, 
  Calendar,
  Filter,
  DownloadCloud,
  Zap,
  Activity
} from 'lucide-react';
import { motion } from 'framer-motion';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

const AnalyticsPage = () => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState({
    daily: [],
    distribution: [],
    summary: {},
    taskHeatmap: []
  });

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const [dailyRes, actionsRes] = await Promise.all([
          api.get('/analytics/daily/'),
          api.get('/analytics/actions/?page_size=500'),
        ]);

        const dailyRows = Array.isArray(dailyRes.data) ? dailyRes.data : (dailyRes.data?.results || []);
        const actionRows = Array.isArray(actionsRes.data) ? actionsRes.data : (actionsRes.data?.results || []);

        const daily = dailyRows.map((r) => ({
          date: r.date,
          follows: r.follows_count ?? r.follows ?? 0,
          likes: r.likes_count ?? r.likes ?? 0,
          stories: r.stories_viewed ?? r.stories ?? 0,
          downloads: r.downloads_count ?? r.downloads ?? 0,
        }));

        const byType = actionRows.reduce((acc, row) => {
          const t = row.action_type || 'unknown';
          acc[t] = (acc[t] || 0) + 1;
          return acc;
        }, {});

        const distribution = Object.entries(byType).map(([name, value]) => ({ name, value }));

        const totalActions = actionRows.length;
        const successCount = actionRows.filter((a) => a.success === true).length;
        const successRate = totalActions > 0 ? `${((successCount / totalActions) * 100).toFixed(1)}%` : '—';

        const taskHeatmap = [
          { name: 'Likes', key: 'like', color: '#3b82f6' },
          { name: 'Follows', key: 'follow', color: '#10b981' },
          { name: 'Comments', key: 'comment', color: '#f59e0b' },
          { name: 'Downloads', key: 'download', color: '#ef4444' },
          { name: 'Stories', key: 'view_stories', color: '#8b5cf6' },
        ].map((t) => ({ name: t.name, count: byType[t.key] || 0, color: t.color }));

        setData({
          daily,
          distribution,
          summary: {
            totalActions,
            avgDaily: daily.length ? Math.round(totalActions / daily.length) : 0,
            successRate,
          },
          taskHeatmap,
        });
      } catch (err) {
        console.error('Failed to fetch analytics:', err);
        setData({ daily: [], distribution: [], summary: {}, taskHeatmap: [] });
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, []);

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: 'hsl(var(--background))' }}>
      <Sidebar />
      <main style={{ flex: 1, marginLeft: '240px', padding: '2.5rem' }}>
        <header style={{ marginBottom: '3rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ fontSize: '2.25rem', fontWeight: 'bold' }}>Analytics Deep-Dive</h1>
            <p style={{ color: 'hsl(var(--muted-foreground))', marginTop: '0.5rem' }}>Comprehensive performance analysis across your bot network.</p>
          </div>
          <button className="btn" style={{ border: '1px solid hsl(var(--border))', gap: '0.5rem' }}>
            <DownloadCloud size={18} /> Export Report
          </button>
        </header>

        {/* Charts Row */}
        <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '2rem', marginBottom: '2rem' }}>
          <section className="glass" style={{ padding: '2rem', height: '400px', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <TrendingUp size={20} color="hsl(var(--primary))" />
                <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>Growth Metrics</h3>
              </div>
            </div>
            
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.daily}>
                <defs>
                  <linearGradient id="colorFollows" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{fill: 'hsl(var(--muted-foreground))', fontSize: 11}} />
                <YAxis axisLine={false} tickLine={false} tick={{fill: 'hsl(var(--muted-foreground))', fontSize: 11}} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }} />
                <Area type="monotone" dataKey="follows" stroke="#3b82f6" fillOpacity={1} fill="url(#colorFollows)" strokeWidth={3} />
                <Area type="monotone" dataKey="likes" stroke="#10b981" fill="transparent" strokeWidth={3} />
              </AreaChart>
            </ResponsiveContainer>
          </section>

          <section className="glass" style={{ padding: '2rem', height: '400px', display: 'flex', flexDirection: 'column' }}>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', marginBottom: '2rem' }}>Task Volume</h3>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.taskHeatmap}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fill: 'hsl(var(--muted-foreground))', fontSize: 11}} />
                <YAxis axisLine={false} tickLine={false} tick={{fill: 'hsl(var(--muted-foreground))', fontSize: 11}} />
                <Tooltip cursor={{fill: 'rgba(255,255,255,0.05)'}} contentStyle={{ backgroundColor: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {data.taskHeatmap.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </section>
        </div>

        {/* Second Row: Distribution & System Highlights */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '2rem', marginBottom: '2rem' }}>
          <section className="glass" style={{ padding: '2rem', height: '400px', display: 'flex', flexDirection: 'column' }}>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', marginBottom: '2rem' }}>Action Distribution</h3>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data.distribution}
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {data.distribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
              </PieChart>
            </ResponsiveContainer>
          </section>

          <section className="glass" style={{ padding: '2rem', height: '400px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <Activity size={20} color="hsl(var(--primary))" />
                <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>Activity Heatmap</h3>
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '10px' }}>
              {Array.from({ length: 28 }).map((_, i) => (
                <motion.div
                  key={i}
                  whileHover={{ scale: 1.1 }}
                  style={{
                    aspectRatio: '1',
                    borderRadius: '4px',
                    backgroundColor: i % 5 === 0 ? 'rgba(59, 130, 246, 0.1)' : i % 3 === 0 ? 'rgba(59, 130, 246, 0.4)' : 'rgba(59, 130, 246, 0.8)',
                    cursor: 'pointer'
                  }}
                />
              ))}
            </div>
            <p style={{ marginTop: '2rem', fontSize: '0.75rem', color: 'hsl(var(--muted-foreground))', textAlign: 'center' }}>
              Visualizing the intensity of bot interactions over the last 4 weeks.
            </p>
          </section>
        </div>

        {/* Detailed Stats Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem' }}>
          {[
            { label: 'Avg Daily Actions', value: `${data.summary?.avgDaily ?? '—'}`, icon: <TrendingUp size={20} />, color: '#3b82f6' },
            { label: 'Success Rate', value: `${data.summary?.successRate ?? '—'}`, icon: <Heart size={20} />, color: '#ef4444' },
            { label: 'Total Actions', value: `${data.summary?.totalActions ?? '—'}`, icon: <MessageSquare size={20} />, color: '#f59e0b' },
            { label: 'Downloads (sum)', value: `${data.daily.reduce((s, r) => s + (r.downloads || 0), 0)}`, icon: <Download size={20} />, color: '#10b981' }
          ].map((stat, i) => (
            <motion.div 
              key={i}
              whileHover={{ scale: 1.02 }}
              className="glass" 
              style={{ padding: '1.5rem', display: 'flex', alignItems: 'center', gap: '1rem' }}
            >
              <div style={{ padding: '10px', borderRadius: '12px', backgroundColor: `${stat.color}10`, color: stat.color }}>
                {stat.icon}
              </div>
              <div>
                <p style={{ fontSize: '0.75rem', color: 'hsl(var(--muted-foreground))' }}>{stat.label}</p>
                <h4 style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>{stat.value}</h4>
              </div>
            </motion.div>
          ))}
        </div>
      </main>
    </div>
  );
};

export default AnalyticsPage;
