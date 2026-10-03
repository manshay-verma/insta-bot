import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { 
  BarChart3, 
  Users, 
  Settings, 
  Download, 
  Play, 
  LogOut, 
  LayoutDashboard,
  ShieldCheck,
  Menu,
  X,
  Database,
  ShieldAlert,
  HelpCircle,
  FileBox,
  Image as ImageIcon
} from 'lucide-react';
import { useAuthStore } from '../store/useAuthStore';
import { motion, AnimatePresence } from 'framer-motion';

const Sidebar = () => {
  const logout = useAuthStore(state => state.logout);
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);

  const navItems = [
    { name: 'Dashboard', icon: <LayoutDashboard size={20} />, path: '/' },
    { name: 'Accounts', icon: <Users size={20} />, path: '/accounts' },
    { name: 'Bot Controls', icon: <Play size={20} />, path: '/bot' },
    { name: 'Rate Limits', icon: <ShieldAlert size={20} />, path: '/rate-limits' },
    { name: 'Downloads', icon: <Download size={20} />, path: '/downloads' },
    { name: 'Gallery', icon: <ImageIcon size={20} />, path: '/gallery' },
    { name: 'Analytics', icon: <BarChart3 size={20} />, path: '/analytics' },
    { name: 'Export Data', icon: <FileBox size={20} />, path: '/export' },
    { name: 'Settings', icon: <Settings size={20} />, path: '/settings' },
    { name: 'Help Hub', icon: <HelpCircle size={20} />, path: '/help' },
  ];

  const toggleSidebar = () => setIsOpen(!isOpen);

  return (
    <>
      {/* Mobile Toggle Button */}
      <button 
        onClick={toggleSidebar}
        style={{
          position: 'fixed',
          top: '1rem',
          left: '1rem',
          zIndex: 1000,
          padding: '0.5rem',
          backgroundColor: 'hsl(var(--primary))',
          borderRadius: '8px',
          border: 'none',
          color: 'white',
          display: 'none', // Overridden by media query
        }}
        className="mobile-toggle"
      >
        {isOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      <aside 
        className={isOpen ? "sidebar-open" : "sidebar-closed"}
        style={{
          width: '240px',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          backgroundColor: 'rgba(15, 23, 42, 0.98)',
          borderRight: '1px solid hsl(var(--border))',
          display: 'flex',
          flexDirection: 'column',
          padding: '1.5rem',
          zIndex: 100,
          transition: 'transform 0.3s ease-in-out',
        }}
      >
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '0.75rem', 
          marginBottom: '2.5rem',
          paddingLeft: '0.5rem' 
        }}>
          <div style={{
            padding: '0.5rem',
            borderRadius: '10px',
            backgroundColor: 'hsl(var(--primary))',
            color: 'hsl(var(--primary-foreground))'
          }}>
            <ShieldCheck size={24} />
          </div>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 'bold', letterSpacing: '-0.5px' }}>InstaBot</h1>
        </div>

        <nav style={{ flex: 1, overflowY: 'auto', marginRight: '-0.5rem', paddingRight: '0.5rem' }}>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {navItems.map((item) => (
              <li key={item.name} style={{ marginBottom: '0.25rem' }}>
                <NavLink
                  to={item.path}
                  onClick={() => setIsOpen(false)}
                  style={({ isActive }) => ({
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                    padding: '0.75rem 1rem',
                    borderRadius: 'var(--radius)',
                    color: isActive ? 'white' : 'hsl(var(--muted-foreground))',
                    backgroundColor: isActive ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
                    textDecoration: 'none',
                    transition: 'all 0.2s',
                    fontWeight: isActive ? 600 : 400,
                    fontSize: '0.875rem'
                  })}
                >
                  {item.icon}
                  <span>{item.name}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <div style={{ marginTop: 'auto', borderTop: '1px solid hsl(var(--border))', paddingTop: '1rem' }}>
          <button 
            onClick={() => {
              logout();
              navigate('/login');
            }}
            className="btn"
            style={{ 
              width: '100%', 
              justifyContent: 'flex-start', 
              gap: '0.75rem', 
              color: '#ef4444',
              padding: '0.75rem 1rem'
            }}
          >
            <LogOut size={20} />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Screen Overlay for Mobile */}
      <AnimatePresence>
        {isOpen && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsOpen(false)}
            style={{
              position: 'fixed',
              inset: 0,
              backgroundColor: 'rgba(0,0,0,0.5)',
              zIndex: 90,
              backdropFilter: 'blur(4px)',
            }}
          />
        )}
      </AnimatePresence>

      <style dangerouslySetInnerHTML={{ __html: `
        @media (max-width: 768px) {
          .mobile-toggle { display: block !important; }
          aside.sidebar-closed { transform: translateX(-100%); }
          aside.sidebar-open { transform: translateX(0); }
        }
      `}} />
    </>
  );
};

export default Sidebar;
