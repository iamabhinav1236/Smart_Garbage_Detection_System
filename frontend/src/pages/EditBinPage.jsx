import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Save, X, Radio, ArrowLeft, CheckCircle, XCircle, Camera, Monitor, Smartphone, HelpCircle } from 'lucide-react';
import { binService } from '../services/api';
import { useNotification } from '../context/NotificationContext';

const EditBinPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { showToast } = useNotification();

  const [formData, setFormData] = useState({
    name: '',
    location: '',
    camera_url: '',
    camera_protocol: 'http',
    threshold: 85.0,
    floor_litter_enabled: true,
    description: '',
    active: true,
  });

  const [binCode, setBinCode] = useState('');
  const [testingCamera, setTestingCamera] = useState(false);
  const [cameraTestResult, setCameraTestResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const normalizeUrlInput = (val) => {
    let clean = val.trim();
    if (!clean || clean.toLowerCase() === 'demo' || clean === '0' || clean === '1') {
      return clean;
    }
    if (!clean.startsWith('http://') && !clean.startsWith('https://') && !clean.startsWith('rtsp://')) {
      clean = 'http://' + clean;
    }
    if (clean.includes(':8080') && !clean.includes('/video') && !clean.includes('/shot.jpg')) {
      clean = clean.replace(/\/+$/, '') + '/video';
    }
    return clean;
  };

  useEffect(() => {
    const fetchBin = async () => {
      try {
        const res = await binService.getById(id);
        const b = res.data;
        setBinCode(b.bin_id);
        setFormData({
          name: b.name,
          location: b.location,
          camera_url: b.camera_url,
          camera_protocol: b.camera_protocol || 'http',
          threshold: b.threshold,
          floor_litter_enabled: b.floor_litter_enabled ?? true,
          description: b.description || '',
          active: b.active,
        });
      } catch (err) {
        showToast('Failed to load bin details for editing', 'error');
        navigate('/bins');
      } finally {
        setLoading(false);
      }
    };
    fetchBin();
  }, [id]);

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
      showToast('Camera test request failed', 'error');
    } finally {
      setTestingCamera(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const finalUrl = normalizeUrlInput(formData.camera_url);
      await binService.update(id, {
        ...formData,
        camera_url: finalUrl,
        threshold: parseFloat(formData.threshold),
      });
      showToast(`Bin ${binCode} updated successfully.`, 'success');
      navigate('/bins');
    } catch (err) {
      showToast('Failed to update bin configuration', 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <div style={{ textAlign: 'center', padding: '60px' }}>Loading bin configuration...</div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div style={{ marginBottom: '20px' }}>
        <button className="btn btn-secondary btn-sm" onClick={() => navigate('/bins')}>
          <ArrowLeft size={14} />
          Back to Bins
        </button>
      </div>

      <div className="form-card">
        <div className="form-header">
          <h2>Edit Dustbin Configuration — {binCode}</h2>
          <p>Modify camera streaming URL, alert sensitivity, and operational parameters.</p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-grid">
            <div className="form-group">
              <label className="form-label">Bin Descriptive Name</label>
              <input
                type="text"
                name="name"
                className="form-input"
                value={formData.name}
                onChange={handleChange}
                required
              />
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
                required
              />
            </div>

            <div className="form-group col-span-2">
              <label className="form-label">Location / Zone</label>
              <input
                type="text"
                name="location"
                className="form-input"
                value={formData.location}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group col-span-2">
              <label className="form-label">Camera Source / IP Webcam URL</label>

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

            <div className="form-group col-span-2">
              <label className="form-label">Description / Operational Notes</label>
              <textarea
                name="description"
                className="form-textarea"
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
                  Enable Floor Litter &amp; Overflow Zone Surveillance
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
                  Keep Continuous AI Stream Processing Active
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
              {saving ? 'Updating...' : 'SAVE CHANGES'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default EditBinPage;
