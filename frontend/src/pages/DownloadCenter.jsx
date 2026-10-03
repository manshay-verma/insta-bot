import React, { useState, useEffect } from 'react';
import Sidebar from '../components/Sidebar';
import api from '../services/api';
import { 
  Download, 
  FileVideo, 
  FileImage, 
  Clock, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  MoreVertical,
  ExternalLink,
  Search,
  Filter,
  PlayCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const DownloadItem = ({ download }) => {
  const getStatusInfo = (status) => {
    switch (status) {
      case 'completed': return { color: '#10b981', icon: <CheckCircle2 size={16} /> };
      case 'downloading': return { color: 'hsl(var(--primary))', icon: <Loader2 size={16} className="animate-spin" /> };
      case 'failed': return { color: '#ef4444', icon: <AlertCircle size={16} /> };
      default: return { color: 'hsl(var(--muted-foreground))', icon: <Clock size={16} /> };
    }
  };

  const status = getStatusInfo(download.status);

  return (
    <motion.div 
      layout
      className="glass"
      style={{ padding: '1.25rem', display: 'flex', gap: '1.25rem', alignItems: 'center' }}
    >
      <div style={{ 
        width: '60px', 
        height: '60px', 
        borderRadius: '12px', 
        backgroundColor: 'rgba(255, 255, 255, 0.05)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'hsl(var(--muted-foreground))',
        flexShrink: 0
      }}>
        {download.media_type === 'video' || download.media_type === 'reel' ? <FileVideo size={28} /> : <FileImage size={28} />}
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.25rem' }}>
          <h4 style={{ fontWeight: 600, fontSize: '0.9375rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {download.source_url.split('/').pop() || 'media_file'}
          </h4>
          <span style={{ fontSize: '0.75rem', color: 'hsl(var(--muted-foreground))' }}>{new Date(download.created_at).toLocaleTimeString()}</span>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '0.75rem', color: 'hsl(var(--muted-foreground))' }}>
          <span style={{ textTransform: 'capitalize' }}>{download.media_type}</span>
          <span>•</span>
          <span>{download.file_size_bytes ? `${(download.file_size_bytes / 1024 / 1024).toFixed(2)} MB` : 'Size unknown'}</span>
          <span>•</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: status.color }}>
            {status.icon}
            <span style={{ textTransform: 'capitalize' }}>{download.status}</span>
          </div>
        </div>

        {download.status === 'downloading' && (
          <div style={{ width: '100%', height: '4px', backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: '2px', marginTop: '0.75rem', overflow: 'hidden' }}>
            <motion.div 
              initial={{ width: 0 }}
              animate={{ width: '65%' }}
              style={{ height: '100%', backgroundColor: 'hsl(var(--primary))' }}
            />
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <button className="btn" style={{ padding: '8px', minHeight: 'unset', border: '1px solid hsl(var(--border))' }}>
          <ExternalLink size={16} />
        </button>
        <button className="btn" style={{ padding: '8px', minHeight: 'unset' }}>
          <MoreVertical size={16} />
        </button>
      </div>
    </motion.div>
  );
};

const DownloadCenter = () => {
  const [downloads, setDownloads] = useState([]);
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    const fetchDownloads = async () => {
      try {
        // downloads app is mounted under `/api/v1/downloads/`
        const [downloadsRes, filesRes] = await Promise.all([
          api.get('/downloads/downloads/'),
          api.get('/downloads/files/'),
        ]);

        const dlData = Array.isArray(downloadsRes.data) ? downloadsRes.data : (downloadsRes.data?.results || []);
        const fileData = Array.isArray(filesRes.data) ? filesRes.data : (filesRes.data?.results || []);

        setDownloads(dlData);
        setFiles(fileData);
      } catch (err) {
        console.error('Failed to fetch downloads:', err);
        setDownloads([]);
        setFiles([]);
      } finally {
        setLoading(false);
      }
    };
    fetchDownloads();
  }, []);

  const filteredDownloads = filter === 'all' ? downloads : downloads.filter(d => d.status === filter);
  const totalBytes = downloads
    .filter(d => d.status === 'completed')
    .reduce((sum, d) => sum + (d.file_size_bytes || 0), 0);
  const totalBytesGB = (totalBytes / 1024 / 1024 / 1024).toFixed(2);
  const pendingCount = downloads.filter(d => d.status === 'pending' || d.status === 'downloading').length;
  const completedCount = downloads.filter(d => d.status === 'completed').length;
  const failedCount = downloads.filter(d => d.status === 'failed').length;
  const successRate = (completedCount + failedCount) > 0
    ? ((completedCount / (completedCount + failedCount)) * 100).toFixed(1)
    : '—';

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: 'hsl(var(--background))' }}>
      <Sidebar />
      <main style={{ flex: 1, marginLeft: '240px', padding: '2.5rem' }}>
        <header style={{ marginBottom: '3rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ fontSize: '2.25rem', fontWeight: 'bold' }}>Download Center</h1>
            <p style={{ color: 'hsl(var(--muted-foreground))', marginTop: '0.5rem' }}>Monitor and manage all media extracted by your bots.</p>
          </div>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <div className="glass" style={{ display: 'flex', padding: '4px', gap: '4px' }}>
              {['all', 'completed', 'downloading', 'failed'].map(f => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  style={{
                    padding: '6px 12px',
                    borderRadius: 'calc(var(--radius) - 4px)',
                    fontSize: '0.75rem',
                    textTransform: 'capitalize',
                    border: 'none',
                    backgroundColor: filter === f ? 'hsl(var(--primary))' : 'transparent',
                    color: filter === f ? 'hsl(var(--primary-foreground))' : 'hsl(var(--muted-foreground))',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>
        </header>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: '2rem' }}>
          {/* Main List */}
          <section style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ position: 'relative', marginBottom: '1rem' }}>
              <Search style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'hsl(var(--muted-foreground))' }} size={18} />
              <input
                type="text"
                placeholder="Search downloads..."
                style={{
                  width: '100%',
                  padding: '0.75rem 0.75rem 0.75rem 2.5rem',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: 'var(--radius)',
                  color: 'white',
                  outline: 'none',
                }}
              />
            </div>

            {loading ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
                <Loader2 className="animate-spin" size={32} />
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <AnimatePresence>
                  {filteredDownloads.map(dl => (
                    <DownloadItem key={dl.id} download={dl} />
                  ))}
                  {filteredDownloads.length === 0 && (
                    <div style={{ textAlign: 'center', padding: '4rem', color: 'hsl(var(--muted-foreground))' }}>
                      <Download size={48} style={{ marginBottom: '1rem', opacity: 0.2 }} />
                      <p>No downloads found matching your criteria.</p>
                    </div>
                  )}
                </AnimatePresence>
              </div>
            )}
          </section>

          {/* Activity/Stats Sidebar */}
          <aside style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div className="glass" style={{ padding: '1.5rem' }}>
              <h3 style={{ fontSize: '1.125rem', fontWeight: 'bold', marginBottom: '1.5rem' }}>Quick Stats</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '0.875rem', color: 'hsl(var(--muted-foreground))' }}>Total Downloaded</span>
                  <span style={{ fontWeight: 600 }}>{totalBytes ? `${totalBytesGB} GB` : '—'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '0.875rem', color: 'hsl(var(--muted-foreground))' }}>Pending Tasks</span>
                  <span style={{ fontWeight: 600 }}>{pendingCount}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '0.875rem', color: 'hsl(var(--muted-foreground))' }}>Success Rate</span>
                  <span style={{ fontWeight: 600, color: completedCount >= failedCount ? '#10b981' : '#ef4444' }}>
                    {successRate === '—' ? '—' : `${successRate}%`}
                  </span>
                </div>
              </div>
            </div>

            <div className="glass" style={{ padding: '1.5rem' }}>
              <h3 style={{ fontSize: '1.125rem', fontWeight: 'bold', marginBottom: '1.25rem' }}>Media Gallery</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                {(files.slice(0, 4)).map((f) => (
                  <div key={f.id} style={{
                    aspectRatio: '1', 
                    borderRadius: '8px', 
                    backgroundColor: 'rgba(255,255,255,0.05)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'rgba(255,255,255,0.1)'
                  }}>
                    <FileImage size={24} />
                  </div>
                ))}
              </div>
              <button className="btn" style={{ width: '100%', marginTop: '1rem', border: '1px solid hsl(var(--border))', fontSize: '0.8125rem' }}>
                View Full Gallery
              </button>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
};

export default DownloadCenter;
