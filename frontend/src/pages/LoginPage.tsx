import React, { useState } from 'react';
import { ShieldAlert, LogIn, Lock, Mail, Sparkles, AlertCircle } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader } from '../components/ui/Card';
import { useAuth } from '../context/AuthContext';

interface LoginPageProps {
  onNavigate: (page: string) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onNavigate }) => {
  const { login, demoLogin } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      // Auto-route based on email domain
      if (email.includes('admin') || email.includes('bbmp') || email.includes('gov.in')) {
        onNavigate('admin-dashboard');
      } else {
        onNavigate('citizen-dashboard');
      }
    } catch (err: any) {
      setError(err.message || 'Invalid email or password');
    } finally {
      setLoading(false);
    }
  };

  const handleDemo = async (role: 'citizen' | 'admin') => {
    setLoading(true);
    setError(null);
    try {
      await demoLogin(role);
      onNavigate(role === 'admin' ? 'admin-dashboard' : 'citizen-dashboard');
    } catch (err: any) {
      setError(err.message || 'Demo login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-6">
        
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 rounded-2xl bg-slate-900 text-teal-400 border border-slate-800 shadow-md">
            <ShieldAlert className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900">Sign in to CivicPulse AI</h2>
          <p className="text-xs text-slate-500">Citizen Reporting & Municipal Operations Console</p>
        </div>

        {/* Demo Fast-Login Cards */}
        <div className="bg-slate-50 p-4 rounded-xl border border-slate-200/80 space-y-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-amber-500" />
            Quick Demo Accounts (One-Click)
          </div>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => handleDemo('citizen')}
              className="p-2.5 bg-white border border-slate-200 rounded-lg text-left hover:border-teal-500 transition-all shadow-xs"
            >
              <div className="font-semibold text-xs text-slate-900">Citizen Account</div>
              <div className="text-[10px] text-slate-500 truncate">citizen@example.com</div>
              <div className="text-[9px] text-teal-600 font-medium mt-1">Submit & track reports →</div>
            </button>
            <button
              type="button"
              onClick={() => handleDemo('admin')}
              className="p-2.5 bg-white border border-slate-200 rounded-lg text-left hover:border-teal-500 transition-all shadow-xs"
            >
              <div className="font-semibold text-xs text-slate-900">Municipal Admin</div>
              <div className="text-[10px] text-slate-500 truncate">admin@civicpulse.gov.in</div>
              <div className="text-[9px] text-teal-600 font-medium mt-1">Full control & GIS dispatch →</div>
            </button>
          </div>
        </div>

        {/* Form Card */}
        <Card>
          <CardContent className="p-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">Email Address</label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Enter your email"
                    className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">Password</label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                  />
                </div>
              </div>

              <Button
                type="submit"
                variant="primary"
                className="w-full mt-2"
                loading={loading}
                icon={<LogIn className="w-4 h-4" />}
              >
                Sign In
              </Button>
            </form>

            <div className="mt-4 pt-4 border-t border-slate-100 text-center text-xs text-slate-500">
              Don't have an account?{' '}
              <button
                type="button"
                onClick={() => onNavigate('register')}
                className="font-semibold text-teal-600 hover:text-teal-700"
              >
                Register as Citizen
              </button>
            </div>
          </CardContent>
        </Card>

      </div>
    </div>
  );
};
