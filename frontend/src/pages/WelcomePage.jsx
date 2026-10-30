import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Cpu, ArrowRight, ShieldCheck, Activity, Eye } from 'lucide-react';

const WelcomePage = () => {
  const navigate = useNavigate();

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      background: 'linear-gradient(180deg, #ffffff 0%, var(--brand-cream) 55%, #f3e7cc 100%)',
      padding: '24px',
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* College colour band, as on glbitm.org */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: '8px',
        background: 'linear-gradient(90deg, var(--brand-maroon) 0%, var(--brand-maroon) 70%, var(--brand-gold) 70%)'
      }}></div>

      <div style={{
        maxWidth: '800px',
        width: '100%',
        textAlign: 'center',
        zIndex: 1
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          marginBottom: '28px'
        }}>
          <div style={{
            background: '#ffffff',
            padding: '10px 22px',
            borderRadius: '14px',
            border: '1px solid var(--border-subtle)',
            boxShadow: 'var(--shadow-md)'
          }}>
            <img
              src="/glb-logo.png"
              alt="GL Bajaj Institute of Technology & Management"
              style={{ display: 'block', height: 'clamp(64px, 10vw, 92px)', maxWidth: '100%', objectFit: 'contain' }}
            />
          </div>
        </div>

        {/* Brand Badge */}
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          background: 'rgba(240, 177, 0, 0.14)',
          border: '1px solid rgba(240, 177, 0, 0.5)',
          padding: '6px 18px',
          borderRadius: '9999px',
          color: 'var(--primary)',
          fontSize: '13px',
          fontWeight: 700,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          marginBottom: '24px'
        }}>
          <Cpu size={16} />
          EDGE AI &amp; YOLOV8 SURVEILLANCE
        </div>

        {/* Mandatory exact heading */}
        <h1 style={{
          fontSize: 'clamp(40px, 6vw, 68px)',
          fontWeight: 900,
          color: 'var(--brand-maroon)',
          letterSpacing: '-0.03em',
          lineHeight: 1.1,
          marginBottom: '14px'
        }}>
          WELCOME BACK
        </h1>

        {/* Project Name */}
        <h2 style={{
          fontSize: 'clamp(20px, 3.5vw, 32px)',
          fontWeight: 800,
          color: 'var(--brand-copper)',
          letterSpacing: '-0.01em',
          marginBottom: '16px'
        }}>
          SMART GARBAGE DETECTION SYSTEM
        </h2>

        {/* Subtitle */}
        <p style={{
          fontSize: '18px',
          color: 'var(--text-secondary)',
          maxWidth: '600px',
          margin: '0 auto 36px auto',
          lineHeight: 1.6
        }}>
          AI Powered Real-Time Waste Monitoring &amp; Dual-ROI Fill Level Estimation
        </p>

        {/* Feature Highlights Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '16px',
          marginBottom: '44px',
          textAlign: 'left'
        }}>
          <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderTop: '3px solid var(--brand-gold)', borderRadius: '12px', padding: '16px', boxShadow: 'var(--shadow-sm)' }}>
            <Activity size={20} style={{ color: 'var(--primary)', marginBottom: '8px' }} />
            <h4 style={{ fontSize: '14px', color: 'var(--brand-maroon)', fontWeight: 700 }}>Real-Time Stream</h4>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Continuous IP Webcam feed with resilient reconnection.</p>
          </div>
          <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderTop: '3px solid var(--brand-gold)', borderRadius: '12px', padding: '16px', boxShadow: 'var(--shadow-sm)' }}>
            <Eye size={20} style={{ color: 'var(--accent-cyan)', marginBottom: '8px' }} />
            <h4 style={{ fontSize: '14px', color: 'var(--brand-maroon)', fontWeight: 700 }}>Dual-ROI Vision</h4>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Simultaneous bin interior fill &amp; floor overflow detection.</p>
          </div>
          <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderTop: '3px solid var(--brand-gold)', borderRadius: '12px', padding: '16px', boxShadow: 'var(--shadow-sm)' }}>
            <ShieldCheck size={20} style={{ color: 'var(--warning)', marginBottom: '8px' }} />
            <h4 style={{ fontSize: '14px', color: 'var(--brand-maroon)', fontWeight: 700 }}>85% Auto Alert</h4>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Instant SMTP email dispatch with snapshot evidence.</p>
          </div>
        </div>

        {/* Action Button */}
        <div>
          <button
            className="btn btn-primary"
            style={{
              padding: '16px 38px',
              fontSize: '17px',
              borderRadius: '9999px',
              boxShadow: '0 8px 24px rgba(89, 33, 6, 0.25)',
              letterSpacing: '0.04em'
            }}
            onClick={() => navigate('/login')}
          >
            ENTER PORTAL
            <ArrowRight size={20} />
          </button>
        </div>

        <div style={{ marginTop: '48px', fontSize: '12px', color: 'var(--text-secondary)' }}>
          Department of CSE (AIML) • GL Bajaj Institute of Technology &amp; Management • Session 2025-2026
        </div>
      </div>
    </div>
  );
};

export default WelcomePage;
