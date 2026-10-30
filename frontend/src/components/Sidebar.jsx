import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Trash2,
  PlusCircle,
  BarChart3,
  Bell,
  Mail,
  Settings,
  LogOut,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const Sidebar = ({ isCollapsed }) => {
  const { logout } = useAuth();

  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Bins', path: '/bins', icon: Trash2 },
    { name: 'Add Bin', path: '/bins/new', icon: PlusCircle },
    { name: 'Analytics', path: '/analytics', icon: BarChart3 },
    { name: 'Alerts', path: '/alerts', icon: Bell },
    { name: 'Caretaker / Email', path: '/settings/email', icon: Mail },
    { name: 'Settings', path: '/settings/system', icon: Settings },
  ];

  return (
    <aside className={`sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <img src="/glb-logo.png" alt="GL Bajaj Institute of Technology & Management" className="sidebar-brand-logo" />
        <img src="/glb-emblem.png" alt="GL Bajaj" className="sidebar-brand-emblem" />
      </div>

      {!isCollapsed && (
        <div className="sidebar-project-tag">
          <div className="logo-text">Smart Garbage System</div>
          <div className="logo-sub">AI Waste Surveillance</div>
        </div>
      )}

      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              title={isCollapsed ? item.name : undefined}
            >
              <Icon className="nav-item-icon" />
              {!isCollapsed && <span>{item.name}</span>}
            </NavLink>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <button className="logout-btn" onClick={logout} title="Sign Out">
          <LogOut size={18} />
          {!isCollapsed && <span>Logout</span>}
        </button>
        {!isCollapsed && <div className="sidebar-credit">Dept. of CSE (AIML) · Session 2025–26</div>}
      </div>
    </aside>
  );
};

export default Sidebar;
