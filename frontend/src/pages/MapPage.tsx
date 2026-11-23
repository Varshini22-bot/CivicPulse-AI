import React, { useState, useEffect } from 'react';
import {
  MapPin, Filter, Layers, Navigation, Eye, AlertTriangle,
  RefreshCw, List, Compass, Info, CheckCircle2, GitCommit, Activity
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card, CardContent } from '../components/ui/Card';
import { PriorityBadge, StatusBadge, CategoryBadge } from '../components/ui/Badge';
import { LeafletMap } from '../components/maps/LeafletMap';
import { api } from '../services/api';
import { MapMarker, Hotspot, Category, RecurringCorridor } from '../types';

interface MapPageProps {
  onNavigate: (page: string, params?: any) => void;
}

export const MapPage: React.FC<MapPageProps> = ({ onNavigate }) => {
  const [markers, setMarkers] = useState<MapMarker[]>([]);
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  const [corridors, setCorridors] = useState<RecurringCorridor[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedPriority, setSelectedPriority] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [selectedArea, setSelectedArea] = useState('');

  // View state & Cluster toggle: 'hdbscan' | 'dbscan' | 'none'
  const [clusterMode, setClusterMode] = useState<'hdbscan' | 'dbscan' | 'none'>('hdbscan');
  const [showCorridors, setShowCorridors] = useState(true);
  const [showListView, setShowListView] = useState(false);
  const [selectedMarkerId, setSelectedMarkerId] = useState<string | undefined>(undefined);
  const [mapCenter, setMapCenter] = useState<[number, number]>([12.9716, 77.5946]); // Bengaluru Center
  const [mapZoom, setMapZoom] = useState(12);

  useEffect(() => {
    api.getCategories().then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    loadMapData();
  }, [selectedCategory, selectedPriority, selectedStatus, selectedArea, clusterMode, showCorridors]);

  const loadMapData = async () => {
    setLoading(true);
    try {
      const promises: [Promise<MapMarker[]>, Promise<Hotspot[]>, Promise<RecurringCorridor[]>] = [
        api.getMapReports({
          category_id: selectedCategory || undefined,
          priority: selectedPriority || undefined,
          status: selectedStatus || undefined,
          area: selectedArea || undefined,
        }),
        clusterMode !== 'none'
          ? api.getHotspotsV2(clusterMode, 14, 3)
          : Promise.resolve([]),
        showCorridors
          ? api.getRecurringCorridors()
          : Promise.resolve([]),
      ];

      const [markerData, hotspotData, corridorData] = await Promise.all(promises);
      setMarkers(markerData);
      setHotspots(hotspotData);
      setCorridors(corridorData);
    } catch {
      // Handle error gracefully
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
      
      {/* Persistent Synthetic Demo Data Banner */}
      <div className="bg-amber-500/10 border border-amber-500/30 text-amber-900 dark:text-amber-200 px-4 py-2.5 rounded-xl text-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 shadow-xs">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
          <span>
            <strong>Synthetic Demo Data:</strong> Seeded records for municipal decision-support evaluation and algorithmic stress-testing. Original citizen submissions are never deleted or merged automatically.
          </span>
        </div>
        <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-amber-500/20 text-amber-800 dark:text-amber-300 whitespace-nowrap">
          Evaluation Mode
        </span>
      </div>

      {/* Page Title & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">Geospatial Infrastructure GIS</h1>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Spatial distribution of municipal reports, density clusters, and OpenStreetMap chronic recurrence corridors
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Cluster Mode Selector */}
          <div className="flex items-center rounded-lg border border-slate-300 dark:border-slate-700 p-0.5 bg-slate-100 dark:bg-slate-800 text-xs">
            <button
              type="button"
              onClick={() => setClusterMode('hdbscan')}
              className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                clusterMode === 'hdbscan'
                  ? 'bg-white dark:bg-slate-700 text-teal-800 dark:text-teal-300 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
              }`}
              title="HDBSCAN hierarchical density clustering in spherical radians"
            >
              HDBSCAN (Provisional)
            </button>
            <button
              type="button"
              onClick={() => setClusterMode('dbscan')}
              className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                clusterMode === 'dbscan'
                  ? 'bg-white dark:bg-slate-700 text-teal-800 dark:text-teal-300 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
              }`}
              title="DBSCAN provisional clustering (eps=300m, min_samples=3)"
            >
              DBSCAN (eps=300m)
            </button>
            <button
              type="button"
              onClick={() => setClusterMode('none')}
              className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                clusterMode === 'none'
                  ? 'bg-white dark:bg-slate-700 text-teal-800 dark:text-teal-300 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
              }`}
            >
              Markers Only
            </button>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowCorridors(!showCorridors)}
            className={showCorridors ? 'bg-amber-50 dark:bg-amber-950/40 border-amber-300 text-amber-800 dark:text-amber-300' : ''}
            icon={<Activity className="w-3.5 h-3.5" />}
          >
            {showCorridors ? 'Chronic Corridors On' : 'Corridors Off'}
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
      <div className="bg-white dark:bg-slate-900 p-3 rounded-xl border border-slate-200/80 dark:border-slate-800 shadow-xs flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1">
            <Filter className="w-3.5 h-3.5 text-slate-500" /> Filters:
          </span>

          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="border border-slate-300 dark:border-slate-700 rounded-lg px-2.5 py-1 text-xs bg-white dark:bg-slate-800 focus:ring-2 focus:ring-teal-500"
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>

          <select
            value={selectedPriority}
            onChange={(e) => setSelectedPriority(e.target.value)}
            className="border border-slate-300 dark:border-slate-700 rounded-lg px-2.5 py-1 text-xs bg-white dark:bg-slate-800 focus:ring-2 focus:ring-teal-500"
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
            className="border border-slate-300 dark:border-slate-700 rounded-lg px-2.5 py-1 text-xs bg-white dark:bg-slate-800 focus:ring-2 focus:ring-teal-500"
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
            className="border border-slate-300 dark:border-slate-700 rounded-lg px-2.5 py-1 text-xs bg-white dark:bg-slate-800 focus:ring-2 focus:ring-teal-500"
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
        <div className="hidden lg:flex items-center gap-3 text-[11px] font-medium text-slate-600 dark:text-slate-400">
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
            corridors={corridors}
            showHotspots={clusterMode !== 'none'}
            showCorridors={showCorridors}
            center={mapCenter}
            zoom={mapZoom}
            selectedReportId={selectedMarkerId}
            onMarkerClick={(id) => {
              setSelectedMarkerId(id);
              onNavigate('issue-details', { reportId: id });
            }}
            height="620px"
          />

          {/* Map Footer status */}
          <div className="mt-2 text-[11px] text-slate-500 dark:text-slate-400 flex flex-wrap items-center justify-between gap-2 px-1">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span>Map Layer: {clusterMode === 'hdbscan' ? 'HDBSCAN Hierarchical Radian Density Clusters' : clusterMode === 'dbscan' ? 'Provisional Haversine DBSCAN (eps=300m)' : 'Individual Markers'}</span>
            </div>
            <span>Tiles: CartoDB Positron &bull; OSM ODbL Data Layer</span>
          </div>
        </div>

        {/* Split View Issue Drawer */}
        {showListView && (
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800 p-4 shadow-xs flex flex-col h-[620px]">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <h3 className="font-semibold text-xs text-slate-900 dark:text-slate-100">
                Visible Mapped Tickets ({markers.length})
              </h3>
              <span className="text-[10px] text-slate-400">Click to focus pin</span>
            </div>

            <div className="flex-1 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-800 space-y-1 pt-2 pr-1">
              {markers.map((m) => (
                <div
                  key={m.id}
                  onClick={() => handleFocusArea(m.latitude, m.longitude)}
                  className={`p-2.5 rounded-lg text-xs cursor-pointer transition-colors ${
                    selectedMarkerId === m.id ? 'bg-teal-50 dark:bg-teal-950/40 border border-teal-200' : 'hover:bg-slate-50 dark:hover:bg-slate-800/60'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono font-bold text-slate-900 dark:text-slate-100">#{m.tracking_number}</span>
                    <PriorityBadge level={m.priority_level} score={Math.round(m.priority_score)} />
                  </div>
                  <div className="font-medium text-slate-800 dark:text-slate-200 truncate">{m.title}</div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400 truncate mt-0.5">{m.category} &bull; {m.area || 'Bengaluru'}</div>
                  
                  <div className="flex items-center justify-between mt-2 pt-1 border-t border-slate-100 dark:border-slate-800">
                    <StatusBadge status={m.status} />
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onNavigate('issue-details', { reportId: m.id });
                      }}
                      className="text-teal-600 dark:text-teal-400 font-semibold hover:underline"
                    >
                      Dossier &rarr;
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>

    </div>
  );
};
