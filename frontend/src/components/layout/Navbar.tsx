import React, { useState, useEffect } from 'react';
import {
  ShieldAlert, MapPin, BarChart3, LayoutDashboard,
  FileText, PlusCircle, Bell, LogOut,
  ChevronDown, Sparkles, Sun, Moon
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { api } from '../../services/api';
import { NotificationItem } from '../../types';

interface NavbarProps {
  currentPage: string;
  onNavigate: (page: string, params?: any) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentPage, onNavigate }) => {
  const { user, isAuthenticated, isAdmin, logout, demoLogin } = useAuth();
  const { theme, toggleTheme, isDark } = useTheme();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [showNotifications, setShowNotifications] = useState<boolean>(false);
  const [showUserMenu, setShowUserMenu] = useState<boolean>(false);

  useEffect(() => {
    if (isAuthenticated) {
      api.getNotifications()
        .then(setNotifications)
        .catch(() => {});
    }
  }, [isAuthenticated, currentPage]);

  const unreadCount = notifications.filter(n => !n.is_read).length;

  const handleMarkAllRead = async () => {
    await api.markAllNotificationsRead();
    setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
  };

  const navLinks = [
    { id: 'landing', label: 'Home', publicOnly: false },
    { id: 'map', label: 'Live GIS Map', icon: <MapPin className="w-4 h-4" /> },
    ...(isAuthenticated && !isAdmin ? [
      { id: 'citizen-dashboard', label: 'My Reports', icon: <LayoutDashboard className="w-4 h-4" /> },
      { id: 'report-issue', label: 'Report Issue', icon: <PlusCircle className="w-4 h-4" /> },
    ] : []),
    ...(isAdmin ? [
      { id: 'admin-dashboard', label: 'Control Center', icon: <LayoutDashboard className="w-4 h-4" /> },
      { id: 'issue-management', label: 'Issue Ledger', icon: <FileText className="w-4 h-4" /> },
      { id: 'ai-analytics', label: 'AI Analytics', icon: <BarChart3 className="w-4 h-4" /> },
      { id: 'reports-export', label: 'Export BI', icon: <FileText className="w-4 h-4" /> },
    ] : []),
  ];

  return (
    <header className="sticky top-0 z-40 bg-slate-900 border-b border-slate-800 text-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Brand */}
          <div
            className="flex items-center gap-3 cursor-pointer group"
            onClick={() => onNavigate('landing')}
          >
            <div className="w-9 h-9 rounded-lg bg-teal-500/20 border border-teal-500/40 flex items-center justify-center text-teal-400 group-hover:scale-105 transition-transform">
              <ShieldAlert className="w-5 h-5 text-teal-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg tracking-tight text-white">CivicPulse</span>
                <span className="text-xs font-semibold px-1.5 py-0.5 rounded-sm bg-teal-500 text-slate-950 uppercase tracking-wider">AI</span>
              </div>
              <p className="text-[10px] text-slate-400 tracking-wide">Urban Intelligence Platform</p>
            </div>
          </div>

          {/* Navigation Items */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => (
              <button
                key={link.id}
                onClick={() => onNavigate(link.id)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  currentPage === link.id
                    ? 'bg-slate-800 text-teal-400 border border-slate-700'
                    : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                {link.icon}
                {link.label}
              </button>
            ))}
          </nav>

          {/* Right Action Controls */}
          <div className="flex items-center gap-3">
            
            {/* Quick Demo Role Switcher for seamless demonstration */}
            <div className="hidden lg:flex items-center bg-slate-800/80 p-1 rounded-lg border border-slate-700/60 text-xs">
              <span className="text-slate-400 px-2 flex items-center gap-1 font-medium">
                <Sparkles className="w-3.5 h-3.5 text-amber-400" /> Demo:
              </span>
              <button
                onClick={() => { demoLogin('citizen'); onNavigate('citizen-dashboard'); }}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                  user?.role === 'citizen' ? 'bg-teal-600 text-white' : 'text-slate-300 hover:text-white'
                }`}
              >
                Citizen
              </button>
              <button
                onClick={() => { demoLogin('admin'); onNavigate('admin-dashboard'); }}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                  isAdmin ? 'bg-teal-600 text-white' : 'text-slate-300 hover:text-white'
                }`}
              >
                Municipal Admin
              </button>
            </div>

            {/* Theme Toggle Button */}
            <button
              onClick={toggleTheme}
              title={`Switch to ${isDark ? 'Light' : 'Dark'} Mode`}
              className="p-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
            >
              {isDark ? <Sun className="w-5 h-5 text-amber-400" /> : <Moon className="w-5 h-5 text-slate-300" />}
            </button>

            {/* Notifications Bell */}
            {isAuthenticated && (
              <div className="relative">
                <button
                  onClick={() => setShowNotifications(!showNotifications)}
                  className="relative p-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
                >
                  <Bell className="w-5 h-5" />
                  {unreadCount > 0 && (
                    <span className="absolute top-1 right-1 w-4 h-4 rounded-full bg-red-500 text-[10px] font-bold text-white flex items-center justify-center ring-2 ring-slate-900">
                      {unreadCount}
                    </span>
                  )}
                </button>

                {showNotifications && (
                  <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-2xl border border-slate-200 py-2 z-50 text-slate-900">
                    <div className="flex items-center justify-between px-4 py-2 border-b border-slate-100">
                      <span className="font-semibold text-xs text-slate-700 uppercase tracking-wider">Notifications</span>
                      {unreadCount > 0 && (
                        <button
                          onClick={handleMarkAllRead}
                          className="text-xs text-teal-600 hover:text-teal-700 font-medium"
                        >
                          Mark all read
                        </button>
                      )}
                    </div>
                    <div className="max-h-72 overflow-y-auto divide-y divide-slate-100">
                      {notifications.length === 0 ? (
                        <div className="p-4 text-center text-xs text-slate-400">No new notifications</div>
                      ) : (
                        notifications.map((n) => (
                          <div
                            key={n.id}
                            className={`p-3 text-xs hover:bg-slate-50 transition-colors ${!n.is_read ? 'bg-teal-50/50' : ''}`}
                            onClick={() => {
                              api.markNotificationRead(n.id);
                              if (n.report_id) {
                                onNavigate('issue-details', { reportId: n.report_id });
                                setShowNotifications(false);
                              }
                            }}
                          >
                            <div className="font-semibold text-slate-900">{n.title}</div>
                            <p className="text-slate-600 mt-0.5 line-clamp-2">{n.message}</p>
                            <span className="text-[10px] text-slate-400 mt-1 block">
                              {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Auth Button or User Menu */}
            {isAuthenticated ? (
              <div className="relative">
                <button
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
                >
                  <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center font-bold text-xs text-teal-400 border border-slate-600">
                    {user?.full_name?.charAt(0) || 'U'}
                  </div>
                  <ChevronDown className="w-4 h-4 text-slate-400" />
                </button>

                {showUserMenu && (
                  <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-2xl border border-slate-200 py-2 z-50 text-slate-900">
                    <div className="px-4 py-2 border-b border-slate-100">
                      <div className="font-semibold text-sm text-slate-900">{user?.full_name}</div>
                      <div className="text-xs text-slate-500 truncate">{user?.email}</div>
                      <div className="mt-1 inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-teal-50 text-teal-700 border border-teal-200">
                        {isAdmin ? 'Municipal Administrator' : 'Citizen'}
                      </div>
                    </div>
                    
                    <button
                      onClick={() => {
                        onNavigate(isAdmin ? 'admin-dashboard' : 'citizen-dashboard');
                        setShowUserMenu(false);
                      }}
                      className="w-full text-left px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                    >
                      <LayoutDashboard className="w-4 h-4 text-slate-400" /> Dashboard
                    </button>

                    <button
                      onClick={() => {
                        logout();
                        setShowUserMenu(false);
                        onNavigate('landing');
                      }}
                      className="w-full text-left px-4 py-2 text-xs font-medium text-red-600 hover:bg-red-50 flex items-center gap-2"
                    >
                      <LogOut className="w-4 h-4 text-red-500" /> Sign Out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onNavigate('login')}
                  className="px-3 py-1.5 rounded-lg text-sm font-medium text-slate-300 hover:text-white transition-colors"
                >
                  Sign In
                </button>
                <button
                  onClick={() => onNavigate('register')}
                  className="px-3.5 py-1.5 rounded-lg text-sm font-semibold bg-teal-600 text-white hover:bg-teal-500 transition-colors shadow-xs"
                >
                  Register
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
