import React from 'react';
import { motion } from 'framer-motion';
import { Mail, Shield, Lock, FileText, ExternalLink } from 'lucide-react';

const HelpPage = () => {
  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: 'hsl(var(--background))' }}>
      <main style={{ flex: 1, padding: '4rem 2.5rem', maxWidth: '1000px', margin: '0 auto' }}>
        <header style={{ marginBottom: '4rem', textAlign: 'center' }}>
          <h1 style={{ fontSize: '3rem', fontWeight: 'bold' }}>InstaBot <span style={{ color: 'hsl(var(--primary))' }}>Help Center</span></h1>
          <p style={{ color: 'hsl(var(--muted-foreground))', marginTop: '1rem', fontSize: '1.25rem' }}>Guidance, documentation, and technical support.</p>
        </header>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem', marginBottom: '4rem' }}>
          <motion.div whileHover={{ y: -5 }} className="glass" style={{ padding: '2rem' }}>
            <div style={{ padding: '0.75rem', backgroundColor: 'rgba(59, 130, 246, 0.1)', color: 'hsl(var(--primary))', borderRadius: '12px', width: 'fit-content', marginBottom: '1.5rem' }}>
              <FileText size={28} />
            </div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', marginBottom: '0.75rem' }}>User Guide</h3>
            <p style={{ color: 'hsl(var(--muted-foreground))', fontSize: '0.9375rem', lineHeight: 1.6 }}>Learn how to set up your bots, configure proxies, and manage multiple accounts efficiently.</p>
            <button className="btn" style={{ marginTop: '1.5rem', border: '1px solid hsl(var(--border))', width: '100%' }}>Read Documentation</button>
          </motion.div>

          <motion.div whileHover={{ y: -5 }} className="glass" style={{ padding: '2rem' }}>
            <div style={{ padding: '0.75rem', backgroundColor: 'rgba(16, 185, 129, 0.1)', color: '#10b981', borderRadius: '12px', width: 'fit-content', marginBottom: '1.5rem' }}>
              <Shield size={28} />
            </div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', marginBottom: '0.75rem' }}>Safety & Privacy</h3>
            <p style={{ color: 'hsl(var(--muted-foreground))', fontSize: '0.9375rem', lineHeight: 1.6 }}>Best practices for maintaining high trust scores and avoiding Instagram's automated flags.</p>
            <button className="btn" style={{ marginTop: '1.5rem', border: '1px solid hsl(var(--border))', width: '100%' }}>View Guidelines</button>
          </motion.div>

          <motion.div whileHover={{ y: -5 }} className="glass" style={{ padding: '2rem' }}>
            <div style={{ padding: '0.75rem', backgroundColor: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', borderRadius: '12px', width: 'fit-content', marginBottom: '1.5rem' }}>
              <Mail size={28} />
            </div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', marginBottom: '0.75rem' }}>Technical Support</h3>
            <p style={{ color: 'hsl(var(--muted-foreground))', fontSize: '0.9375rem', lineHeight: 1.6 }}>Encountering errors? Reach out to our team via our 24/7 support ticketing system.</p>
            <button className="btn btn-primary" style={{ marginTop: '1.5rem', width: '100%' }}>Contact Support</button>
          </motion.div>
        </div>

        <section className="glass" style={{ padding: '2.5rem' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '1.5rem' }}>Frequently Asked Questions</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {[
              { q: 'How many accounts can I run simultaneously?', a: 'Standard license supports up to 5 concurrent accounts, while Enterprise allows unlimited scaling.' },
              { q: 'What kind of proxies do you recommend?', a: 'We highly recommend High-Quality Residential or Mobile (4G/LTE) proxies for the best trust scores.' },
              { q: 'Will I get banned for using this tool?', a: 'Our tool implements humanized behavior emulation, but you should always follow our Safety Guidelines to minimize risk.' }
            ].map((faq, i) => (
              <div key={i} style={{ paddingBottom: '1.5rem', borderBottom: '1px solid hsl(var(--border))' }}>
                <h4 style={{ fontWeight: 600, marginBottom: '0.5rem' }}>{faq.q}</h4>
                <p style={{ color: 'hsl(var(--muted-foreground))', fontSize: '0.9375rem' }}>{faq.a}</p>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
};

export default HelpPage;
