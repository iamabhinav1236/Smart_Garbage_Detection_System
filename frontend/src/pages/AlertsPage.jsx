import React, { useState, useEffect } from 'react';
import {
  Bell,
  CheckCircle,
  XCircle,
  Clock,
  Eye,
  X,
  MapPin,
  RefreshCw
} from 'lucide-react';
import { alertService } from '../services/api';
import { useNotification } from '../context/NotificationContext';

const AlertsPage = () => {
  const { showToast } = useNotification();
  const [alerts, setAlerts] = useState([]);
  const [filter, setFilter] = useState('ALL');
  const [loading, setLoading] = useState(true);
  const [previewSnapshot, setPreviewSnapshot] = useState(null);

  const fetchAlerts = async () => {
    try {
      const res = await alertService.getAll(filter === 'ALL' ? null : filter);
      setAlerts(res.data);
    } catch (err) {
      showToast('Failed to load alerts registry', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, [filter]);

  return (
    <div className="page-container">
      <div className="dashboard-header">
        <div className="dashboard-title-area">
          <h1>Automated Alerts &amp; Incident Log</h1>
          <p>Auditable records of all 85% fill level breaches, snapshots, and caretaker dispatches</p>
        </div>

        <button className="btn btn-secondary" onClick={fetchAlerts}>
          <RefreshCw size={15} />
          Refresh
        </button>
      </div>

      <div className="table-card">
        <div className="table-filter-bar">
          <div className="filter-pills">
            {['ALL', 'SENT', 'SIMULATED', 'FAILED'].map((st) => (
              <button
                key={st}
                className={`filter-pill ${filter === st ? 'active' : ''}`}
                onClick={() => setFilter(st)}
              >
                {st}
              </button>
            ))}
          </div>

          <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Showing {alerts.length} alert events
          </span>
        </div>

        <div className="table-responsive">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Alert ID</th>
                <th>Bin</th>
                <th>Location</th>
                <th>Fill Level</th>
                <th>Threshold</th>
                <th>Recipient Caretaker</th>
                <th>Timestamp</th>
                <th>Status</th>
                <th>Snapshot Evidence</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="9" style={{ textAlign: 'center', padding: '30px' }}>Loading alerts log...</td>
                </tr>
              ) : alerts.length === 0 ? (
                <tr>
                  <td colSpan="9" style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>
                    No alert events recorded matching selected criteria.
                  </td>
                </tr>
              ) : (
                alerts.map((a) => (
                  <tr key={a.id}>
                    <td>
                      <strong>#{a.id}</strong>
                    </td>
                    <td>
                      <span className="bin-code-pill">{a.bin_code}</span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--text-secondary)' }}>
                        <MapPin size={12} />
                        <span>{a.location || 'N/A'}</span>
                      </div>
                    </td>
                    <td>
                      <span className="status-badge critical">
                        {a.fill_percentage.toFixed(1)}%
                      </span>
                    </td>
                    <td>{a.threshold}%</td>
                    <td>{a.recipient}</td>
                    <td>{new Date(a.sent_at).toLocaleString()}</td>
                    <td>
                      <span className={`status-badge ${a.status === 'SENT' ? 'normal' : a.status === 'SIMULATED' ? 'warning' : 'critical'}`}>
                        {a.status}
                      </span>
                    </td>
                    <td>
                      {a.snapshot_path ? (
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => setPreviewSnapshot(alertService.getSnapshotUrl(a.id))}
                        >
                          <Eye size={13} />
                          View Snapshot
                        </button>
                      ) : (
                        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>No Image</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Snapshot Preview Modal */}
      {previewSnapshot && (
        <div className="modal-overlay" onClick={() => setPreviewSnapshot(null)}>
          <div className="modal-card" style={{ maxWidth: '680px' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 700 }}>AI Annotated Alert Snapshot Evidence</h3>
              <button className="btn btn-secondary btn-sm" onClick={() => setPreviewSnapshot(null)}>
                <X size={16} />
              </button>
            </div>
            <div style={{ borderRadius: '8px', overflow: 'hidden', border: '1px solid var(--border-subtle)' }}>
              <img
                src={previewSnapshot}
                alt="Alert Snapshot"
                style={{ width: '100%', height: 'auto', display: 'block' }}
                onError={(e) => {
                  e.target.src = 'https://via.placeholder.com/640x480?text=Snapshot+Stored+in+data/snapshots';
                }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AlertsPage;
