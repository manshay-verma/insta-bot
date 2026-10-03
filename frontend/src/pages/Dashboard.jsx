import React, { useEffect, useState } from 'react';
import Sidebar from '../components/Sidebar';
import StatsGrid from '../components/StatsGrid';
import ActivityChart from '../components/ActivityChart';
import Timeline from '../components/Timeline';
import api from '../services/api';
import { Play, Activity, Clock, Zap } from 'lucide-react';

const Dashboard = () => {
  const [summary, setSummary] = useState(null);
  const [daily, setDaily] = useState([]);
  const [recentEvents, setRecentEvents] = useState([]);
  const [system, setSystem] = useState(null);
  const [upcoming, setUpcoming] = useState([]);

  useEffect(() => {
    const fetch = async () => {
      try {
        const [summaryRes, dailyRes, actionsRes, systemRes, upcomingRes] = await Promise.all([
          api.get('/analytics/dashboard/'),
          api.get('/analytics/daily/?page_size=7'),
          api.get('/analytics/actions/?page_size=10'),
          api.get('/system/status/'),
          api.get('/schedule/upcoming/'),
        ]);

        setSummary(summaryRes.data);
        setSystem(systemRes.data);
        setUpcoming(upcomingRes.data?.items || []);

        const dailyRows = Array.isArray(dailyRes.data) ? dailyRes.data : (dailyRes.data?.results || []);
        const chart = dailyRows.slice(-7).map((r) => ({
          name: (r.date || '').slice(5), // MM-DD
          actions: (r.follows_count || 0) + (r.likes_count || 0) + (r.downloads_count || 0),
          downloads: r.downloads_count || 0,
        }));
        setDaily(chart);

        const actionRows = Array.isArray(actionsRes.data) ? actionsRes.data : (actionsRes.data?.results || []);
        setRecentEvents(actionRows.slice(0, 6).map((a) => ({
          title: `${a.action_type || 'action'} ${a.success ? 'succeeded' : 'failed'}`,
          time: a.created_at ? new Date(a.created_at).toLocaleString() : '—',
          description: `${a.account_username || 'account'} → ${a.target_username || a.target_url || 'target'}`,
          type: a.success ? 'success' : 'error',
        })));
      } catch (e) {
        console.error('Failed to load dashboard:', e);
        setSummary(null);
        setDaily([]);
        setRecentEvents([]);
        setSystem(null);
        setUpcoming([]);
      }
    };
    fetch();
  }, []);

  const startAll = async () => {
    await api.post('/bots/control/bulk/', { action: 'start_all' });
  };

  const stopAll = async () => {
    await api.post('/bots/control/bulk/', { action: 'stop_all' });
  };

  const cleanupDb = async () => {
    await api.post('/maintenance/cleanup/', { cutoff_days: 30 });
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: 'hsl(var(--background))' }}>
      <Sidebar />
      
      <main style={{ flex: 1, marginLeft: '240px', padding: '2.5rem' }}>
        <header style={{ marginBottom: '3rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ fontSize: '2.25rem', fontWeight: 'bold' }}>Dashboard</h1>
            <p style={{ color: 'hsl(var(--muted-foreground))', marginTop: '0.25rem' }}>Overview of your Instagram automation network.</p>
          </div>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <button className="btn" style={{ border: '1px solid hsl(var(--border))' }}>Settings</button>
            <button className="btn btn-primary" style={{ gap: '8px' }}>
              <Zap size={18} /> Deep Scan
            </button>
          </div>
        </header>

        <StatsGrid summary={summary} />
        
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.2fr', gap: '2rem' }}>
          <section style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <ActivityChart data={daily} />
            
            <div className="glass" style={{ padding: '2rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2rem' }}>
                <Activity size={24} color="hsl(var(--primary))" />
                <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>Activity Timeline</h3>
              </div>
              <Timeline events={recentEvents} />
            </div>
          </section>
          
          <aside style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div className="glass" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <h3 style={{ fontSize: '1.125rem', fontWeight: 'bold' }}>Quick Actions</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <button
                  className="btn"
                  onClick={startAll}
                  style={{ justifyContent: 'flex-start', width: '100%', backgroundColor: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.2)' }}
                >
                  Start All Bots
                </button>
                <button
                  className="btn"
                  onClick={stopAll}
                  style={{ justifyContent: 'flex-start', width: '100%', backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', color: '#ef4444' }}
                >
                  Emergency Stop
                </button>
                <button
                  className="btn"
                  onClick={cleanupDb}
                  style={{ justifyContent: 'flex-start', width: '100%', backgroundColor: 'rgba(255, 255, 255, 0.05)', border: '1px solid hsl(var(--border))' }}
                >
                  Clean Database
                </button>
              </div>
              
              <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid hsl(var(--border))' }}>
                <p style={{ fontSize: '0.875rem', color: 'hsl(var(--muted-foreground))', display: 'flex', justifyContent: 'space-between' }}>
                  <span>Network Health</span>
                  <span style={{ color: '#10b981', fontWeight: 600 }}>{system?.network_health || '—'}</span>
                </p>
                <p style={{ fontSize: '0.875rem', color: 'hsl(var(--muted-foreground))', display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem' }}>
                  <span>CPU Usage</span>
                  <span>{system?.cpu_usage_percent == null ? '—' : `${system.cpu_usage_percent}%`}</span>
                </p>
              </div>
            </div>

            <div className="glass" style={{ padding: '1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                <Clock size={20} color="hsl(var(--primary))" />
                <h3 style={{ fontSize: '1.125rem', fontWeight: 'bold' }}>Upcoming Schedule</h3>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {upcoming.length === 0 ? (
                  <div style={{ padding: '0.75rem', color: 'hsl(var(--muted-foreground))' }}>
                    No upcoming schedule configured.
                  </div>
                ) : upcoming.map((it, i) => (
                  <div key={it.id || i} style={{ padding: '0.75rem', borderRadius: '8px', borderLeft: '4px solid hsl(var(--primary))', backgroundColor: 'rgba(55, 130, 246, 0.05)' }}>
                    <p style={{ fontWeight: 600, fontSize: '0.875rem' }}>{it.title || 'Scheduled task'}</p>
                    <p style={{ fontSize: '0.75rem', color: 'hsl(var(--muted-foreground))' }}>{it.description || ''}</p>
                    <p style={{ fontSize: '0.75rem', color: 'hsl(var(--primary))', marginTop: '4px' }}>{it.when || '—'}</p>
                  </div>
                ))}
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
