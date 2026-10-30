import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Trash2,
  Camera,
  AlertOctagon,
  Percent,
  PlusCircle,
  RefreshCw,
  Sparkles
} from 'lucide-react';
import MetricCard from '../components/MetricCard';
import BinCard from '../components/BinCard';
import RoiModal from '../components/RoiModal';
import { binService, dashboardService } from '../services/api';
import { wsService } from '../services/websocket';
import { useNotification } from '../context/NotificationContext';

const DashboardPage = () => {
  const navigate = useNavigate();
  const { showToast } = useNotification();

  const [stats, setStats] = useState({
    total_bins: 0,
    online_cameras: 0,
    critical_bins: 0,
    average_fill: 0.0,
  });
  const [bins, setBins] = useState([]);
  const [liveMap, setLiveMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [calibratingBin, setCalibratingBin] = useState(null);

  const fetchDashboardData = async () => {
    try {
      const [statsRes, binsRes] = await Promise.all([
        dashboardService.getStats(),
        binService.getAll(),
      ]);
      setStats(statsRes.data);
      setBins(binsRes.data);
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      showToast('Failed to load latest dashboard metrics', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();

    // Subscribe to WebSocket live telemetry stream
    const unsubscribe = wsService.subscribe((payload) => {
      if (payload.type === 'telemetry' && Array.isArray(payload.bins)) {
        const newMap = {};
        let critCount = 0;
        let onlineCount = 0;
        let fillSum = 0;

        payload.bins.forEach((b) => {
          newMap[b.bin_pk] = b;
          if (b.fill_percentage >= 85.0) critCount++;
          if (b.camera_online) onlineCount++;
          fillSum += b.fill_percentage;
        });

        setLiveMap(newMap);

        // Dynamically update stats from live telemetry
        if (payload.bins.length > 0) {
          setStats((prev) => ({
            ...prev,
            online_cameras: onlineCount,
            critical_bins: critCount,
            average_fill: roundOne(fillSum / payload.bins.length),
          }));
        }
      }
    });

    return () => {
      unsubscribe();
    };
  }, []);

  const roundOne = (num) => Math.round(num * 10) / 10;

  return (
    <div className="page-container">
      {/* Header */}
      <div className="dashboard-header">
        <div className="dashboard-title-area">
          <h1>Main Monitoring Dashboard</h1>
          <p>Real-time AI camera streaming, dustbin fill tracking, and smart alerts</p>
        </div>

        <div className="dashboard-actions">
          <button className="btn btn-secondary" onClick={fetchDashboardData}>
            <RefreshCw size={16} />
            Refresh
          </button>
          <button className="btn btn-primary" onClick={() => navigate('/bins/new')}>
            <PlusCircle size={16} />
            Add New Bin
          </button>
        </div>
      </div>

      {/* Top Metrics Cards */}
      <div className="metrics-grid">
        <MetricCard
          title="TOTAL BINS"
          value={stats.total_bins}
          icon={Trash2}
          colorClass="blue"
          subtitle="Monitored Campus Nodes"
        />
        <MetricCard
          title="ONLINE CAMERAS"
          value={stats.online_cameras}
          icon={Camera}
          colorClass="emerald"
          subtitle="Active Video Streams"
        />
        <MetricCard
          title="BINS ABOVE 85%"
          value={stats.critical_bins}
          icon={AlertOctagon}
          colorClass="red"
          subtitle="Immediate Caretaker Attention"
        />
        <MetricCard
          title="AVERAGE FILL LEVEL"
          value={`${stats.average_fill}%`}
          icon={Percent}
          colorClass="amber"
          subtitle="Campus Aggregate Fill Level"
        />
      </div>

      {/* Live Stream Section */}
      <div className="section-header">
        <div className="section-title">
          <Sparkles size={18} style={{ color: 'var(--primary)' }} />
          <span>Live Camera Feeds &amp; Detection Overlay</span>
        </div>
        <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
          Showing {bins.length} monitored dustbins
        </span>
      </div>

      {/* Dynamic Bin Cards Grid */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-secondary)' }}>
          Loading active cameras and AI detection pipeline...
        </div>
      ) : bins.length === 0 ? (
        <div className="empty-state">
          <h3>No Dustbins Registered Yet</h3>
          <p>Register your first IP camera or simulated smart dustbin to begin monitoring.</p>
          <button className="btn btn-primary" onClick={() => navigate('/bins/new')}>
            <PlusCircle size={16} />
            + ADD FIRST BIN
          </button>
        </div>
      ) : (
        <div className="bins-grid">
          {bins.map((bin) => (
            <BinCard
              key={bin.id}
              bin={bin}
              liveTelemetry={liveMap[bin.id]}
              onCalibrateRoi={(targetBin) => setCalibratingBin(targetBin)}
            />
          ))}
        </div>
      )}

      {/* Interactive ROI Calibration Modal */}
      {calibratingBin && (
        <RoiModal
          bin={calibratingBin}
          onClose={() => setCalibratingBin(null)}
          onSaved={() => fetchDashboardData()}
        />
      )}
    </div>
  );
};

export default DashboardPage;
