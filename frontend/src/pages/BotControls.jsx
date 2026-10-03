import React, { useState, useEffect } from 'react';
import Sidebar from '../components/Sidebar';
import Alert from '../components/Alert';
import api from '../services/api';
import { 
  Play, 
  Terminal, 
  Settings, 
  Target, 
  Zap,
  Pause,
  RotateCcw,
  Plus,
  Monitor,
  User,
  ListFilter,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const BotControls = () => {
  const [isRunning, setIsRunning] = useState(false);
  const [accounts, setAccounts] = useState([]);
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  const [selectedAccountId, setSelectedAccountId] = useState('');
  const [selectedAction, setSelectedAction] = useState('like');
  const [executionMode, setExecutionMode] = useState('sync'); // sync | async
  const [targetsInput, setTargetsInput] = useState('');
  const [logs, setLogs] = useState([
    { time: new Date().toLocaleTimeString(), type: 'info', msg: 'System initialized. Waiting for task configuration...' },
  ]);
  const [alerts, setAlerts] = useState([]);

  // Fetch bot accounts on component mount
  useEffect(() => {
    const fetchAccounts = async () => {
      try {
        setLoadingAccounts(true);
        const response = await api.get('/accounts/');
        // Check if response.data is an array (it might be nested depending on DRF setup)
        const accountData = Array.isArray(response.data) ? response.data : response.data.results || [];
        const activeAccounts = accountData.filter(acc => acc.status === 'active');
        setAccounts(activeAccounts);
        if (activeAccounts.length > 0) {
          setSelectedAccountId(activeAccounts[0].id);
        }
      } catch (err) {
        console.error('Failed to fetch accounts:', err);
        addAlert('error', 'Could not fetch bot accounts. Please check backend connection.');
      } finally {
        setLoadingAccounts(false);
      }
    };

    fetchAccounts();
  }, []);

  const addLog = (type, msg) => {
    setLogs(prev => [{
      time: new Date().toLocaleTimeString(),
      type,
      msg
    }, ...prev]);
  };

  const addAlert = (type, message) => {
    setAlerts(prev => [...prev, { id: Date.now(), type, message }]);
  };

  const startBot = async () => {
    if (!selectedAccountId) {
      addAlert('warning', 'Please select a bot account first.');
      return;
    }

    if (!targetsInput.trim()) {
      addAlert('warning', 'Please enter at least one target username or URL.');
      return;
    }

    const targets = targetsInput.split(',').map(t => t.trim()).filter(Boolean);
    
    setIsRunning(true);
    addLog('process', `Initiating mission: ${selectedAction.toUpperCase()} targets: ${targets.join(', ')}`);

    try {
      if (executionMode === 'async') {
        const queued = await api.post('/bot/execute/async/', {
          account_id: parseInt(selectedAccountId),
          action: selectedAction,
          targets: targets
        });

        const taskId = queued.data.task_id;
        addLog('process', `Queued async task: ${taskId}`);

        const poll = async () => {
          const statusRes = await api.get(`/bot/task/${taskId}/`);
          const s = statusRes.data.status;
          if (s === 'PENDING' || s === 'STARTED' || s === 'RETRY') {
            return null;
          }
          return statusRes.data;
        };

        let done = null;
        for (let i = 0; i < 120; i++) { // ~4 minutes max
          await new Promise(r => setTimeout(r, 2000));
          done = await poll();
          if (done) break;
        }

        if (!done) {
          addLog('error', 'Async task timed out while waiting for result.');
          addAlert('warning', 'Task is still running. Check worker logs or poll status endpoint.');
        } else if (done.status === 'SUCCESS') {
          const result = done.result || {};
          if (result.success) {
            addLog('success', `Async Success: processed ${result.items_processed || 0}`);
            addAlert('info', `Async task completed. Processed: ${result.items_processed || 0}`);
          } else {
            const errorMsg = result.errors?.join(', ') || 'Unknown execution error';
            addLog('error', `Async Failed: ${errorMsg}`);
            addAlert('error', `Async execution failed: ${errorMsg}`);
          }
        } else {
          addLog('error', `Async task ended with status: ${done.status}`);
          addAlert('error', `Async task ended with status: ${done.status}`);
        }
      } else {
        const response = await api.post('/bot/execute/', {
          account_id: parseInt(selectedAccountId),
          action: selectedAction,
          targets: targets
        });

        if (response.data.success) {
          addLog('success', `Mission Successful: ${response.data.message || 'Complete'} (${response.data.items_processed} processed)`);
          addAlert('info', `Successfully executed ${selectedAction} for ${response.data.items_processed} targets.`);
        } else {
          const errorMsg = response.data.errors?.join(', ') || 'Unknown execution error';
          addLog('error', `Mission Failed: ${errorMsg}`);
          addAlert('error', `Execution failed: ${errorMsg}`);
        }
      }
    } catch (err) {
      console.error('Bot execution failed:', err);
      const errMsg = err.response?.data?.error || err.response?.data?.detail || err.message || 'Network error during execution.';
      addLog('error', `Fatal Error: ${errMsg}`);
      addAlert('error', `Execution blocked: ${errMsg}`);
    } finally {
      setIsRunning(false);
    }
  };

  const stopBot = () => {
    setIsRunning(false);
    addLog('error', 'Bot paused: Manual interruption received.');
  };

  const dismissAlert = (id) => setAlerts(alerts.filter(a => a.id !== id));

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: 'hsl(var(--background))' }}>
      <Sidebar />
      <main style={{ flex: 1, marginLeft: '240px', padding: '2.5rem' }}>
        <header style={{ marginBottom: '2.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ fontSize: '2.25rem', fontWeight: 'bold', color: 'white' }}>Mission Control</h1>
            <p style={{ color: 'hsl(var(--muted-foreground))', marginTop: '0.25rem' }}>Trigger and monitor live Instagram automation tasks.</p>
          </div>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <button 
              className={`btn ${isRunning ? 'btn-danger' : 'btn-primary'}`} 
              onClick={isRunning ? stopBot : startBot}
              disabled={isRunning}
              style={{ gap: '8px', minWidth: '160px', opacity: isRunning ? 0.7 : 1 }}
            >
              {isRunning ? <Pause size={18} /> : <Play size={18} />}
              {isRunning ? 'Running...' : 'Initiate Task'}
            </button>
          </div>
        </header>

        {/* Global Alert Zone */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '2.5rem' }}>
          <AnimatePresence>
            {alerts.map(a => (
              <Alert key={a.id} id={a.id} type={a.type} message={a.message} onDismiss={dismissAlert} />
            ))}
          </AnimatePresence>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1.8fr', gap: '2rem' }}>
          {/* Mission config */}
          <section className="glass" style={{ padding: '2rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2rem' }}>
              <Settings size={22} color="hsl(var(--primary))" />
              <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>Task Parameters</h3>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {/* Execution Mode */}
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', marginBottom: '0.5rem', color: 'hsl(var(--muted-foreground))' }}>
                  Execution Mode
                </label>
                <select
                  value={executionMode}
                  onChange={(e) => setExecutionMode(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.75rem 0.75rem',
                    backgroundColor: 'rgba(255,255,255,0.05)',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: 'var(--radius)',
                    color: 'white',
                    outline: 'none',
                    appearance: 'none',
                    cursor: 'pointer'
                  }}
                >
                  <option value="sync">Sync (wait for response)</option>
                  <option value="async">Async (Celery worker + polling)</option>
                </select>
              </div>
              {/* Account Selection */}
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', marginBottom: '0.5rem', color: 'hsl(var(--muted-foreground))' }}>Bot Account</label>
                <div style={{ position: 'relative' }}>
                  <User style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'hsl(var(--muted-foreground))' }} size={18} />
                  <select 
                    value={selectedAccountId}
                    onChange={(e) => setSelectedAccountId(e.target.value)}
                    style={{ 
                      width: '100%', 
                      padding: '0.75rem 0.75rem 0.75rem 2.5rem', 
                      backgroundColor: 'rgba(255,255,255,0.05)', 
                      border: '1px solid hsl(var(--border))', 
                      borderRadius: 'var(--radius)', 
                      color: 'white', 
                      outline: 'none',
                      appearance: 'none',
                      cursor: 'pointer'
                    }}
                  >
                    {loadingAccounts ? (
                      <option>Loading accounts...</option>
                    ) : (
                      <>
                        {accounts.length === 0 && <option value="">No active accounts found</option>}
                        {accounts.map(acc => (
                          <option key={acc.id} value={acc.id}>{acc.username}</option>
                        ))}
                      </>
                    )}
                  </select>
                </div>
              </div>

              {/* Action Selection */}
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', marginBottom: '0.5rem', color: 'hsl(var(--muted-foreground))' }}>Select Action</label>
                <div style={{ position: 'relative' }}>
                  <ListFilter style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'hsl(var(--muted-foreground))' }} size={18} />
                  <select 
                    value={selectedAction}
                    onChange={(e) => setSelectedAction(e.target.value)}
                    style={{ 
                      width: '100%', 
                      padding: '0.75rem 0.75rem 0.75rem 2.5rem', 
                      backgroundColor: 'rgba(255,255,255,0.05)', 
                      border: '1px solid hsl(var(--border))', 
                      borderRadius: 'var(--radius)', 
                      color: 'white', 
                      outline: 'none',
                      appearance: 'none',
                      cursor: 'pointer'
                    }}
                  >
                    <option value="like">Like Posts</option>
                    <option value="follow">Follow Users</option>
                    <option value="unfollow">Unfollow Users</option>
                    <option value="scrape_profile">Scrape Profile</option>
                    <option value="view_stories">View Stories</option>
                    <option value="comment">Comment on Post</option>
                  </select>
                </div>
              </div>

              {/* Targets Input */}
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', marginBottom: '0.5rem', color: 'hsl(var(--muted-foreground))' }}>Target Profiles / URLs (Comma separated)</label>
                <div style={{ position: 'relative' }}>
                  <Target style={{ position: 'absolute', left: '0.75rem', top: '0.75rem', color: 'hsl(var(--muted-foreground))' }} size={18} />
                  <textarea 
                    placeholder="@cristiano, @leomessi, https://instagram.com/p/xyz" 
                    value={targetsInput}
                    onChange={(e) => setTargetsInput(e.target.value)}
                    style={{ 
                      width: '100%', 
                      padding: '0.75rem 0.75rem 0.75rem 2.5rem', 
                      backgroundColor: 'rgba(255,255,255,0.05)', 
                      border: '1px solid hsl(var(--border))', 
                      borderRadius: 'var(--radius)', 
                      color: 'white', 
                      outline: 'none',
                      minHeight: '100px',
                      resize: 'vertical'
                    }} 
                  />
                </div>
              </div>
            </div>
          </section>

          {/* Console / Terminal Section */}
          <section className="glass" style={{ padding: '0', backgroundColor: '#020617', overflow: 'hidden', border: '1px solid rgba(255,255,255,0.1)' }}>
            <div style={{ padding: '0.75rem 1.25rem', backgroundColor: 'rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'hsl(var(--muted-foreground))' }}>
                <Terminal size={16} />
                <span style={{ fontSize: '0.75rem', fontWeight: 600, letterSpacing: '0.05em' }}>LIVE EXECUTION FEED</span>
              </div>
              <div style={{ display: 'flex', gap: '4px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#ef4444' }} />
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#f59e0b' }} />
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10b981' }} />
              </div>
            </div>
            
            <div style={{ padding: '1.5rem', height: '480px', overflowY: 'auto', fontFamily: '"JetBrains Mono", "Fira Code", monospace', fontSize: '0.8125rem', lineHeight: 1.6 }}>
              {logs.map((log, i) => (
                <div key={i} style={{ display: 'flex', gap: '1rem', marginBottom: '0.5rem' }}>
                  <span style={{ color: 'rgba(255,255,255,0.3)' }}>[{log.time}]</span>
                  <span style={{ 
                    color: log.type === 'error' ? '#ef4444' : log.type === 'process' ? '#3b82f6' : log.type === 'success' ? '#10b981' : '#f59e0b',
                    fontWeight: 700 
                  }}>
                    {log.type.toUpperCase()}
                  </span>
                  <span style={{ color: 'rgba(255,255,255,0.8)' }}>{log.msg}</span>
                </div>
              ))}
              {isRunning && (
                <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem' }}>
                  <span style={{ color: 'rgba(255,255,255,0.3)' }}>[{new Date().toLocaleTimeString()}]</span>
                  <span style={{ color: '#3b82f6', fontWeight: 700 }}>RUNTIME</span>
                  <span style={{ color: 'rgba(255,255,255,0.8)' }}>Executing automation engine in background...</span>
                  <motion.span 
                    animate={{ opacity: [0, 1] }} 
                    transition={{ repeat: Infinity, duration: 0.8 }}
                    style={{ backgroundColor: '#3b82f6', width: '8px', height: '14px', marginTop: '2px' }}
                  />
                </div>
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
};

export default BotControls;
