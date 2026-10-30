import React, { useState, useEffect } from 'react';
import { CHART } from '../theme';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Edit,
  Trash2,
  Crosshair,
  Play,
  Square,
  Send,
  Wifi,
  WifiOff,
  AlertTriangle,
  Activity,
  Layers,
  MapPin,
  Clock
} from 'lucide-react';
import { binService, alertService } from '../services/api';
import { useNotification } from '../context/NotificationContext';
import { wsService } from '../services/websocket';
import RoiModal from '../components/RoiModal';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from 'recharts';

const BinDetailsPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { showToast } = useNotification();

  const [bin, setBin] = useState(null);
  const [liveTelemetry, setLiveTelemetry] = useState(null);
  const [readings, setReadings] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [calibrating, setCalibrating] = useState(false);
  const [dispatchingAlert, setDispatchingAlert] = useState(false);
  const [overrideVal, setOverrideVal] = useState(75);

  const fetchDetails = async () => {
    try {
      const [binRes, readingsRes, alertsRes] = await Promise.all([
        binService.getById(id),
        binService.getReadings(id, 40),
        alertService.getAll(null, id),
      ]);
      setBin(binRes.data);
      setReadings(readingsRes.data);
      setAlerts(alertsRes.data);
    } catch (err) {
      showToast('Failed to load bin details', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetails();

    const unsubscribe = wsService.subscribe((payload) => {
      if (payload.type === 'telemetry' && Array.isArray(payload.bins)) {
        const item = payload.bins.find((b) => b.bin_pk === parseInt(id));
        if (item) setLiveTelemetry(item);
      }
    });

    return () => unsubscribe();
  }, [id]);

  const handleToggleMonitoring = async () => {
    if (!bin) return;
    try {
      if (bin.active) {
        await binService.stopMonitoring(bin.id);
        showToast(`Monitoring paused for ${bin.bin_id}`, 'info');
      } else {
        await binService.startMonitoring(bin.id);
        showToast(`Monitoring started for ${bin.bin_id}`, 'success');
      }
      fetchDetails();
    } catch (err) {
      showToast('Failed to toggle monitoring', 'error');
    }
  };

  const handleManualAlert = async () => {
    setDispatchingAlert(true);
    try {
      const res = await binService.triggerAlert(bin.id);
      showToast(res.data.message || 'Alert dispatched successfully to caretaker!', 'success');
      fetchDetails();
    } catch (err) {
      showToast('Failed to dispatch alert', 'error');
    } finally {
      setDispatchingAlert(false);
    }
  };

  const handleOverride = async (val) => {
    try {
      await binService.overrideFill(bin.id, parseFloat(val));
      showToast(`Set test override to ${val}%`, 'info');
    } catch (err) {
      showToast('Failed to set override', 'error');
    }
  };

  const handleResetOverride = async () => {
    try {
      await binService.overrideFill(bin.id, null);
      showToast('Reset to automatic camera detection', 'info');
    } catch (err) {
      showToast('Failed to reset override', 'error');
    }
  };

  if (loading || !bin) {
    return (
      <div className="page-container">
        <div style={{ textAlign: 'center', padding: '60px' }}>Loading smart bin inspection telemetry...</div>
      </div>
    );
  }

  const fill = liveTelemetry?.fill_percentage ?? bin.current_fill_percentage ?? 0.0;
  const status = liveTelemetry?.status ?? bin.current_status ?? 'NORMAL';
  const cameraOnline = liveTelemetry?.camera_online ?? bin.camera_online ?? false;
  const floorLitter = liveTelemetry?.floor_litter_detected ?? bin.floor_litter_detected ?? false;
  const isCritical = fill >= (bin.threshold || 85.0);

  const streamUrl = binService.getStreamUrl(bin.id);

  const chartData = readings.map((r) => ({
    time: new Date(r.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    fill: r.fill_percentage,
  }));

  return (
    <div className="page-container">
      {/* Top Breadcrumb & Action Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
        <button className="btn btn-secondary btn-sm" onClick={() => navigate('/bins')}>
          <ArrowLeft size={14} />
          Back to Bins
        </button>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className={`btn btn-sm ${bin.active ? 'btn-secondary' : 'btn-primary'}`}
            onClick={handleToggleMonitoring}
          >
            {bin.active ? <Square size={14} /> : <Play size={14} />}
            {bin.active ? 'Stop Monitoring' : 'Start Monitoring'}
          </button>
          <button className="btn btn-secondary btn-sm" onClick={() => setCalibrating(true)}>
            <Crosshair size={14} />
            Calibrate ROI
          </button>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate(`/bins/${bin.id}/edit`)}>
            <Edit size={14} />
            Edit Bin
          </button>
        </div>
      </div>

      {/* Main Inspection Grid: Stream on Left, Diagnostics Panel on Right */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '24px', marginBottom: '32px' }}>
        {/* Left: Large Camera Stream */}
        <div className="camera-detail-viewport">
          <img
            src={streamUrl}
            alt={`Camera Stream ${bin.bin_id}`}
            className="camera-stream-large"
          />
          <div className="camera-hud-badge">
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {cameraOnline ? <Wifi size={14} color="var(--success)" /> : <WifiOff size={14} color="var(--danger)" />}
              <strong>{cameraOnline ? 'CAMERA ONLINE' : 'OFFLINE'}</strong>
            </span>
            <span>•</span>
            <span>FPS: {liveTelemetry?.fps || '8.0'}</span>
            <span>•</span>
            <span style={{ color: 'var(--accent-cyan)' }}>AI DUAL-ROI ACTIVE</span>
          </div>
        </div>

        {/* Right: Real-time Fill Level Diagnostics */}
        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '16px', padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
            <div>
              <span className="bin-code-pill">{bin.bin_id}</span>
              <h2 style={{ fontSize: '20px', fontWeight: 800, marginTop: '6px' }}>{bin.name}</h2>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '2px' }}>
                <MapPin size={13} /> {bin.location}
              </p>
            </div>
            <span className={`status-badge ${isCritical ? 'critical' : fill >= 60 ? 'warning' : 'normal'}`}>
              {status}
            </span>
          </div>

          {/* Large Circular Fill Level Gauge Display */}
          <div style={{
            background: 'var(--bg-secondary)',
            borderRadius: '12px',
            padding: '20px',
            textAlign: 'center',
            border: `2px solid ${isCritical ? 'var(--danger-border)' : 'var(--border-subtle)'}`,
            marginBottom: '20px'
          }}>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Bin Fill Level
            </div>
            <div style={{
              fontSize: '48px',
              fontWeight: 900,
              color: isCritical ? 'var(--danger)' : fill >= 60 ? 'var(--warning)' : 'var(--success)',
              lineHeight: 1.1,
              margin: '8px 0'
            }}>
              {fill.toFixed(1)}%
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Alert Threshold: <strong style={{ color: 'var(--primary)' }}>{bin.threshold}%</strong>
            </div>
          </div>

          {/* Diagnostics Breakdown Table */}
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', marginBottom: '20px' }}>
            <tbody>
              <tr style={{ borderBottom: '1px solid var(--divider)' }}>
                <td style={{ padding: '8px 0', color: 'var(--text-secondary)' }}>Surrounding Floor Litter</td>
                <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: 700, color: floorLitter ? 'var(--danger)' : 'var(--success)' }}>
                  {floorLitter ? 'DETECTED' : 'CLEAR'}
                </td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--divider)' }}>
                <td style={{ padding: '8px 0', color: 'var(--text-secondary)' }}>Surface Coverage %</td>
                <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: 600 }}>
                  {liveTelemetry?.surface_coverage_pct ?? 0}%
                </td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--divider)' }}>
                <td style={{ padding: '8px 0', color: 'var(--text-secondary)' }}>Estimated Fill Height</td>
                <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: 600 }}>
                  {liveTelemetry?.fill_height_pct ?? 0}%
                </td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--divider)' }}>
                <td style={{ padding: '8px 0', color: 'var(--text-secondary)' }}>Waste Objects in Bin</td>
                <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: 600 }}>
                  {liveTelemetry?.waste_boxes_count ?? 0}
                </td>
              </tr>
            </tbody>
          </table>

          {/* Test Fill Level Override */}
          <div className="test-override-panel" style={{ marginTop: '0', marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '12px' }}>
              <span style={{ color: 'var(--warning)', fontWeight: 600 }}>Demo Fill Level Override</span>
              <strong>{overrideVal}%</strong>
            </div>
            <input
              type="range"
              min="15"
              max="98"
              value={overrideVal}
              onChange={(e) => setOverrideVal(e.target.value)}
              onMouseUp={() => handleOverride(overrideVal)}
              onTouchEnd={() => handleOverride(overrideVal)}
              style={{ width: '100%' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px' }}>
              <button className="btn btn-secondary btn-sm" onClick={() => handleOverride(90)}>
                Set 90% (Trigger Test)
              </button>
              <button className="btn btn-secondary btn-sm" onClick={handleResetOverride}>
                Reset to Auto
              </button>
            </div>
          </div>

          {/* Manual Alert Dispatcher */}
          <div>
            <button
              className="btn btn-danger"
              style={{ width: '100%', padding: '12px' }}
              onClick={handleManualAlert}
              disabled={dispatchingAlert}
            >
              <Send size={15} />
              {dispatchingAlert ? 'Dispatching...' : 'Send Test Alert Email Now'}
            </button>
          </div>
        </div>
      </div>

      {/* Historical Trend Chart */}
      <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '16px', padding: '24px', marginBottom: '32px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Activity size={18} color="var(--primary)" />
          Historical Fill Level Trend (Last 24 Hours)
        </h3>
        <div style={{ width: '100%', height: '240px' }}>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} />
                <XAxis dataKey="time" stroke={CHART.axis} fontSize={11} />
                <YAxis domain={[0, 100]} stroke={CHART.axis} fontSize={11} unit="%" />
                <Tooltip
                  contentStyle={CHART.tooltip}
                />
                <Line
                  type="monotone"
                  dataKey="fill"
                  name="Fill Level"
                  stroke={CHART.line}
                  strokeWidth={2.5}
                  dot={{ r: 2 }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ textAlign: 'center', padding: '80px', color: 'var(--text-muted)' }}>
              No historical readings accumulated yet for this dustbin.
            </div>
          )}
        </div>
      </div>

      {/* Alert History for this Bin */}
      <div className="table-card">
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700 }}>Alert Log for {bin.bin_id}</h3>
        </div>
        <div className="table-responsive">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Alert ID</th>
                <th>Fill Level</th>
                <th>Threshold</th>
                <th>Recipient</th>
                <th>Timestamp</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {alerts.length === 0 ? (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)' }}>
                    No alerts triggered for this bin yet.
                  </td>
                </tr>
              ) : (
                alerts.map((a) => (
                  <tr key={a.id}>
                    <td>#{a.id}</td>
                    <td style={{ color: 'var(--danger)', fontWeight: 700 }}>{a.fill_percentage}%</td>
                    <td>{a.threshold}%</td>
                    <td>{a.recipient}</td>
                    <td>{new Date(a.sent_at).toLocaleString()}</td>
                    <td>
                      <span className={`status-badge ${a.status === 'SENT' ? 'normal' : 'warning'}`}>
                        {a.status}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {calibrating && (
        <RoiModal
          bin={bin}
          onClose={() => setCalibrating(false)}
          onSaved={() => fetchDetails()}
        />
      )}
    </div>
  );
};

export default BinDetailsPage;
