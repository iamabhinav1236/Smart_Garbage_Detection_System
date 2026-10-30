import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  MapPin,
  Eye,
  Edit,
  Crosshair,
  Wifi,
  WifiOff,
  AlertTriangle,
  Sliders
} from 'lucide-react';
import { binService } from '../services/api';
import { useNotification } from '../context/NotificationContext';

const BinCard = ({ bin, onCalibrateRoi, liveTelemetry }) => {
  const navigate = useNavigate();
  const { showToast } = useNotification();
  const [showOverride, setShowOverride] = useState(false);
  const [overrideValue, setOverrideValue] = useState(bin.current_fill_percentage || 50);

  // Merge live telemetry if available from websocket
  const fill = liveTelemetry?.fill_percentage ?? bin.current_fill_percentage ?? 0.0;
  const status = liveTelemetry?.status ?? bin.current_status ?? 'NORMAL';
  const cameraOnline = liveTelemetry?.camera_online ?? bin.camera_online ?? false;
  const floorLitter = liveTelemetry?.floor_litter_detected ?? bin.floor_litter_detected ?? false;

  const isCritical = fill >= (bin.threshold || 85.0);
  const isWarning = fill >= 60.0 && !isCritical;
  const statusClass = isCritical ? 'critical' : isWarning ? 'warning' : 'normal';

  const isDemo = bin.camera_url?.toLowerCase().includes('demo') || bin.camera_url === 'demo';
  const streamUrl = binService.getStreamUrl(bin.id);

  const handleApplyOverride = async (val) => {
    try {
      await binService.overrideFill(bin.id, parseFloat(val));
      showToast(`Applied test override: ${val}% for ${bin.bin_id}`, 'info');
    } catch (err) {
      showToast('Failed to apply override', 'error');
    }
  };

  const handleResetOverride = async () => {
    try {
      await binService.overrideFill(bin.id, null);
      showToast(`Reset ${bin.bin_id} to automatic AI detection`, 'info');
    } catch (err) {
      showToast('Failed to reset override', 'error');
    }
  };

  return (
    <div className={`bin-card ${isCritical ? 'critical-border' : ''}`}>
      {/* Header */}
      <div className="bin-card-header">
        <div className="bin-title-group">
          <h3>
            <span className="bin-code-pill">{bin.bin_id}</span>
            {bin.name}
          </h3>
          <div className="bin-location-text">
            <MapPin size={12} />
            <span>{bin.location}</span>
          </div>
        </div>

        <div className="header-status">
          <span className={`status-badge ${statusClass}`}>
            {status}
          </span>
        </div>
      </div>

      {/* Live Video Feed */}
      <div className="bin-video-frame">
        {bin.active ? (
          <img
            src={streamUrl}
            alt={`Camera Stream ${bin.bin_id}`}
            className="bin-video-img"
            onError={(e) => {
              // Graceful error fallback
              e.target.style.display = 'none';
            }}
          />
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)', fontSize: '13px' }}>
            MONITORING PAUSED
          </div>
        )}

        {/* Badges on stream */}
        <div className="live-badge">
          <div className="live-indicator-dot"></div>
          <span>LIVE</span>
        </div>

        {isDemo && (
          <div className="demo-watermark-pill">
            DEMO STREAM
          </div>
        )}
      </div>

      {/* Card Content & Telemetry */}
      <div className="bin-card-body">
        {/* Fill Level Metric */}
        <div className="fill-level-block">
          <div className="fill-level-labels">
            <span className="fill-label-name">Bin Fill Level</span>
            <span className={`fill-percentage-value ${statusClass}`}>
              {fill.toFixed(1)}%
            </span>
          </div>

          <div className="fill-progress-track">
            <div
              className={`fill-progress-bar ${statusClass}`}
              style={{ width: `${Math.min(100, Math.max(0, fill))}%` }}
            ></div>
          </div>
        </div>

        {/* Floor Litter & Camera Status Row */}
        <div className="floor-litter-row">
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            {cameraOnline ? (
              <Wifi size={14} style={{ color: 'var(--success)' }} />
            ) : (
              <WifiOff size={14} style={{ color: 'var(--text-muted)' }} />
            )}
            <span style={{ color: cameraOnline ? 'var(--text-primary)' : 'var(--text-muted)' }}>
              {cameraOnline ? 'Camera Online' : 'Camera Offline'}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ color: floorLitter ? 'var(--danger)' : 'var(--success)', fontWeight: 600 }}>
              {floorLitter ? 'Floor Litter: DETECTED' : 'Floor: CLEAR'}
            </span>
          </div>
        </div>

        {/* Test Override Slider (collapsible for demonstration) */}
        {showOverride && (
          <div className="test-override-panel">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '12px' }}>
              <span style={{ color: 'var(--warning)', fontWeight: 600 }}>Simulate Fill Level</span>
              <span style={{ fontWeight: 800 }}>{overrideValue}%</span>
            </div>
            <input
              type="range"
              min="10"
              max="98"
              value={overrideValue}
              onChange={(e) => setOverrideValue(e.target.value)}
              onMouseUp={() => handleApplyOverride(overrideValue)}
              onTouchEnd={() => handleApplyOverride(overrideValue)}
              style={{ width: '100%', cursor: 'pointer' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px' }}>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => {
                  setOverrideValue(92);
                  handleApplyOverride(92);
                }}
              >
                Set 92% (Trigger &gt;85% Alert)
              </button>
              <button
                className="btn btn-secondary btn-sm"
                onClick={handleResetOverride}
              >
                Reset to Auto
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Card Footer Actions */}
      <div className="bin-card-footer">
        <div style={{ display: 'flex', gap: '6px' }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => navigate(`/bins/${bin.id}`)}
            title="Inspect Bin Analytics and Video"
          >
            <Eye size={13} />
            VIEW
          </button>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => navigate(`/bins/${bin.id}/edit`)}
            title="Edit Bin Configuration"
          >
            <Edit size={13} />
            EDIT
          </button>
        </div>

        <div style={{ display: 'flex', gap: '6px' }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => onCalibrateRoi(bin)}
            title="Calibrate Bin and Floor ROI"
          >
            <Crosshair size={13} />
            CALIBRATE
          </button>
          <button
            className={`btn btn-sm ${showOverride ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setShowOverride(!showOverride)}
            title="Toggle Demo Fill Level Slider"
          >
            <Sliders size={13} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default BinCard;
