import React from 'react';

const MetricCard = ({ title, value, icon: Icon, colorClass = 'emerald', subtitle }) => {
  return (
    <div className="metric-card">
      <div className="metric-info">
        <h4>{title}</h4>
        <div className="metric-value">{value}</div>
        {subtitle && <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>{subtitle}</p>}
      </div>
      <div className={`metric-icon-box ${colorClass}`}>
        {Icon && <Icon size={24} />}
      </div>
    </div>
  );
};

export default MetricCard;
