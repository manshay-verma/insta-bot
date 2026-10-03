import React, { useState } from 'react';
import Sidebar from '../components/Sidebar';
import { 
  DownloadCloud, 
  FileJson, 
  FileSpreadsheet, 
  Archive, 
  Clock, 
  Database,
  Loader2,
  CheckCircle2,
  ShieldCheck,
  Zap
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const ExportCenter = () => {
  const [exporting, setExporting] = useState(false);
  const [format, setFormat] = useState('json');
  const [success, setSuccess] = useState(false);

  const handleExport = () => {
    setExporting(true);
    setSuccess(false);
    setTimeout(() => {
      setExporting(false);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    }, 2000);
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: 'hsl(var(--background))' }}>
      <Sidebar />
      <main style={{ flex: 1, marginLeft: '240px', padding: '2.5rem' }}>
        <header style={{ marginBottom: '3rem' }}>
          <h1 style={{ fontSize: '2.25rem', fontWeight: 'bold' }}>Export Center</h1>
          <p style={{ color: 'hsl(var(--muted-foreground))', marginTop: '0.5rem' }}>Generate and download reports of your bot data and media.</p>
        </header>

        <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '2rem' }}>
          <section style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div className="glass" style={{ padding: '2.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2.5rem' }}>
                <Zap size={24} color="hsl(var(--primary))" />
                <h3 style={{ fontSize: '1.4rem', fontWeight: 'bold' }}>Data Configuration</h3>
              </div>

              <div style={{ marginBottom: '2rem' }}>
                <p style={{ fontWeight: 500, marginBottom: '1rem' }}>Select Data Types</p>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  {[
                    { label: 'Account Analytics', icon: <FileJson size={18} /> },
                    { label: 'Action Logs', icon: <FileSpreadsheet size={18} /> },
                    { label: 'Media Downloads Metadata', icon: <Archive size={18} /> },
                    { label: 'System Usage Reports', icon: <Clock size={18} /> }
                  ].map((item, i) => (
                    <div key={i} className="glass" style={{ padding: '1rem', display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer', border: '1px solid rgba(255,255,255,0.05)' }}>
                      <input type="checkbox" defaultChecked style={{ accentColor: 'hsl(var(--primary))' }} />
                      <div style={{ color: 'hsl(var(--primary))' }}>{item.icon}</div>
                      <span style={{ fontSize: '0.875rem' }}>{item.label}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ marginBottom: '2rem' }}>
                <p style={{ fontWeight: 500, marginBottom: '1rem' }}>Export Format</p>
                <div style={{ display: 'flex', gap: '1rem' }}>
                  {['JSON', 'CSV', 'PDF', 'Archive (ZIP)'].map(f => (
                    <button
                      key={f}
                      onClick={() => setFormat(f.toLowerCase())}
                      className="btn"
                      style={{ 
                        flex: 1, 
                        border: format === f.toLowerCase() ? '1px solid hsl(var(--primary))' : '1px solid hsl(var(--border))',
                        backgroundColor: format === f.toLowerCase() ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
                        color: format === f.toLowerCase() ? 'white' : 'hsl(var(--muted-foreground))'
                      }}
                    >
                      {f}
                    </button>
                  ))}
                </div>
              </div>

              <button 
                onClick={handleExport}
                disabled={exporting}
                className="btn btn-primary" 
                style={{ width: '100%', padding: '1.25rem', gap: '0.75rem', fontSize: '1rem' }}
              >
                {exporting ? <Loader2 className="animate-spin" /> : <DownloadCloud size={22} />}
                <span>{exporting ? 'Generating Bundle...' : 'Export Selected Data'}</span>
              </button>

              <AnimatePresence>
                {success && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    style={{ 
                      marginTop: '1.5rem', 
                      padding: '1rem', 
                      borderRadius: 'var(--radius)', 
                      backgroundColor: 'rgba(16, 185, 129, 0.1)', 
                      color: '#10b981', 
                      display: 'flex', 
                      alignItems: 'center', 
                      gap: '0.75rem', 
                      border: '1px solid rgba(16, 185, 129, 0.2)' 
                    }}
                  >
                    <CheckCircle2 size={20} />
                    <span>Your export is ready! Downloading automatically.</span>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <div className="glass" style={{ padding: '2rem' }}>
              <h3 style={{ fontSize: '1.125rem', fontWeight: 'bold', marginBottom: '1.5rem' }}>Export History</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {[
                  { name: 'Monthly_Analytics_April.json', date: '2 hours ago', size: '2.4 MB' },
                  { name: 'Account_List_Backup.csv', date: 'Yesterday', size: '124 KB' }
                ].map((h, idx) => (
                  <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem', borderRadius: '8px', backgroundColor: 'rgba(255,255,255,0.02)' }}>
                    <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                      <FileJson size={18} color="hsl(var(--muted-foreground))" />
                      <div>
                        <p style={{ fontSize: '0.875rem', fontWeight: 500 }}>{h.name}</p>
                        <p style={{ fontSize: '0.75rem', color: 'hsl(var(--muted-foreground))' }}>{h.date} • {h.size}</p>
                      </div>
                    </div>
                    <button className="btn" style={{ padding: '4px', minHeight: 'unset' }}><DownloadCloud size={16} /></button>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <aside style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div className="glass" style={{ padding: '1.5rem', backgroundColor: 'rgba(59, 130, 246, 0.05)', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
              <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem' }}>
                <ShieldCheck size={20} color="hsl(var(--primary))" />
                <h4 style={{ fontWeight: 'bold' }}>Data Safety</h4>
              </div>
              <p style={{ fontSize: '0.8125rem', color: 'hsl(var(--muted-foreground))', lineHeight: 1.5 }}>
                Exports contain sensitive account data. Always keep your exported files in a secure location and do not share them with unauthorized parties.
              </p>
            </div>

            <div className="glass" style={{ padding: '1.5rem' }}>
              <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem' }}>
                <Database size={20} color="hsl(var(--primary))" />
                <h4 style={{ fontWeight: 'bold' }}>Live Data Pool</h4>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem' }}>
                  <span style={{ color: 'hsl(var(--muted-foreground))' }}>Total Rows</span>
                  <span style={{ fontWeight: 600 }}>12,842</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem' }}>
                  <span style={{ color: 'hsl(var(--muted-foreground))' }}>Media Assets</span>
                  <span style={{ fontWeight: 600 }}>142 GB</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem' }}>
                  <span style={{ color: 'hsl(var(--muted-foreground))' }}>Last DB Sync</span>
                  <span style={{ color: '#10b981' }}>Healthy</span>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
};

export default ExportCenter;
