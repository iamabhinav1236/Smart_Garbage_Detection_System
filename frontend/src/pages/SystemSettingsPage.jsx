import React, { useState, useEffect } from 'react';
import { Settings, Save, Cpu, Sliders, RefreshCw, Layers, KeyRound } from 'lucide-react';
import { systemSettingsService, authService } from '../services/api';
import { useNotification } from '../context/NotificationContext';

const ChangePasswordCard = () => {
  const { showToast } = useNotification();
  const [form, setForm] = useState({ current: '', next: '', confirm: '' });
  const [saving, setSaving] = useState(false);

  const handleChange = (e) => setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (form.next.length < 8) {
      showToast('New password must be at least 8 characters', 'error');
      return;
    }
    if (form.next !== form.confirm) {
      showToast('New passwords do not match', 'error');
      return;
    }
    setSaving(true);
    try {
      await authService.changePassword(form.current, form.next);
      showToast('Password updated. Use it next time you log in.', 'success');
      setForm({ current: '', next: '', confirm: '' });
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to change password', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="form-card" style={{ maxWidth: '820px', margin: '24px 0 0' }}>
      <div className="form-header">
        <h2>Admin Password</h2>
        <p>Change the password used to log in to this dashboard.</p>
      </div>
      <form onSubmit={handleSubmit}>
        <div className="form-grid">
          <div className="form-group col-span-2">
            <label className="form-label">Current Password</label>
            <input type="password" name="current" className="form-input" autoComplete="current-password"
              value={form.current} onChange={handleChange} required />
          </div>
          <div className="form-group">
            <label className="form-label">New Password (min 8 characters)</label>
            <input type="password" name="next" className="form-input" autoComplete="new-password"
              minLength={8} value={form.next} onChange={handleChange} required />
          </div>
          <div className="form-group">
            <label className="form-label">Confirm New Password</label>
            <input type="password" name="confirm" className="form-input" autoComplete="new-password"
              minLength={8} value={form.confirm} onChange={handleChange} required />
          </div>
        </div>
        <div className="form-actions">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            <KeyRound size={16} />
            {saving ? 'Updating...' : 'CHANGE PASSWORD'}
          </button>
        </div>
      </form>
    </div>
  );
};

const SystemSettingsPage = () => {
  const { showToast } = useNotification();

  const [formData, setFormData] = useState({
    default_threshold: 85.0,
    default_cooldown: 15,
    detection_fps: 5,
    confidence_threshold: 0.25,
    camera_reconnect_interval: 5,
    demo_mode: false,
    email_notification_enabled: true,
    floor_litter_enabled: true,
    model_path: 'models/yolov8n.onnx',
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const fetchSettings = async () => {
    try {
      const res = await systemSettingsService.get();
      setFormData(res.data);
    } catch (err) {
      showToast('Failed to load system parameters', 'error');
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
      await systemSettingsService.update({
        ...formData,
        default_threshold: parseFloat(formData.default_threshold),
        default_cooldown: parseInt(formData.default_cooldown),
        detection_fps: parseInt(formData.detection_fps),
        confidence_threshold: parseFloat(formData.confidence_threshold),
        camera_reconnect_interval: parseInt(formData.camera_reconnect_interval),
      });
      showToast('System configuration updated successfully.', 'success');
      fetchSettings();
    } catch (err) {
      showToast('Failed to update system settings', 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <div style={{ textAlign: 'center', padding: '60px' }}>Loading system settings...</div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="dashboard-header">
        <div className="dashboard-title-area">
          <h1>System &amp; AI Engine Configuration</h1>
          <p>Configure computer vision inference rates, YOLO model weights, and global system defaults</p>
        </div>
      </div>

      <div className="form-card" style={{ maxWidth: '820px', margin: 0 }}>
        <div className="form-header">
          <h2>Computer Vision &amp; Pipeline Tuning</h2>
          <p>Settings governing frame sampling rates, object detection thresholds, and failover behavior.</p>
        </div>

        <form onSubmit={handleSave}>
          <div className="form-grid">
            <div className="form-group">
              <label className="form-label">Default Alert Threshold (%)</label>
              <input
                type="number"
                name="default_threshold"
                className="form-input"
                min="50"
                max="100"
                value={formData.default_threshold}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Alert Cooldown Window (Minutes)</label>
              <input
                type="number"
                name="default_cooldown"
                className="form-input"
                min="1"
                max="120"
                value={formData.default_cooldown}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Detection Frame Rate (FPS)</label>
              <input
                type="number"
                name="detection_fps"
                className="form-input"
                min="1"
                max="30"
                value={formData.detection_fps}
                onChange={handleChange}
                required
              />
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Recommended: 5 FPS for optimal CPU efficiency without lag.
              </span>
            </div>

            <div className="form-group">
              <label className="form-label">YOLOv8 Confidence Threshold (0.1 - 1.0)</label>
              <input
                type="number"
                step="0.05"
                name="confidence_threshold"
                className="form-input"
                min="0.1"
                max="0.95"
                value={formData.confidence_threshold}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Camera Reconnect Retry (Seconds)</label>
              <input
                type="number"
                name="camera_reconnect_interval"
                className="form-input"
                min="2"
                max="60"
                value={formData.camera_reconnect_interval}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">YOLO Weights File Path</label>
              <input
                type="text"
                name="model_path"
                className="form-input"
                value={formData.model_path}
                onChange={handleChange}
                required
              />
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Supports custom Roboflow ONNX models in <code>models/</code> directory.
              </span>
            </div>

            <div className="form-group col-span-2">
              <div className="form-checkbox-row">
                <input
                  type="checkbox"
                  id="floor_litter_enabled"
                  name="floor_litter_enabled"
                  className="form-checkbox"
                  checked={formData.floor_litter_enabled}
                  onChange={handleChange}
                />
                <label htmlFor="floor_litter_enabled" style={{ fontSize: '14px', color: 'var(--text-primary)', cursor: 'pointer' }}>
                  Enable Floor Litter &amp; Overflow Zone Detection Globally
                </label>
              </div>

              <div className="form-checkbox-row">
                <input
                  type="checkbox"
                  id="demo_mode"
                  name="demo_mode"
                  className="form-checkbox"
                  checked={formData.demo_mode}
                  onChange={handleChange}
                />
                <label htmlFor="demo_mode" style={{ fontSize: '14px', color: 'var(--text-primary)', cursor: 'pointer' }}>
                  Force Synthetic Demo Generator Mode for all cameras
                </label>
              </div>
            </div>
          </div>

          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={saving}>
              <Save size={16} />
              {saving ? 'Updating...' : 'SAVE SYSTEM CONFIG'}
            </button>
          </div>
        </form>
      </div>

      <ChangePasswordCard />
    </div>
  );
};

export default SystemSettingsPage;
