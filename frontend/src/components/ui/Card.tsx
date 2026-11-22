import React from 'react';

export const Card: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className = '' }) => {
  return (
    <div className={`bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 shadow-xs overflow-hidden transition-colors ${className}`}>
      {children}
    </div>
  );
};

export const CardHeader: React.FC<{
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}> = ({ title, subtitle, action, icon, className = '' }) => {
  return (
    <div className={`p-5 border-b border-slate-100 dark:border-slate-800/80 flex items-center justify-between ${className}`}>
      <div className="flex items-center gap-3">
        {icon && <div className="text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 p-2 rounded-lg">{icon}</div>}
        <div>
          <h3 className="text-base font-semibold text-slate-900 dark:text-white leading-snug">{title}</h3>
          {subtitle && <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{subtitle}</p>}
        </div>
      </div>
      {action && <div>{action}</div>}
    </div>
  );
};

export const CardContent: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className = '' }) => {
  return <div className={`p-5 ${className}`}>{children}</div>;
};

export const StatCard: React.FC<{
  title: string;
  value: string | number;
  subtitle?: string;
  change?: string;
  isPositive?: boolean;
  icon: React.ReactNode;
  accentColor?: string;
}> = ({ title, value, subtitle, change, isPositive, icon, accentColor = 'bg-blue-50 text-blue-600' }) => {
  return (
    <Card className="hover:border-slate-300 dark:hover:border-slate-700 transition-all">
      <CardContent className="p-5">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">{title}</span>
          <div className={`p-2 rounded-lg ${accentColor}`}>{icon}</div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">{value}</span>
          {change && (
            <span className={`text-xs font-medium ${isPositive ? 'text-emerald-600' : 'text-red-600'}`}>
              {change}
            </span>
          )}
        </div>
        {subtitle && <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{subtitle}</p>}
      </CardContent>
    </Card>
  );
};
