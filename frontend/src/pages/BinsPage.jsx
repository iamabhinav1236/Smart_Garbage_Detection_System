import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Trash2,
  PlusCircle,
  Play,
  Square,
  Edit,
  Eye,
  Crosshair,
  AlertTriangle,
  MapPin,
  Search
} from 'lucide-react';
import { binService } from '../services/api';
import { useNotification } from '../context/NotificationContext';
import RoiModal from '../components/RoiModal';

const BinsPage = () => {
  const navigate = useNavigate();
  const { showToast } = useNotification();

  const [bins, setBins] = useState([]);
  const [filter, setFilter] = useState('ALL');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [binToDelete, setBinToDelete] = useState(null);
  const [calibratingBin, setCalibratingBin] = useState(null);

  const fetchBins = async () => {
    try {
      const res = await binService.getAll();
      setBins(res.data);
    } catch (err) {
      showToast('Failed to load bins list', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBins();
  }, []);

  const handleToggleMonitoring = async (bin) => {
    try {
      if (bin.active) {
        await binService.stopMonitoring(bin.id);
        showToast(`Stopped monitoring ${bin.bin_id}`, 'info');
      } else {
        await binService.startMonitoring(bin.id);
        showToast(`Started monitoring ${bin.bin_id}`, 'success');
      }
      fetchBins();
    } catch (err) {
      showToast('Error updating monitoring status', 'error');
    }
  };

  const confirmDelete = async () => {
    if (!binToDelete) return;
    try {
      await binService.delete(binToDelete.id);
      showToast(`Bin ${binToDelete.bin_id} removed successfully`, 'success');
      setBinToDelete(null);
      fetchBins();
    } catch (err) {
      showToast('Failed to delete bin', 'error');
    }
  };

  const filteredBins = bins.filter((b) => {
    const matchesSearch =
      b.bin_id.toLowerCase().includes(search.toLowerCase()) ||
      b.name.toLowerCase().includes(search.toLowerCase()) ||
      b.location.toLowerCase().includes(search.toLowerCase());

    if (!matchesSearch) return false;

    if (filter === 'CRITICAL') return b.current_fill_percentage >= (b.threshold || 85.0);
    if (filter === 'WARNING') return b.current_fill_percentage >= 60.0 && b.current_fill_percentage < (b.threshold || 85.0);
    if (filter === 'NORMAL') return b.current_fill_percentage < 60.0;
    if (filter === 'OFFLINE') return !b.camera_online;
    return true;
  });

  return (
    <div className="page-container">
      <div className="dashboard-header">
        <div className="dashboard-title-area">
          <h1>Dustbin Management &amp; Registry</h1>
          <p>Configure smart dustbins, inspect network endpoints, and calibrate ROIs</p>
        </div>

        <button className="btn btn-primary" onClick={() => navigate('/bins/new')}>
          <PlusCircle size={16} />
          Register New Bin
        </button>
      </div>

      <div className="table-card">
        {/* Filter bar */}
        <div className="table-filter-bar">
          <div className="filter-pills">
            {['ALL', 'NORMAL', 'WARNING', 'CRITICAL', 'OFFLINE'].map((status) => (
              <button
                key={status}
                className={`filter-pill ${filter === status ? 'active' : ''}`}
                onClick={() => setFilter(status)}
              >
                {status}
              </button>
            ))}
          </div>

          <div style={{ position: 'relative', width: '260px' }}>
            <input
              type="text"
              className="form-input"
              style={{ width: '100%', paddingLeft: '36px', height: '36px' }}
              placeholder="Search by ID or Location..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <Search size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          </div>
        </div>

        {/* Bins Table */}
        <div className="table-responsive">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Bin ID</th>
                <th>Name</th>
                <th>Location</th>
                <th>Camera Status</th>
                <th>Current Fill</th>
                <th>Threshold</th>
                <th>Monitoring</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: 'center', padding: '30px' }}>Loading registered bins...</td>
                </tr>
              ) : filteredBins.length === 0 ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>
                    No matching dustbins found.
                  </td>
                </tr>
              ) : (
                filteredBins.map((bin) => {
                  const isCrit = bin.current_fill_percentage >= (bin.threshold || 85.0);
                  const isWarn = bin.current_fill_percentage >= 60.0 && !isCrit;
                  const statusClass = isCrit ? 'critical' : isWarn ? 'warning' : 'normal';

                  return (
                    <tr key={bin.id}>
                      <td>
                        <strong className="bin-code-pill">{bin.bin_id}</strong>
                      </td>
                      <td>
                        <strong>{bin.name}</strong>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--text-secondary)' }}>
                          <MapPin size={13} />
                          <span>{bin.location}</span>
                        </div>
                      </td>
                      <td>
                        <span className={`status-badge ${bin.camera_online ? 'online' : 'offline'}`}>
                          {bin.camera_online ? 'ONLINE' : 'OFFLINE'}
                        </span>
                      </td>
                      <td>
                        <span className={`status-badge ${statusClass}`}>
                          {bin.current_fill_percentage.toFixed(1)}%
                        </span>
                      </td>
                      <td>{bin.threshold}%</td>
                      <td>
                        <button
                          className={`btn btn-sm ${bin.active ? 'btn-secondary' : 'btn-primary'}`}
                          onClick={() => handleToggleMonitoring(bin)}
                        >
                          {bin.active ? <Square size={13} /> : <Play size={13} />}
                          {bin.active ? 'Stop' : 'Start'}
                        </button>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '6px' }}>
                          <button
                            className="btn btn-secondary btn-sm"
                            title="Inspect Details"
                            onClick={() => navigate(`/bins/${bin.id}`)}
                          >
                            <Eye size={14} />
                          </button>
                          <button
                            className="btn btn-secondary btn-sm"
                            title="Edit Bin"
                            onClick={() => navigate(`/bins/${bin.id}/edit`)}
                          >
                            <Edit size={14} />
                          </button>
                          <button
                            className="btn btn-secondary btn-sm"
                            title="Calibrate ROI"
                            onClick={() => setCalibratingBin(bin)}
                          >
                            <Crosshair size={14} />
                          </button>
                          <button
                            className="btn btn-outline-danger btn-sm"
                            title="Remove Bin"
                            onClick={() => setBinToDelete(bin)}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {binToDelete && (
        <div className="modal-overlay">
          <div className="modal-card" style={{ maxWidth: '460px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--danger)', marginBottom: '14px' }}>
              <AlertTriangle size={24} />
              <h3 style={{ fontSize: '18px', fontWeight: 700 }}>Confirm Bin Removal</h3>
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: 1.5 }}>
              Are you sure you want to remove <strong>{binToDelete.bin_id} ({binToDelete.name})</strong>? This will permanently delete its configuration and historical readings.
            </p>
            <div className="form-actions" style={{ marginTop: '24px' }}>
              <button className="btn btn-secondary" onClick={() => setBinToDelete(null)}>
                Cancel
              </button>
              <button className="btn btn-danger" onClick={confirmDelete}>
                Yes, Delete Bin
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Calibration Modal */}
      {calibratingBin && (
        <RoiModal
          bin={calibratingBin}
          onClose={() => setCalibratingBin(null)}
          onSaved={() => fetchBins()}
        />
      )}
    </div>
  );
};

export default BinsPage;
