import React from 'react';
import { ShieldAlert, MapPin, Database, Cpu, Lock } from 'lucide-react';

export const Footer: React.FC<{ onNavigate: (page: string) => void }> = ({ onNavigate }) => {
  return (
    <footer className="bg-slate-900 border-t border-slate-800 text-slate-400 text-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          
          {/* Brand Info */}
          <div className="md:col-span-1">
            <div className="flex items-center gap-2 mb-3">
              <ShieldAlert className="w-5 h-5 text-teal-400" />
              <span className="font-bold text-white text-base">CivicPulse AI</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Intelligent civic infrastructure monitoring, explainable computer vision defect triage,
              and geospatial prioritization decision-support system.
            </p>
            <div className="mt-4 flex items-center gap-2 text-[11px] text-teal-400 bg-slate-800/60 px-2.5 py-1.5 rounded-lg border border-slate-700/50 w-fit">
              <span className="w-2 h-2 rounded-full bg-teal-400 animate-pulse"></span>
              Bengaluru Municipal Ward Network
            </div>
          </div>

          {/* Core Modules */}
          <div>
            <h4 className="text-xs font-semibold text-white uppercase tracking-wider mb-3">Capabilities</h4>
            <ul className="space-y-2 text-xs">
              <li className="flex items-center gap-2"><Cpu className="w-3.5 h-3.5 text-teal-400" /> Computer Vision Inspection</li>
              <li className="flex items-center gap-2"><MapPin className="w-3.5 h-3.5 text-teal-400" /> DBSCAN Geospatial Hotspots</li>
              <li className="flex items-center gap-2"><Database className="w-3.5 h-3.5 text-teal-400" /> Duplicate Detection Engine</li>
              <li className="flex items-center gap-2"><Lock className="w-3.5 h-3.5 text-teal-400" /> Role-Based Dispatch & Audit</li>
            </ul>
          </div>

          {/* Quick Links */}
          <div>
            <h4 className="text-xs font-semibold text-white uppercase tracking-wider mb-3">Platform Views</h4>
            <ul className="space-y-2 text-xs">
              <li><button onClick={() => onNavigate('landing')} className="hover:text-white transition-colors">Public Portal</button></li>
              <li><button onClick={() => onNavigate('map')} className="hover:text-white transition-colors">Interactive GIS Map</button></li>
              <li><button onClick={() => onNavigate('report-issue')} className="hover:text-white transition-colors">Submit Civic Report</button></li>
              <li><button onClick={() => onNavigate('admin-dashboard')} className="hover:text-white transition-colors">Operations Dashboard</button></li>
              <li><button onClick={() => onNavigate('ai-analytics')} className="hover:text-white transition-colors">AI Metrics & Evaluation</button></li>
            </ul>
          </div>

          {/* Decision Support Disclaimer */}
          <div>
            <h4 className="text-xs font-semibold text-white uppercase tracking-wider mb-3">Governance Notice</h4>
            <div className="text-xs text-slate-400 bg-slate-800/40 p-3 rounded-lg border border-slate-800 leading-relaxed">
              CivicPulse AI operates as an explainable decision-support platform for municipal public works authorities.
              All automated classifications, severity scores, and duplicate merges require administrative review and confirmation.
            </div>
          </div>
        </div>

        <div className="pt-8 border-t border-slate-800/80 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-4">
          <p>© 2026 CivicPulse AI Platform. Developed for Technical Portfolio & Municipal Systems Engineering Demonstration.</p>
          <div className="flex items-center gap-4">
            <span className="text-[11px] bg-slate-800 px-2.5 py-1 rounded-sm text-slate-300">Model: CivicPulse-Vision-Ensemble-v1 (87.1% Acc)</span>
            <span className="text-[11px] bg-slate-800 px-2.5 py-1 rounded-sm text-slate-300">FastAPI + React 19 + PostGIS</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
