import React, { useState, useEffect } from 'react';
import {
  MapPin, Filter, Layers, Navigation, Eye, AlertTriangle,
  RefreshCw, List, Compass, Info, CheckCircle2
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card, CardContent } from '../components/ui/Card';
import { PriorityBadge, StatusBadge, CategoryBadge } from '../components/ui/Badge';
import { LeafletMap } from '../components/maps/LeafletMap';
import { api } from '../services/api';
import { MapMarker, Hotspot, Category } from '../types';

interface MapPageProps {
  onNavigate: (page: string, params?: any) => void;
}

export const MapPage: React.FC<MapPageProps> = ({ onNavigate }) => {
  const [markers, setMarkers] = useState<MapMarker[]>([]);
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedPriority, setSelectedPriority] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [selectedArea, setSelectedArea] = useState('');

  // View state
  const [showHotspots, setShowHotspots] = useState(true);
  const [showListView, setShowListView] = useState(false);
  const [selectedMarkerId, setSelectedMarkerId] = useState<string | undefined>(undefined);
  const [mapCenter, setMapCenter] = useState<[number, number]>([12.9716, 77.5946]); // Bengaluru Center
  const [mapZoom, setMapZoom] = useState(12);

  useEffect(() => {
    api.getCategories().then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    loadMapData();
  }, [selectedCategory, selectedPriority, selectedStatus, selectedArea]);

  const loadMapData = async () => {
    setLoading(true);
    try {
      const [markerData, hotspotData] = await Promise.all([
        api.getMapReports({
          category_id: selectedCategory || undefined,
          priority: selectedPriority || undefined,
          status: selectedStatus || undefined,
          area: selectedArea || undefined,
        }),
        api.getHotspots(),
      ]);
      setMarkers(markerData);
      setHotspots(hotspotData);
    } catch {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  const handleFocusArea = (lat: number, lng: number) => {
    setMapCenter([lat, lng]);
    setMapZoom(14);
  };

  return (
    <div className="space-y-4 py-6">
      
      {/* Page Title & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Geospatial Infrastructure GIS</h1>
          <p className="text-xs text-slate-500">Live spatial mapping of municipal complaints, density clusters, and DBSCAN priority hotspots</p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowHotspots(!showHotspots)}
            className={showHotspots ? 'bg-teal-50 border-teal-300 text-teal-800' : ''}
            icon={<Layers className="w-3.5 h-3.5" />}
          >
            {showHotspots ? 'Hotspots Active' : 'Show Hotspots'}
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowListView(!showListView)}
            icon={<List className="w-3.5 h-3.5" />}
          >
            {showListView ? 'Hide List' : 'Split View'}
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={loadMapData}
            icon={<RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-3 rounded-xl border border-slate-200/80 shadow-xs flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="font-semibold text-slate-700 flex items-center gap-1">
            <Filter className="w-3.5 h-3.5 text-slate-500" /> Filters:
          </span>

          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="border border-slate-300 rounded-lg px-2.5 py-1 text-xs bg-white focus:ring-2 focus:ring-teal-500"
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>

          <select
            value={selectedPriority}
            onChange={(e) => setSelectedPriority(e.target.value)}
            className="border border-slate-300 rounded-lg px-2.5 py-1 text-xs bg-white focus:ring-2 focus:ring-teal-500"
          >
            <option value="">All Priorities</option>
            <option value="Critical">Critical (Red)</option>
            <option value="High">High (Orange)</option>
            <option value="Medium">Medium (Yellow)</option>
            <option value="Low">Low (Green)</option>
          </select>

          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="border border-slate-300 rounded-lg px-2.5 py-1 text-xs bg-white focus:ring-2 focus:ring-teal-500"
          >
            <option value="">All Statuses</option>
            <option value="Submitted">Submitted</option>
            <option value="Under Review">Under Review</option>
            <option value="Verified">Verified</option>
            <option value="Assigned">Assigned</option>
            <option value="In Progress">In Progress</option>
            <option value="Resolved">Resolved</option>
          </select>

          <select
            value={selectedArea}
            onChange={(e) => setSelectedArea(e.target.value)}
            className="border border-slate-300 rounded-lg px-2.5 py-1 text-xs bg-white focus:ring-2 focus:ring-teal-500"
          >
            <option value="">All Municipal Wards</option>
            <option value="Koramangala">Koramangala</option>
            <option value="Indiranagar">Indiranagar</option>
            <option value="Whitefield">Whitefield</option>
            <option value="HSR Layout">HSR Layout</option>
            <option value="CBD / Central">CBD / Central</option>
            <option value="Jayanagar">Jayanagar</option>
            <option value="Malleshwaram">Malleshwaram</option>
            <option value="Electronic City">Electronic City</option>
            <option value="Hebbal">Hebbal</option>
          </select>
        </div>

        {/* Legend */}
        <div className="hidden lg:flex items-center gap-3 text-[11px] font-medium text-slate-600">
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-red-500" /> Critical</span>
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-orange-500" /> High</span>
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> Medium</span>
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Low</span>
          <span className="text-slate-400">({markers.length} points mapped)</span>
        </div>
      </div>

      {/* Main Map Viewport */}
      <div className={`grid grid-cols-1 ${showListView ? 'lg:grid-cols-3' : 'lg:grid-cols-1'} gap-4`}>
        
        {/* Map Container */}
        <div className={showListView ? 'lg:col-span-2' : 'col-span-1'}>
          <LeafletMap
            markers={markers}
            hotspots={hotspots}
            showHotspots={showHotspots}
            center={mapCenter}
            zoom={mapZoom}
            selectedReportId={selectedMarkerId}
            onMarkerClick={(id) => {
              setSelectedMarkerId(id);
              onNavigate('issue-details', { reportId: id });
            }}
            height="620px"
          />
        </div>

        {/* Optional Split-Screen List View */}
        {showListView && (
          <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs p-4 flex flex-col h-[620px]">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <span className="font-semibold text-xs text-slate-700 uppercase tracking-wider">
                Mapped Issues ({markers.length})
              </span>
              <span className="text-[11px] text-slate-400">Click to focus</span>
            </div>

            <div className="flex-1 overflow-y-auto divide-y divide-slate-100 mt-2 pr-1 space-y-1">
              {markers.map((m) => (
                <div
                  key={m.id}
                  onClick={() => handleFocusArea(m.latitude, m.longitude)}
                  className="p-3 text-xs hover:bg-slate-50 rounded-lg cursor-pointer transition-colors space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-slate-900">#{m.tracking_number}</span>
                    <PriorityBadge level={m.priority_level} score={Math.round(m.priority_score)} />
                  </div>
                  <div className="font-medium text-slate-900 line-clamp-1">{m.title}</div>
                  <div className="flex items-center justify-between text-slate-500 text-[11px]">
                    <span>{m.area || 'Bengaluru'}</span>
                    <StatusBadge status={m.status} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>

      {/* Active DBSCAN Hotspots Bar */}
      {showHotspots && hotspots.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="w-4 h-4 text-red-500" />
              <span className="font-bold text-xs text-slate-900 uppercase tracking-wider">
                Active Spatial Hotspot Clusters (DBSCAN ε=800m, Min=3)
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {hotspots.slice(0, 4).map((h) => (
                <div
                  key={h.hotspot_id}
                  onClick={() => handleFocusArea(h.center_latitude, h.center_longitude)}
                  className="p-3 rounded-lg border border-slate-200 bg-slate-50 hover:bg-teal-50/50 hover:border-teal-300 cursor-pointer transition-all text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900">{h.area_name}</span>
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-sm bg-red-100 text-red-700">
                      {h.total_reports} Reports
                    </span>
                  </div>
                  <div className="text-slate-500 mt-1 line-clamp-2">{h.insight_summary}</div>
                  <div className="text-[10px] text-teal-600 font-semibold mt-2">Center map on hotspot →</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

    </div>
  );
};
