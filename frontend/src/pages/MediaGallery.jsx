import React, { useEffect, useMemo, useState } from 'react';
import Sidebar from '../components/Sidebar';
import api from '../services/api';
import { 
  FileVideo, 
  FileImage, 
  Search, 
  Filter, 
  Play, 
  Grid, 
  List,
  MoreVertical,
  Download,
  Trash2,
  ExternalLink,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const MediaGallery = () => {
  const [view, setView] = useState('grid');
  const [category, setCategory] = useState('all');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [mediaItems, setMediaItems] = useState([]);

  useEffect(() => {
    const fetchFiles = async () => {
      try {
        const res = await api.get('/downloads/files/');
        const rows = Array.isArray(res.data) ? res.data : (res.data?.results || []);
        setMediaItems(rows.map((f) => ({
          id: f.id,
          type: (f.content_type || '').startsWith('video') ? 'video' : 'image',
          title: f.filename,
          size: f.file_size ? `${(f.file_size / 1024 / 1024).toFixed(2)} MB` : '—',
          date: f.created_at ? new Date(f.created_at).toLocaleString() : '—',
          url: f.s3_url || null,
        })));
      } catch (e) {
        console.error('Failed to fetch media files:', e);
        setMediaItems([]);
      } finally {
        setLoading(false);
      }
    };
    fetchFiles();
  }, []);

  const filtered = useMemo(() => {
    return mediaItems.filter((item) => {
      const matchCategory = category === 'all'
        || (category === 'videos' && item.type === 'video')
        || (category === 'images' && item.type === 'image');
      const matchSearch = !search.trim() || item.title.toLowerCase().includes(search.trim().toLowerCase());
      return matchCategory && matchSearch;
    });
  }, [mediaItems, category, search]);

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: 'hsl(var(--background))' }}>
      <Sidebar />
      <main style={{ flex: 1, marginLeft: '240px', padding: '2.5rem' }}>
        <header style={{ marginBottom: '3rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ fontSize: '2.25rem', fontWeight: 'bold' }}>Media Gallery</h1>
            <p style={{ color: 'hsl(var(--muted-foreground))', marginTop: '0.5rem' }}>Browse and manage all downloaded assets.</p>
          </div>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <div className="glass" style={{ display: 'flex', padding: '4px', gap: '4px' }}>
              <button 
                onClick={() => setView('grid')}
                style={{ padding: '8px', borderRadius: '4px', backgroundColor: view === 'grid' ? 'rgba(255,255,255,0.1)' : 'transparent', border: 'none', color: 'white', cursor: 'pointer' }}
              >
                <Grid size={18} />
              </button>
              <button 
                onClick={() => setView('list')}
                style={{ padding: '8px', borderRadius: '4px', backgroundColor: view === 'list' ? 'rgba(255,255,255,0.1)' : 'transparent', border: 'none', color: 'white', cursor: 'pointer' }}
              >
                <List size={18} />
              </button>
            </div>
            <button className="btn btn-primary" style={{ gap: '0.5rem' }}>
              <Download size={18} /> Sync Cloud
            </button>
          </div>
        </header>

        <div style={{ marginBottom: '2rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'hsl(var(--muted-foreground))' }} size={18} />
            <input 
              type="text" 
              placeholder="Search by title or account..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ width: '100%', padding: '0.75rem 1rem 0.75rem 2.75rem', backgroundColor: 'rgba(255,255,255,0.05)', border: '1px solid hsl(var(--border))', borderRadius: 'var(--radius)', color: 'white', outline: 'none' }} 
            />
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {['All', 'Videos', 'Images'].map(c => (
              <button 
                key={c}
                onClick={() => setCategory(c.toLowerCase())}
                className="btn" 
                style={{ border: category === c.toLowerCase() ? '1px solid hsl(var(--primary))' : '1px solid hsl(var(--border))' }}
              >
                {c}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="glass" style={{ padding: '2rem', color: 'hsl(var(--muted-foreground))' }}>
            Loading media...
          </div>
        ) : view === 'grid' ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1.5rem' }}>
            {filtered.map(item => (
              <motion.div 
                key={item.id} 
                whileHover={{ y: -5 }}
                className="glass" 
                style={{ padding: '0', overflow: 'hidden' }}
              >
                <div style={{ aspectRatio: '16/9', backgroundColor: 'rgba(255,255,255,0.02)', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
                  {item.type === 'video' ? <FileVideo size={48} color="rgba(255,255,255,0.1)" /> : <FileImage size={48} color="rgba(255,255,255,0.1)" />}
                  <div style={{ position: 'absolute', bottom: '10px', right: '10px', padding: '4px 8px', backgroundColor: 'rgba(0,0,0,0.6)', borderRadius: '4px', fontSize: '0.7rem' }}>
                    {item.size}
                  </div>
                  {item.type === 'video' && (
                    <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(1/-50%, -50%)', padding: '12px', borderRadius: '50%', backgroundColor: 'rgba(59, 130, 246, 0.8)', color: 'white' }}>
                      <Play size={24} fill="white" />
                    </div>
                  )}
                </div>
                <div style={{ padding: '1.25rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                    <h4 style={{ fontWeight: 600 }}>{item.title}</h4>
                    <MoreVertical size={16} color="hsl(var(--muted-foreground))" />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: 'hsl(var(--muted-foreground))' }}>
                    <span>{item.date}</span>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button
                        style={{ border: 'none', background: 'none', color: 'hsl(var(--muted-foreground))', cursor: item.url ? 'pointer' : 'not-allowed', opacity: item.url ? 1 : 0.4 }}
                        onClick={() => item.url && window.open(item.url, '_blank')}
                        title={item.url ? 'Open file' : 'No URL available'}
                      >
                        <ExternalLink size={14} />
                      </button>
                      <button style={{ border: 'none', background: 'none', color: '#ef4444', cursor: 'pointer' }}><Trash2 size={14} /></button>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        ) : (
          <div className="glass" style={{ padding: '0' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid hsl(var(--border))' }}>
                  <th style={{ padding: '1.25rem' }}>Name</th>
                  <th style={{ padding: '1.25rem' }}>Type</th>
                  <th style={{ padding: '1.25rem' }}>Size</th>
                  <th style={{ padding: '1.25rem' }}>Date</th>
                  <th style={{ padding: '1.25rem' }}></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(item => (
                  <tr key={item.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <td style={{ padding: '1.25rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
                      {item.type === 'video' ? <FileVideo size={18} /> : <FileImage size={18} />}
                      {item.title}
                    </td>
                    <td style={{ padding: '1.25rem', textTransform: 'capitalize' }}>{item.type}</td>
                    <td style={{ padding: '1.25rem' }}>{item.size}</td>
                    <td style={{ padding: '1.25rem' }}>{item.date}</td>
                    <td style={{ padding: '1.25rem', textAlign: 'right' }}>
                      <button className="btn" style={{ padding: '6px', minHeight: 'unset' }}><Download size={16} /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <footer style={{ marginTop: '3rem', display: 'flex', justifyContent: 'center', gap: '0.5rem', alignItems: 'center' }}>
          <button className="btn" style={{ padding: '8px' }}><ChevronLeft size={20} /></button>
          {[1, 2, 3].map(p => (
            <button key={p} className="btn" style={{ minWidth: '40px', backgroundColor: p === 1 ? 'hsl(var(--primary))' : 'transparent' }}>{p}</button>
          ))}
          <button className="btn" style={{ padding: '8px' }}><ChevronRight size={20} /></button>
        </footer>
      </main>
    </div>
  );
};

export default MediaGallery;
