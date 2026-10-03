import React, { useState, useEffect } from 'react';
import Sidebar from '../components/Sidebar';
import AccountModal from '../components/AccountModal';
import api from '../services/api';
import { 
  Plus, 
  Search, 
  Filter, 
  MoreVertical, 
  Shield, 
  Activity, 
  Trash2, 
  Settings,
  AlertCircle,
  Loader2,
  CheckSquare,
  Square,
  Trash
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const AccountList = () => {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState(null);
  const [selectedIds, setSelectedIds] = useState(new Set());

  useEffect(() => {
    fetchAccounts();
  }, []);

  const normalizeAccountsResponse = (data) => {
    const list = Array.isArray(data) ? data : (data?.results || []);
    return list.map((acc) => {
      const trust = typeof acc.trust_score === 'number'
        ? acc.trust_score
        : parseFloat(acc.trust_score ?? '0');
      const trustPct = Number.isFinite(trust) ? Math.round(trust * 100) : 0;
      const lastActivity = acc.last_login ? new Date(acc.last_login).toLocaleString() : '—';
      return {
        ...acc,
        trust_score: trustPct,
        last_activity: lastActivity,
      };
    });
  };

  const fetchAccounts = async () => {
    try {
      const response = await api.get('/accounts/');
      setAccounts(normalizeAccountsResponse(response.data));
    } catch (err) {
      console.error('Failed to fetch accounts:', err);
      setAccounts([]);
    } finally {
      setLoading(false);
    }
  };

  const saveAccount = async (formData) => {
    // Backend expects: username, password (create only), status, proxy (id or null)
    const payload = {
      username: formData.username,
      status: formData.status || 'active',
      proxy: formData.proxy ? Number(formData.proxy) : null,
    };

    if (selectedAccount?.id) {
      // Update (password changes not supported by current backend serializer)
      const res = await api.patch(`/accounts/${selectedAccount.id}/`, payload);
      return res.data;
    }

    const res = await api.post('/accounts/', {
      ...payload,
      password: formData.password,
    });
    return res.data;
  };

  const deleteAccount = async (accountId) => {
    if (!window.confirm('Delete this account?')) return;
    await api.delete(`/accounts/${accountId}/`);
    await fetchAccounts();
  };

  const toggleSelect = (id) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) newSelected.delete(id);
    else newSelected.add(id);
    setSelectedIds(newSelected);
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === filteredAccounts.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredAccounts.map(a => a.id)));
    }
  };

  const deleteBulk = async () => {
    if (!window.confirm(`Delete ${selectedIds.size} accounts?`)) return;
    await Promise.allSettled([...selectedIds].map((id) => api.delete(`/accounts/${id}/`)));
    setSelectedIds(new Set());
    await fetchAccounts();
  };

  const filteredAccounts = accounts.filter(acc => 
    acc.username.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: 'hsl(var(--background))' }}>
      <Sidebar />
      
      <main style={{ flex: 1, marginLeft: '240px', padding: '2.5rem' }}>
        <header style={{ marginBottom: '3rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ fontSize: '2.25rem', fontWeight: 'bold' }}>Account Management</h1>
            <p style={{ color: 'hsl(var(--muted-foreground))', marginTop: '0.25rem' }}>Monitor and manage your Instagram bot farm.</p>
          </div>
          <button 
            className="btn btn-primary" 
            style={{ gap: '8px' }}
            onClick={() => { setSelectedAccount(null); setIsModalOpen(true); }}
          >
            <Plus size={18} /> Add Account
          </button>
        </header>

        {/* Toolbar */}
        <div style={{ marginBottom: '2rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'hsl(var(--muted-foreground))' }} size={18} />
            <input 
              type="text" 
              placeholder="Search by username or status..." 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{ width: '100%', padding: '0.75rem 1rem 0.75rem 2.75rem', backgroundColor: 'rgba(255,255,255,0.05)', border: '1px solid hsl(var(--border))', borderRadius: 'var(--radius)', color: 'white', outline: 'none' }} 
            />
          </div>
          
          <AnimatePresence>
            {selectedIds.size > 0 && (
              <motion.div 
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}
              >
                <span style={{ fontSize: '0.875rem', marginRight: '0.5rem', color: 'hsl(var(--primary))' }}>{selectedIds.size} Selected</span>
                <button className="btn" style={{ borderColor: '#ef4444', color: '#ef4444', gap: '0.5rem' }} onClick={deleteBulk}>
                  <Trash size={16} /> Bulk Delete
                </button>
              </motion.div>
            )}
          </AnimatePresence>
          <button className="btn" style={{ gap: '8px', border: '1px solid hsl(var(--border))' }}>
            <Filter size={18} /> Filter
          </button>
        </div>

        {/* Account Table with Bulk Select */}
        <div className="glass" style={{ padding: '0', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid hsl(var(--border))', background: 'rgba(255,255,255,0.02)' }}>
                <th style={{ padding: '1.25rem', width: '50px' }}>
                  <button onClick={toggleSelectAll} style={{ border: 'none', background: 'none', color: 'hsl(var(--primary))', cursor: 'pointer' }}>
                    {selectedIds.size === filteredAccounts.length && filteredAccounts.length > 0 ? <CheckSquare size={20} /> : <Square size={20} />}
                  </button>
                </th>
                <th style={{ padding: '1.25rem', fontSize: '0.875rem', fontWeight: 600 }}>Account</th>
                <th style={{ padding: '1.25rem', fontSize: '0.875rem', fontWeight: 600 }}>Status</th>
                <th style={{ padding: '1.25rem', fontSize: '0.875rem', fontWeight: 600 }}>Health</th>
                <th style={{ padding: '1.25rem', fontSize: '0.875rem', fontWeight: 600 }}>Last Activity</th>
                <th style={{ padding: '1.25rem' }}></th>
              </tr>
            </thead>
            <tbody>
              {filteredAccounts.map((acc) => (
                <motion.tr 
                  layout
                  key={acc.id} 
                  style={{ 
                    borderBottom: '1px solid rgba(255,255,255,0.05)',
                    backgroundColor: selectedIds.has(acc.id) ? 'rgba(59, 130, 246, 0.05)' : 'transparent'
                  }}
                >
                  <td style={{ padding: '1.25rem' }}>
                    <button onClick={() => toggleSelect(acc.id)} style={{ border: 'none', background: 'none', color: selectedIds.has(acc.id) ? 'hsl(var(--primary))' : 'rgba(255,255,255,0.2)', cursor: 'pointer' }}>
                      {selectedIds.has(acc.id) ? <CheckSquare size={20} /> : <Square size={20} />}
                    </button>
                  </td>
                  <td style={{ padding: '1.25rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', fontSize: '0.75rem' }}>
                        {acc.username[0].toUpperCase()}
                      </div>
                      <span style={{ fontWeight: 500 }}>{acc.username}</span>
                    </div>
                  </td>
                  <td style={{ padding: '1.25rem' }}>
                    <span style={{ 
                      padding: '4px 8px', borderRadius: '4px', fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase',
                      backgroundColor: acc.status === 'active' ? 'rgba(16, 185, 129, 0.1)' : acc.status === 'error' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(255,255,255,0.05)',
                      color: acc.status === 'active' ? '#10b981' : acc.status === 'error' ? '#ef4444' : 'hsl(var(--muted-foreground))'
                    }}>
                      {acc.status}
                    </span>
                  </td>
                  <td style={{ padding: '1.25rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ flex: 1, height: '6px', backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: '3px', maxWidth: '100px' }}>
                        <div style={{ width: `${acc.trust_score}%`, height: '100%', borderRadius: '3px', backgroundColor: acc.trust_score > 80 ? '#10b981' : acc.trust_score > 50 ? '#f59e0b' : '#ef4444' }} />
                      </div>
                      <span style={{ fontSize: '0.75rem', fontWeight: 600 }}>{acc.trust_score}%</span>
                    </div>
                  </td>
                  <td style={{ padding: '1.25rem', fontSize: '0.875rem', color: 'hsl(var(--muted-foreground))' }}>{acc.last_activity}</td>
                  <td style={{ padding: '1.25rem', textAlign: 'right' }}>
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                      <button
                        className="btn"
                        style={{ padding: '6px', minHeight: 'unset' }}
                        onClick={() => { setSelectedAccount(acc); setIsModalOpen(true); }}
                        title="Edit account"
                      >
                        <Settings size={16} />
                      </button>
                      <button
                        className="btn"
                        style={{ padding: '6px', minHeight: 'unset', borderColor: 'rgba(239,68,68,0.4)', color: '#ef4444' }}
                        onClick={() => deleteAccount(acc.id)}
                        title="Delete account"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>

        {isModalOpen && (
          <AccountModal 
            isOpen={isModalOpen}
            onClose={() => setIsModalOpen(false)}
            onSave={async (data) => {
              await saveAccount(data);
              await fetchAccounts();
            }}
            mode={selectedAccount ? 'edit' : 'add'}
            initialData={{
              username: selectedAccount?.username || '',
              status: selectedAccount?.status || 'active',
              proxy: selectedAccount?.proxy || '',
            }}
          />
        )}
      </main>
    </div>
  );
};

export default AccountList;
