import React, { useState, useEffect } from 'react';
import { Mail, Save, Send, ShieldCheck, Key, Clock, AlertTriangle } from 'lucide-react';
import { emailSettingsService } from '../services/api';
import { useNotification } from '../context/NotificationContext';

const CaretakerSettingsPage = () => {
  const { showToast } = useNotification();

  const [formData, setFormData] = useState({
    caretaker_name: '',
    caretaker_email: '',
    backup_email: '',
    smtp_host: 'smtp.gmail.com',
    smtp_port: 587,
    smtp_username: '',
    smtp_password: '',
    alert_threshold: 85.0,
    cooldown_minutes: 15,
    email_alerts_enabled: true,
  });

  const [passwordConfigured, setPasswordConfigured] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [sendingTest, setSendingTest] = useState(false);
  const [testRecipient, setTestRecipient] = useState('');

  const fetchSettings = async () => {
    try {
      const res = await emailSettingsService.get();
      const s = res.data;
      setFormData({
        caretaker_name: s.caretaker_name,
        caretaker_email: s.caretaker_email,
        backup_email: s.backup_email || '',
        smtp_host: s.smtp_host,
        smtp_port: s.smtp_port,
        smtp_username: s.smtp_username,
        smtp_password: '', // Never populate existing password plaintext
        alert_threshold: s.alert_threshold,
        cooldown_minutes: s.cooldown_minutes,
        email_alerts_enabled: s.email_alerts_enabled,
      });
      setPasswordConfigured(s.smtp_password_configured);
      setTestRecipient(s.caretaker_email);
    } catch (err) {
      showToast('Failed to load email & caretaker settings', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        ...formData,
        alert_threshold: parseFloat(formData.alert_threshold),
        cooldown_minutes: parseInt(formData.cooldown_minutes),
      };
      if (!formData.smtp_password.trim()) {
        delete payload.smtp_password; // preserve existing password in DB
      }
      await emailSettingsService.update(payload);
      showToast('Caretaker & Email settings saved successfully.', 'success');
      fetchSettings();
    } catch (err) {
      showToast('Failed to save settings', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleSendTest = async () => {
    setSendingTest(true);
    try {
      const res = await emailSettingsService.sendTest(testRecipient || formData.caretaker_email);
      showToast(res.data.message || 'Test email sent successfully!', 'success');
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to send test email. Check SMTP credentials.';
      showToast(msg, 'error');
    } finally {
      setSendingTest(false);
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <div style={{ textAlign: 'center', padding: '60px' }}>Loading caretaker notification parameters...</div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="dashboard-header">
        <div className="dashboard-title-area">
          <h1>Caretaker &amp; SMTP Email Alert Settings</h1>
          <p>Configure automated dispatch parameters, Gmail App Password, and alert cooldown windows</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '24px' }}>
        {/* Left: Main Settings Form */}
        <div className="form-card" style={{ maxWidth: '100%', margin: 0 }}>
          <div className="form-header">
            <h2>Sanitation Caretaker &amp; SMTP Server</h2>
            <p>Emails are dispatched when dustbin fill level crosses configured threshold.</p>
          </div>

          <form onSubmit={handleSave}>
            <div className="form-grid">
              <div className="form-group">
                <label className="form-label">Primary Caretaker Name</label>
                <input
                  type="text"
                  name="caretaker_name"
                  className="form-input"
                  value={formData.caretaker_name}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Primary Caretaker Email *</label>
                <input
                  type="email"
                  name="caretaker_email"
                  className="form-input"
                  value={formData.caretaker_email}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="form-group col-span-2">
                <label className="form-label">Backup / Supervisor Email (Optional)</label>
                <input
                  type="email"
                  name="backup_email"
                  className="form-input"
                  placeholder="supervisor@campus.org"
                  value={formData.backup_email}
                  onChange={handleChange}
                />
              </div>

              <div className="form-group">
                <label className="form-label">SMTP Host</label>
                <input
                  type="text"
                  name="smtp_host"
                  className="form-input"
                  value={formData.smtp_host}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">SMTP Port</label>
                <input
                  type="number"
                  name="smtp_port"
                  className="form-input"
                  value={formData.smtp_port}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">SMTP Username / Sender Email</label>
                <input
                  type="text"
                  name="smtp_username"
                  className="form-input"
                  placeholder="your-email@gmail.com"
                  value={formData.smtp_username}
                  onChange={handleChange}
                />
              </div>

              <div className="form-group">
                <label className="form-label">
                  SMTP App Password
                  {passwordConfigured && (
                    <span style={{ color: 'var(--success)', fontSize: '11px', marginLeft: '6px' }}>
                      (✓ Stored)
                    </span>
                  )}
                </label>
                <input
                  type="password"
                  name="smtp_password"
                  className="form-input"
                  placeholder={passwordConfigured ? '•••••••••••••••• (Leave blank to keep)' : 'Enter 16-character App Password'}
                  value={formData.smtp_password}
                  onChange={handleChange}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Global Alert Threshold (%)</label>
                <input
                  type="number"
                  name="alert_threshold"
                  className="form-input"
                  min="50"
                  max="100"
                  value={formData.alert_threshold}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Alert Cooldown Window (Minutes)</label>
                <input
                  type="number"
                  name="cooldown_minutes"
                  className="form-input"
                  min="1"
                  max="120"
                  value={formData.cooldown_minutes}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="form-group col-span-2">
                <div className="form-checkbox-row">
                  <input
                    type="checkbox"
                    id="email_alerts_enabled"
                    name="email_alerts_enabled"
                    className="form-checkbox"
                    checked={formData.email_alerts_enabled}
                    onChange={handleChange}
                  />
                  <label htmlFor="email_alerts_enabled" style={{ fontSize: '14px', color: 'var(--text-primary)', cursor: 'pointer' }}>
                    Enable Automated Email Alerts for &gt;= 85% Fill Level Breaches
                  </label>
                </div>
              </div>
            </div>

            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={saving}>
                <Save size={16} />
                {saving ? 'Saving...' : 'SAVE SETTINGS'}
              </button>
            </div>
          </form>
        </div>

        {/* Right: Test Email Panel & Guidelines */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Test Email Box */}
          <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '16px', padding: '24px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Send size={18} color="var(--primary)" />
              Send Test Verification Email
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
              Verify SMTP server authentication and caretaker inbox connectivity.
            </p>

            <div className="form-group" style={{ marginBottom: '16px' }}>
              <label className="form-label">Recipient Test Address</label>
              <input
                type="email"
                className="form-input"
                placeholder="test-recipient@campus.org"
                value={testRecipient}
                onChange={(e) => setTestRecipient(e.target.value)}
              />
            </div>

            <button
              className="btn btn-secondary"
              style={{ width: '100%' }}
              onClick={handleSendTest}
              disabled={sendingTest}
            >
              <Send size={14} />
              {sendingTest ? 'Sending Verification Email...' : 'SEND TEST EMAIL'}
            </button>
          </div>

          {/* Cooldown Explanation Card */}
          <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '16px', padding: '24px' }}>
            <h3 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--warning)' }}>
              <Clock size={18} />
              Automated Alert &amp; Cooldown Policy
            </h3>
            <ul style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6, paddingLeft: '20px' }}>
              <li><strong>Trigger Condition:</strong> Email is sent only if fill level reaches/exceeds threshold (&ge; 85%) OR in case of overflowing/floor litter.</li>
              <li><strong>Recurring 15-Min Reminders:</strong> If the dustbin is not emptied, recurring reminder emails are dispatched every 15 minutes.</li>
              <li><strong>Auto-Stop on Emptied:</strong> As soon as the dustbin is emptied and cleared, email transfers stop immediately and state resets to NORMAL.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CaretakerSettingsPage;
