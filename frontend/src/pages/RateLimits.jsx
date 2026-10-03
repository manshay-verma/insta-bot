import React, { useEffect, useState } from 'react';
import Sidebar from '../components/Sidebar';
import api from '../services/api';
import { 
  Shield, 
  Clock, 
  Zap, 
  Save, 
  AlertTriangle, 
  Info,
  ChevronRight,
  Plus,
  Trash2
} from 'lucide-react';
import { motion } from 'framer-motion';

const RateLimitPage = () => {
  const [loading, setLoading] = useState(true);
  const [limits, setLimits] = useState([]);

  useEffect(() => {
    const fetchLimits = async () => {
      try {
        const res = await api.get('/rate-limits/');
        const l = res.data?.limits || {};
        // Backend returns a dict of limits; UI expects rows
        const rows = Object.entries(l).map(([k, v]) => ({
          action: k,
          hourly: typeof v === 'number' ? v : '',
          daily: '',
          delay: '',
        }));
        setLimits(rows);
      } catch (e) {
        console.error('Failed to fetch rate limits:', e);
        setLimits([]);
      } finally {
        setLoading(false);
      }
    };
    fetchLimits();
  }, []);

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: 'hsl(var(--background))' }}>
      <Sidebar />
      <main style={{ flex: 1, marginLeft: '240px', padding: '2.5rem' }}>
        <header style={{ marginBottom: '3rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ fontSize: '2.25rem', fontWeight: 'bold' }}>Rate Limit Settings</h1>
            <p style={{ color: 'hsl(var(--muted-foreground))', marginTop: '0.5rem' }}>Define humanized behavior constraints to maintain account safety.</p>
          </div>
          <button className="btn btn-primary" style={{ gap: '0.75rem' }}>
            <Save size={18} /> Save Thresholds
          </button>
        </header>

        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '2rem' }}>
          <section style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div className="glass" style={{ padding: '0' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid hsl(var(--border))' }}>
                    <th style={{ padding: '1.25rem', fontSize: '0.875rem', fontWeight: 600 }}>Action Type</th>
                    <th style={{ padding: '1.25rem', fontSize: '0.875rem', fontWeight: 600 }}>Hourly Limit</th>
                    <th style={{ padding: '1.25rem', fontSize: '0.875rem', fontWeight: 600 }}>Daily Limit</th>
                    <th style={{ padding: '1.25rem', fontSize: '0.875rem', fontWeight: 600 }}>In-between Delay</th>
                    <th style={{ padding: '1.25rem' }}></th>
                  </tr>
                </thead>
                <tbody>
                  {limits.map((limit, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '1.25rem', fontWeight: 500 }}>{limit.action}</td>
                      <td style={{ padding: '1.25rem' }}>
                        <input type="number" defaultValue={limit.hourly} style={{ width: '60px', padding: '4px 8px', borderRadius: '4px', backgroundColor: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: 'white' }} />
                      </td>
                      <td style={{ padding: '1.25rem' }}>
                        <input type="number" defaultValue={limit.daily} style={{ width: '80px', padding: '4px 8px', borderRadius: '4px', backgroundColor: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: 'white' }} />
                      </td>
                      <td style={{ padding: '1.25rem' }}>
                        <input type="text" defaultValue={limit.delay} style={{ width: '100px', padding: '4px 8px', borderRadius: '4px', backgroundColor: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: 'white' }} />
                      </td>
                      <td style={{ padding: '1.25rem', textAlign: 'right' }}>
                        <button className="btn" style={{ padding: '4px', color: '#ef4444' }}><Trash2 size={16} /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!loading && limits.length === 0 && (
                <div style={{ padding: '1.5rem', color: 'hsl(var(--muted-foreground))' }}>
                  No limits loaded. Make sure the backend is running.
                </div>
              )}
              <button className="btn" style={{ width: '100%', padding: '1rem', border: 'none', backgroundColor: 'rgba(255,255,255,0.02)', gap: '0.5rem', color: 'hsl(var(--muted-foreground))' }}>
                <Plus size={16} /> Add Custom Rule
              </button>
            </div>

            <div className="glass" style={{ padding: '1.5rem', backgroundColor: 'rgba(245, 158, 11, 0.05)', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
              <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '0.75rem', color: '#f59e0b' }}>
                <AlertTriangle size={20} />
                <h4 style={{ fontWeight: 'bold' }}>Risk Analysis</h4>
              </div>
              <ul style={{ fontSize: '0.8125rem', color: 'hsl(var(--muted-foreground))', lineHeight: 1.6, paddingLeft: '1.5rem' }}>
                <li>Your current "Like" threshold is near the "High Risk" zone for fresh accounts.</li>
                <li>Consider increasing the "In-between Delay" to at least 45s for "Follow" actions.</li>
                <li>System will automatically pause tasks if any 403 (Forbidden) response is received.</li>
              </ul>
            </div>
          </section>

          <aside style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div className="glass" style={{ padding: '1.5rem' }}>
              <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem' }}>
                <Shield size={20} color="hsl(var(--primary))" />
                <h4 style={{ fontWeight: 'bold' }}>Humanization Mode</h4>
              </div>
              {[
                { label: 'Jittery Scrolling', desc: 'Adds random scroll pauses' },
                { label: 'Ghost Browsing', desc: 'Navigates profile before action' },
                { label: 'Sleep Cycles', desc: 'Auto-disable during night hours' }
              ].map((h, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <div>
                    <p style={{ fontSize: '0.875rem', fontWeight: 500 }}>{h.label}</p>
                    <p style={{ fontSize: '0.75rem', color: 'hsl(var(--muted-foreground))' }}>{h.desc}</p>
                  </div>
                  <input type="checkbox" defaultChecked style={{ accentColor: 'hsl(var(--primary))' }} />
                </div>
              ))}
            </div>

            <div className="glass" style={{ padding: '1.5rem' }}>
              <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.25rem' }}>
                <Clock size={20} color="hsl(var(--primary))" />
                <h4 style={{ fontWeight: 'bold' }}>Bot Sleep Schedule</h4>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem' }}>
                  <span>Mon - Fri</span>
                  <span style={{ color: 'hsl(var(--primary))' }}>22:00 - 07:00</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem' }}>
                  <span>Sat - Sun</span>
                  <span style={{ color: 'hsl(var(--primary))' }}>23:00 - 09:00</span>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
};

export default RateLimitPage;
