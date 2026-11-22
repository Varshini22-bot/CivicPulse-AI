import React from 'react';

export const PriorityBadge: React.FC<{ level: string; score?: number }> = ({ level, score }) => {
  const styles: Record<string, string> = {
    Critical: 'bg-red-50 text-red-700 border-red-200 ring-red-500/20',
    High: 'bg-orange-50 text-orange-700 border-orange-200 ring-orange-500/20',
    Medium: 'bg-amber-50 text-amber-700 border-amber-200 ring-amber-500/20',
    Low: 'bg-emerald-50 text-emerald-700 border-emerald-200 ring-emerald-500/20',
  };

  const dots: Record<string, string> = {
    Critical: 'bg-red-500',
    High: 'bg-orange-500',
    Medium: 'bg-amber-500',
    Low: 'bg-emerald-500',
  };

  const badgeStyle = styles[level] || 'bg-slate-50 text-slate-700 border-slate-200 ring-slate-500/20';
  const dotColor = dots[level] || 'bg-slate-400';

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border shadow-xs ${badgeStyle}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor} animate-pulse`} />
      {level} {score !== undefined && <span className="opacity-75">({score})</span>}
    </span>
  );
};

export const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const styles: Record<string, string> = {
    Submitted: 'bg-blue-50 text-blue-700 border-blue-200',
    'Under Review': 'bg-purple-50 text-purple-700 border-purple-200',
    Verified: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    Assigned: 'bg-cyan-50 text-cyan-700 border-cyan-200',
    'In Progress': 'bg-amber-50 text-amber-700 border-amber-200',
    Resolved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    Rejected: 'bg-slate-100 text-slate-600 border-slate-200',
  };

  const badgeStyle = styles[status] || 'bg-slate-50 text-slate-700 border-slate-200';

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${badgeStyle}`}>
      {status}
    </span>
  );
};

export const CategoryBadge: React.FC<{ category: string }> = ({ category }) => {
  return (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
      {category}
    </span>
  );
};
