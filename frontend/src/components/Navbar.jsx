import React, { useState, useEffect } from 'react';
import { Menu, Bell, Shield, Activity, Wifi } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useNotification } from '../context/NotificationContext';
import { useNavigate } from 'react-router-dom';

const Navbar = ({ onToggleSidebar, isSidebarCollapsed }) => {
  const { user } = useAuth();
  const { unreadAlertsCount, clearUnread } = useNotification();
  const [currentTime, setCurrentTime] = useState(new Date());
  const navigate = useNavigate();

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const handleAlertsClick = () => {
    clearUnread();
    navigate('/alerts');
  };

  return (
    <header className="navbar">
      <div className="navbar-left">
        <button
          className="sidebar-toggle-btn"
          onClick={onToggleSidebar}
          title="Toggle Navigation"
        >
          <Menu size={18} />
        </button>
        <span className="navbar-title">Smart Garbage Surveillance Hub</span>
      </div>

      <div className="navbar-right">
        {/* Real-time System Active Indicator */}
        <div className="system-status-indicator" title="YOLOv8 Edge Computer Vision Active">
          <div className="status-dot"></div>
          <span>AI ENGINE ACTIVE</span>
        </div>

        {/* Live Date Time */}
        <div className="datetime-display">
          {currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })} • {currentTime.toLocaleDateString()}
        </div>

        {/* Notification Bell */}
        <button
          className="notification-bell-btn"
          onClick={handleAlertsClick}
          title="Alerts History"
        >
          <Bell size={18} />
          {unreadAlertsCount > 0 && (
            <span className="notification-badge-count">{unreadAlertsCount}</span>
          )}
        </button>

        {/* Admin Profile */}
        <div className="user-profile-pill">
          <div className="user-avatar">
            <Shield size={14} />
          </div>
          <span className="user-name">{user?.full_name || 'Admin'}</span>
        </div>
      </div>
    </header>
  );
};

export default Navbar;
