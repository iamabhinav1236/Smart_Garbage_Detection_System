import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Save, X, Radio, CheckCircle, XCircle, ArrowLeft, Camera, Monitor, Smartphone, HelpCircle } from 'lucide-react';
import { binService } from '../services/api';
import { useNotification } from '../context/NotificationContext';

const AddBinPage = () => {
  const navigate = useNavigate();
  const { showToast } = useNotification();

  const [formData, setFormData] = useState({
    bin_id: '',
    name: '',
    location: '',
    camera_url: 'demo',
    camera_protocol: 'http',
    threshold: 85.0,
    floor_litter_enabled: true,
    description: '',
    active: true,
  });

  const [testingCamera, setTestingCamera] = useState(false);
  const [cameraTestResult, setCameraTestResult] = useState(null);
  const [saving, setSaving] = useState(false);

  const normalizeUrlInput = (val) => {
    let clean = val.trim();
    if (!clean || clean.toLowerCase() === 'demo' || clean === '0' || clean === '1') {
      return clean;
    }
    // If user entered e.g. 192.168.1.5 or 192.168.1.5:8080
    if (!clean.startsWith('http://') && !clean.startsWith('https://') && !clean.startsWith('rtsp://')) {
      clean = 'http://' + clean;
    }
    // If it has port 8080 but no /video
    if (clean.includes(':8080') && !clean.includes('/video') && !clean.includes('/shot.jpg')) {
      clean = clean.replace(/\/+$/, '') + '/video';
    }
    return clean;
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleApplyPreset = (presetUrl) => {
    setFormData((prev) => ({ ...prev, camera_url: presetUrl }));
    setCameraTestResult(null);
  };

  const handleTestCamera = async () => {
    setTestingCamera(true);
    setCameraTestResult(null);

    const normalizedUrl = normalizeUrlInput(formData.camera_url);
    if (normalizedUrl !== formData.camera_url) {
      setFormData((prev) => ({ ...prev, camera_url: normalizedUrl }));
    }

    try {
      const res = await binService.testCameraUrl({
        camera_url: normalizedUrl,
        camera_protocol: formData.camera_protocol,
      });
      setCameraTestResult(res.data);
      if (res.data.online) {
        if (res.data.resolved_url && res.data.resolved_url !== 'demo') {
          setFormData((prev) => ({ ...prev, camera_url: res.data.resolved_url }));
        }
        showToast(res.data.message, 'success');
      } else {
        showToast(res.data.message, 'warning');
      }
    } catch (err) {
      setCameraTestResult({
        online: false,
        status: 'Camera Offline',
        message: 'Failed to communicate with camera test service.',
      });
      showToast('Camera connection test failed', 'error');
    } finally {
      setTestingCamera(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const finalUrl = normalizeUrlInput(formData.camera_url);
      await binService.create({
        ...formData,
        camera_url: finalUrl,
        threshold: parseFloat(formData.threshold),
      });
      showToast('Bin added successfully.', 'success');
      navigate('/dashboard');
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to register new dustbin.';
      showToast(msg, 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-container">
      <div style={{ marginBottom: '20px' }}>
        <button className="btn btn-secondary btn-sm" onClick={() => navigate('/bins')}>
          <ArrowLeft size={14} />
          Back to Bins List
        </button>
      </div>

      <div className="form-card">
        <div className="form-header">
          <h2>Register New Smart Dustbin</h2>
          <p>Configure hardware parameters, IP webcam network endpoint, and alert thresholds.</p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-grid">
            <div className="form-group">
              <label className="form-label">Bin ID / Serial Number *</label>
              <input
                type="text"
                name="bin_id"
                className="form-input"
                placeholder="e.g. BIN-004"
                value={formData.bin_id}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Bin Descriptive Name *</label>
              <input
                type="text"
                name="name"
                className="form-input"
                placeholder="e.g. Central Library Courtyard"
                value={formData.name}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group col-span-2">
              <label className="form-label">Location / Zone *</label>
              <input
                type="text"
                name="location"
                className="form-input"
                placeholder="e.g. Academic Block C - Ground Floor Lobby"
                value={formData.location}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group col-span-2">
              <label className="form-label">Camera Source / IP Webcam URL *</label>

              {/* Quick Preset Buttons */}
              <div style={{ display: 'flex', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => handleApplyPreset('0')}
                  title="Use your PC / laptop built-in webcam"
                >
                  <Camera size={13} style={{ color: 'var(--primary)' }} />
                  Use PC Webcam (Device 0)
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => handleApplyPreset('demo')}
                  title="Use synthetic simulated stream"
                >
                  <Monitor size={13} style={{ color: 'var(--accent-cyan)' }} />
                  Use Demo Mode Stream
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => {
                    const current = formData.camera_url;
                    if (current && !current.includes('/video') && current !== 'demo' && current !== '0') {
                      setFormData((prev) => ({ ...prev, camera_url: normalizeUrlInput(current) }));
                    }
                  }}
                  title="Auto-format IP address with http:// and /video"
                >
                  <Smartphone size={13} style={{ color: 'var(--warning)' }} />
                  Auto-Format Phone URL
                </button>
              </div>

              <div className="input-with-button">
                <input
                  type="text"
                  name="camera_url"
                  className="form-input"
                  placeholder="e.g. http://192.168.1.100:8080/video, 0, or demo"
                  value={formData.camera_url}
                  onChange={handleChange}
                  required
                />
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleTestCamera}
                  disabled={testingCamera}
                >
                  <Radio size={14} />
                  {testingCamera ? 'Testing...' : 'TEST CAMERA'}
                </button>
              </div>

              {/* Helpful instructions banner */}
              <div style={{
                marginTop: '10px',
                padding: '12px 14px',
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                fontSize: '12px',
                color: 'var(--text-secondary)',
                lineHeight: 1.6
              }}>
                <div style={{ fontWeight: 700, color: 'var(--primary)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <HelpCircle size={14} color="var(--accent-cyan)" />
                  How to configure your camera:
                </div>
                <div>• <strong>Android IP Webcam:</strong> Connect phone to same Wi-Fi &rarr; Open app &rarr; Tap <em>Start server</em> &rarr; Enter URL shown on phone screen with <code>/video</code> (e.g. <code>http://192.168.1.100:8080/video</code>).</div>
                <div>• <strong>Laptop / PC Webcam:</strong> Click <em>Use PC Webcam (Device 0)</em> or type <code>0</code>.</div>
                <div>• <strong>Offline Testing:</strong> Click <em>Use Demo Mode Stream</em> or type <code>demo</code>.</div>
              </div>

              {/* Camera Connection Status Feedback */}
              {cameraTestResult && (
                <div style={{
                  marginTop: '10px',
                  padding: '12px 14px',
                  borderRadius: '8px',
                  background: cameraTestResult.online ? 'var(--success-bg)' : 'var(--danger-bg)',
                  border: `1px solid ${cameraTestResult.online ? 'var(--success-border)' : 'var(--danger-border)'}`,
                  color: cameraTestResult.online ? 'var(--success)' : 'var(--danger)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  fontSize: '13px'
                }}>
                  {cameraTestResult.online ? <CheckCircle size={18} /> : <XCircle size={18} />}
                  <div>
                    <strong>{cameraTestResult.status}:</strong> {cameraTestResult.message}
                    {cameraTestResult.latency_ms && ` (${cameraTestResult.latency_ms}ms)`}
                  </div>
                </div>
              )}
            </div>

            <div className="form-group">
              <label className="form-label">Camera Protocol</label>
              <select
                name="camera_protocol"
                className="form-select"
                value={formData.camera_protocol}
                onChange={handleChange}
              >
                <option value="http">HTTP Video Stream (IP Webcam)</option>
                <option value="rtsp">RTSP (Real-Time Streaming Protocol)</option>
                <option value="mjpeg">MJPEG Stream</option>
                <option value="demo">Synthetic Demo Generator</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Alert Fill Threshold (%)</label>
              <input
                type="number"
                name="threshold"
                className="form-input"
                min="30"
                max="100"
                value={formData.threshold}
                onChange={handleChange}
              />
            </div>

            <div className="form-group col-span-2">
              <label className="form-label">Description / Operational Notes</label>
              <textarea
                name="description"
                className="form-textarea"
                placeholder="Optional notes regarding bin fill level, servicing schedule, or phone mount angle..."
                value={formData.description}
                onChange={handleChange}
              />
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
                  Enable Floor Litter &amp; Overflow Zone Surveillance (Dual-ROI)
                </label>
              </div>

              <div className="form-checkbox-row">
                <input
                  type="checkbox"
                  id="active"
                  name="active"
                  className="form-checkbox"
                  checked={formData.active}
                  onChange={handleChange}
                />
                <label htmlFor="active" style={{ fontSize: '14px', color: 'var(--text-primary)', cursor: 'pointer' }}>
                  Activate Continuous AI Monitoring immediately after creation
                </label>
              </div>
            </div>
          </div>

          <div className="form-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => navigate('/bins')}
            >
              <X size={16} />
              CANCEL
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={saving}
            >
              <Save size={16} />
              {saving ? 'Saving...' : 'SAVE BIN'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AddBinPage;
