import React, { useEffect, useState } from 'react';
import Sidebar from '../components/Sidebar';
import api from '../services/api';
import { 
  Settings, 
  Moon, 
  Sun, 
  Bell, 
  Shield, 
  Database, 
  Save,
  Globe,
  Monitor
} from 'lucide-react';
import { motion } from 'framer-motion';

const SettingsPage = () => {
  const [theme, setTheme] = useState('dark');
  const [notifications, setNotifications] = useState({
    browser: true,
    email: false,
    webhooks: true
  });
  const [proxySettings, setProxySettings] = useState({
    globalProxy: '',
    trustLevel: 'medium'
  });
  const [saving, setSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.get('/settings/');
        setTheme(res.data?.theme || 'dark');
        setNotifications(res.data?.notifications || { browser: true, email: false, webhooks: true });
        setProxySettings(res.data?.proxy_settings || { globalProxy: '', trustLevel: 'medium' });
      } catch (e) {
        console.error('Failed to load settings:', e);
      }
    };
    load();
  }, []);

  const saveAll = async () => {
    setSaving(true);
    setStatusMsg('');
    try {
      await api.post('/settings/', {
        theme,
        notifications,
        proxy_settings: proxySettings,
      });
      setStatusMsg('Saved.');
      setTimeout(() => setStatusMsg(''), 2000);
    } catch (e) {
      console.error('Failed to save settings:', e);
      setStatusMsg('Save failed.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: 'hsl(var(--background))' }}>
      <Sidebar />
      <main style={{ flex: 1, marginLeft: '240px', padding: '2.5rem' }}>
        <header style={{ marginBottom: '3rem' }}>
          <h1 style={{ fontSize: '2.25rem', fontWeight: 'bold' }}>Settings</h1>
          <p style={{ color: 'hsl(var(--muted-foreground))', marginTop: '0.5rem' }}>Configure your dashboard preferences and system parameters.</p>
        </header>

        <div style={{ maxWidth: '800px', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          {/* Appearance */}
          <section className="glass" style={{ padding: '2rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
              <Monitor size={20} color="hsl(var(--primary))" />
              <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>Appearance</h3>
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <p style={{ fontWeight: 500 }}>Interface Theme</p>
                <p style={{ fontSize: '0.875rem', color: 'hsl(var(--muted-foreground))' }}>Choose between light and dark mode (Currently Dark only).</p>
              </div>
              <div className="glass" style={{ display: 'flex', padding: '4px', gap: '4px' }}>
                <button 
                  onClick={() => setTheme('light')}
                  style={{ 
                    padding: '8px 16px', borderRadius: 'var(--radius)', border: 'none', 
                    backgroundColor: theme === 'light' ? 'white' : 'transparent',
                    color: theme === 'light' ? 'black' : 'white', cursor: 'pointer', display: 'flex', gap: '0.5rem', alignItems: 'center'
                  }}
                >
                  <Sun size={16} /> Light
                </button>
                <button 
                  onClick={() => setTheme('dark')}
                  style={{ 
                    padding: '8px 16px', borderRadius: 'var(--radius)', border: 'none', 
                    backgroundColor: theme === 'dark' ? 'hsl(var(--primary))' : 'transparent',
                    color: 'white', cursor: 'pointer', display: 'flex', gap: '0.5rem', alignItems: 'center'
                  }}
                >
                  <Moon size={16} /> Dark
                </button>
              </div>
            </div>
          </section>

          {/* Notifications */}
          <section className="glass" style={{ padding: '2rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
              <Bell size={20} color="hsl(var(--primary))" />
              <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>Notification Preferences</h3>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {[
                { id: 'browser', label: 'Browser Notifications', desc: 'Real-time toast alerts in the dashboard.' },
                { id: 'email', label: 'Email Alerts', desc: 'Summary of bot activity and critical errors.' },
                { id: 'webhooks', label: 'Webhook Integrations', desc: 'Send events to external services via HTTP POST.' }
              ].map(item => (
                <div key={item.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <p style={{ fontWeight: 500 }}>{item.label}</p>
                    <p style={{ fontSize: '0.875rem', color: 'hsl(var(--muted-foreground))' }}>{item.desc}</p>
                  </div>
                  <div 
                    onClick={() => setNotifications({...notifications, [item.id]: !notifications[item.id]})}
                    style={{ 
                      width: '44px', height: '24px', backgroundColor: notifications[item.id] ? 'hsl(var(--primary))' : 'rgba(255,255,255,0.1)',
                      borderRadius: '12px', cursor: 'pointer', position: 'relative', transition: 'all 0.2s'
                    }}
                  >
                    <motion.div 
                      animate={{ x: notifications[item.id] ? 22 : 2 }}
                      style={{ width: '20px', height: '20px', backgroundColor: 'white', borderRadius: '50%', top: '2px', position: 'absolute' }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* System & API */}
          <section className="glass" style={{ padding: '2rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
              <Shield size={20} color="hsl(var(--primary))" />
              <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>System & Security</h3>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', marginBottom: '0.5rem', color: 'hsl(var(--muted-foreground))' }}>Default Global Proxy</label>
                <div style={{ position: 'relative' }}>
                  <Globe style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'hsl(var(--muted-foreground))' }} size={18} />
                  <input
                    type="text"
                    value={proxySettings.globalProxy}
                    onChange={(e) => setProxySettings({...proxySettings, globalProxy: e.target.value})}
                    placeholder="http://proxy.host:port"
                    style={{
                      width: '100%', padding: '0.75rem 0.75rem 0.75rem 2.5rem', 
                      backgroundColor: 'rgba(255, 255, 255, 0.05)', border: '1px solid hsl(var(--border))',
                      borderRadius: 'var(--radius)', color: 'white', outline: 'none'
                    }}
                  />
                </div>
              </div>

              <div>
                <button
                  onClick={saveAll}
                  disabled={saving}
                  className="btn btn-primary"
                  style={{ gap: '0.75rem', width: '100%', padding: '1rem', opacity: saving ? 0.7 : 1 }}
                >
                  <Save size={20} />
                  {saving ? 'Saving...' : 'Save All Settings'}
                </button>
                {statusMsg && (
                  <div style={{ marginTop: '0.75rem', fontSize: '0.875rem', color: 'hsl(var(--muted-foreground))' }}>
                    {statusMsg}
                  </div>
                )}
              </div>
            </div>
          </section>

          <footer style={{ textAlign: 'center', padding: '1rem', color: 'hsl(var(--muted-foreground))', fontSize: '0.875rem' }}>
            InstaBot Pro v1.4.2-stable • Connected as Admin
          </footer>
        </div>
      </main>
    </div>
  );
};

export default SettingsPage;
