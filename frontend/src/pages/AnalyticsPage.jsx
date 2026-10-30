import React, { useState, useEffect } from 'react';
import { CHART } from '../theme';
import {
  BarChart3,
  TrendingUp,
  AlertTriangle,
  Clock,
  PieChart as PieIcon,
  Filter
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend
} from 'recharts';
import MetricCard from '../components/MetricCard';
import { analyticsService, binService } from '../services/api';
import { useNotification } from '../context/NotificationContext';

const AnalyticsPage = () => {
  const { showToast } = useNotification();
  const [hours, setHours] = useState(24);
  const [selectedBin, setSelectedBin] = useState('');
  const [bins, setBins] = useState([]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchAnalytics = async () => {
    try {
      const [analyticsRes, binsRes] = await Promise.all([
        analyticsService.getAnalytics(hours, selectedBin || null),
        binService.getAll(),
      ]);
      setData(analyticsRes.data);
      setBins(binsRes.data);
    } catch (err) {
      showToast('Failed to load analytics datasets', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [hours, selectedBin]);

  if (loading || !data) {
    return (
      <div className="page-container">
        <div style={{ textAlign: 'center', padding: '60px' }}>Aggregating AI detection analytics...</div>
      </div>
    );
  }

  const { time_series, alerts_per_bin, status_distribution, kpis } = data;

  return (
    <div className="page-container">
      {/* Header */}
      <div className="dashboard-header">
        <div className="dashboard-title-area">
          <h1>Analytics &amp; Detection Telemetry</h1>
          <p>Historical waste patterns, critical threshold occurrences, and camera uptimes</p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <select
            className="form-select"
            value={selectedBin}
            onChange={(e) => setSelectedBin(e.target.value)}
            style={{ width: '180px' }}
          >
            <option value="">All Dustbins</option>
            {bins.map((b) => (
              <option key={b.id} value={b.id}>{b.bin_id} ({b.name})</option>
            ))}
          </select>

          <select
            className="form-select"
            value={hours}
            onChange={(e) => setHours(Number(e.target.value))}
            style={{ width: '140px' }}
          >
            <option value="12">Last 12 Hours</option>
            <option value="24">Last 24 Hours</option>
            <option value="72">Last 3 Days</option>
            <option value="168">Last 7 Days</option>
          </select>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="metrics-grid">
        <MetricCard
          title="MAXIMUM FILL RECORDED"
          value={`${kpis.max_recorded_fill}%`}
          icon={TrendingUp}
          colorClass="amber"
          subtitle="Peak Fill Level Recorded"
        />
        <MetricCard
          title="TOTAL ALERTS SENT"
          value={kpis.total_alerts}
          icon={AlertTriangle}
          colorClass="red"
          subtitle="Caretaker Notifications"
        />
        <MetricCard
          title="THRESHOLD BREACHES"
          value={kpis.threshold_breaches}
          icon={BarChart3}
          colorClass="blue"
          subtitle=">= 85% Fill Events"
        />
        <MetricCard
          title="SYSTEM UPTIME"
          value={`${kpis.system_uptime_pct}%`}
          icon={Clock}
          colorClass="emerald"
          subtitle="High Availability Surveillance"
        />
      </div>

      {/* Charts Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '24px', marginBottom: '32px' }}>
        {/* Line Chart: Fill Level vs Time */}
        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '16px', padding: '24px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '18px' }}>
            Fill Level Over Time (%)
          </h3>
          <div style={{ width: '100%', height: '280px' }}>
            {time_series.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={time_series}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} />
                  <XAxis dataKey="timestamp" stroke={CHART.axis} fontSize={11} />
                  <YAxis domain={[0, 100]} stroke={CHART.axis} fontSize={11} unit="%" />
                  <Tooltip
                    contentStyle={CHART.tooltip}
                  />
                  <Line
                    type="monotone"
                    dataKey="fill_percentage"
                    name="Fill Level"
                    stroke={CHART.line}
                    strokeWidth={2.5}
                    dot={{ r: 2 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ textAlign: 'center', padding: '100px', color: 'var(--text-muted)' }}>
                No readings data available for selected filter.
              </div>
            )}
          </div>
        </div>

        {/* Donut Chart: Normal vs Warning vs Critical Bins */}
        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '16px', padding: '24px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '18px' }}>
            Current Bin Fill Level Distribution
          </h3>
          <div style={{ width: '100%', height: '280px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={status_distribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={95}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {status_distribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={CHART.status[index] || entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={CHART.tooltip}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Bar Chart: Alerts per Bin */}
      <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '16px', padding: '24px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '18px' }}>
          Cumulative Critical Alerts per Dustbin Node
        </h3>
        <div style={{ width: '100%', height: '260px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={alerts_per_bin}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} />
              <XAxis dataKey="bin_code" stroke={CHART.axis} fontSize={11} />
              <YAxis stroke={CHART.axis} fontSize={11} allowDecimals={false} />
              <Tooltip
                contentStyle={CHART.tooltip}
              />
              <Bar dataKey="alert_count" name="Total Alerts Sent" fill={CHART.alertBar} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsPage;
