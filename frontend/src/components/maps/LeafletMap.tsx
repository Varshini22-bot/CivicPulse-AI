import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MapMarker, Hotspot } from '../../types';

interface LeafletMapProps {
  markers?: MapMarker[];
  hotspots?: Hotspot[];
  center?: [number, number];
  zoom?: number;
  interactivePicker?: boolean;
  onLocationSelect?: (lat: number, lng: number) => void;
  selectedLocation?: [number, number] | null;
  selectedReportId?: string;
  onMarkerClick?: (reportId: string) => void;
  showHotspots?: boolean;
  className?: string;
  height?: string;
}

export const LeafletMap: React.FC<LeafletMapProps> = ({
  markers = [],
  hotspots = [],
  center = [12.9716, 77.5946], // Bengaluru center
  zoom = 12,
  interactivePicker = false,
  onLocationSelect,
  selectedLocation,
  selectedReportId,
  onMarkerClick,
  showHotspots = false,
  className = '',
  height = '500px',
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);
  const hotspotsLayerRef = useRef<L.LayerGroup | null>(null);
  const pickerMarkerRef = useRef<L.Marker | null>(null);

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current, {
        center: center,
        zoom: zoom,
        zoomControl: true,
      });

      // CartoDB Positron clean map tiles (high contrast, professional GIS appearance)
      L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19,
      }).addTo(map);

      markersLayerRef.current = L.layerGroup().addTo(map);
      hotspotsLayerRef.current = L.layerGroup().addTo(map);
      mapInstanceRef.current = map;

      // Handle map clicks in interactive picker mode
      if (interactivePicker && onLocationSelect) {
        map.on('click', (e: L.LeafletMouseEvent) => {
          onLocationSelect(e.latlng.lat, e.latlng.lng);
        });
      }
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Update center/zoom if changed
  useEffect(() => {
    if (mapInstanceRef.current && center) {
      mapInstanceRef.current.setView(center, zoom);
    }
  }, [center[0], center[1], zoom]);

  // Handle Interactive Picker Marker
  useEffect(() => {
    if (!mapInstanceRef.current || !interactivePicker) return;

    if (selectedLocation) {
      const [lat, lng] = selectedLocation;
      
      const pinIcon = L.divIcon({
        className: 'custom-picker-pin',
        html: `
          <div style="position: relative; width: 32px; height: 32px; transform: translate(-16px, -32px);">
            <svg viewBox="0 0 24 24" width="32" height="32" fill="#0f172a" stroke="#ffffff" stroke-width="2">
              <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
            </svg>
            <div style="width: 8px; height: 8px; background: #0d9488; border-radius: 50%; position: absolute; bottom: 0; left: 12px; animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>
          </div>
        `,
        iconSize: [32, 32],
        iconAnchor: [16, 32],
      });

      if (!pickerMarkerRef.current) {
        pickerMarkerRef.current = L.marker([lat, lng], {
          icon: pinIcon,
          draggable: true,
        }).addTo(mapInstanceRef.current);

        pickerMarkerRef.current.on('dragend', (e) => {
          const marker = e.target;
          const pos = marker.getLatLng();
          if (onLocationSelect) {
            onLocationSelect(pos.lat, pos.lng);
          }
        });
      } else {
        pickerMarkerRef.current.setLatLng([lat, lng]);
      }
    } else if (pickerMarkerRef.current) {
      pickerMarkerRef.current.remove();
      pickerMarkerRef.current = null;
    }
  }, [selectedLocation, interactivePicker]);

  // Render Issue Markers
  useEffect(() => {
    if (!mapInstanceRef.current || !markersLayerRef.current) return;

    markersLayerRef.current.clearLayers();

    markers.forEach((m) => {
      const color = m.color || '#3b82f6';
      const isSelected = m.id === selectedReportId;

      const markerHtml = `
        <div style="position: relative; width: 24px; height: 24px; cursor: pointer; transform: translate(-12px, -12px);">
          <div style="
            width: ${isSelected ? '24px' : '18px'};
            height: ${isSelected ? '24px' : '18px'};
            border-radius: 50%;
            background-color: ${color};
            border: 2px solid #ffffff;
            box-shadow: 0 2px 6px rgba(0,0,0,0.35);
            transition: transform 0.2s;
            margin: auto;
          "></div>
          ${m.priority_level === 'Critical' ? `
            <div style="
              position: absolute;
              inset: -4px;
              border-radius: 50%;
              border: 2px solid ${color};
              animation: ping 2s cubic-bezier(0, 0, 0.2, 1) infinite;
              opacity: 0.75;
            "></div>
          ` : ''}
        </div>
      `;

      const customIcon = L.divIcon({
        className: 'civic-marker-icon',
        html: markerHtml,
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      });

      const marker = L.marker([m.latitude, m.longitude], { icon: customIcon });

      // Popup Content
      const popupContent = `
        <div style="font-family: inherit; font-size: 13px; line-height: 1.4; padding: 2px; max-width: 240px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span style="font-weight: 700; color: #0f172a; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;">#${m.tracking_number}</span>
            <span style="
              font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 9999px;
              background-color: ${color}20; color: ${color}; border: 1px solid ${color}40;
            ">${m.priority_level} (${m.priority_score})</span>
          </div>
          <div style="font-weight: 600; color: #1e293b; margin-bottom: 4px;">${m.title}</div>
          <div style="color: #64748b; font-size: 11px; margin-bottom: 6px;">${m.category} • ${m.area || 'Bengaluru'}</div>
          <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #f1f5f9; padding-top: 6px;">
            <span style="font-size: 11px; font-weight: 500; color: #475569;">Status: <strong>${m.status}</strong></span>
            <button id="view-report-${m.id}" style="
              font-size: 11px; font-weight: 600; color: #0d9488; background: none; border: none; cursor: pointer; padding: 0;
            ">Details →</button>
          </div>
        </div>
      `;

      marker.bindPopup(popupContent, {
        closeButton: false,
        className: 'custom-civic-popup',
      });

      marker.on('click', () => {
        if (onMarkerClick) onMarkerClick(m.id);
      });

      marker.on('popupopen', () => {
        const btn = document.getElementById(`view-report-${m.id}`);
        if (btn) {
          btn.onclick = () => {
            if (onMarkerClick) onMarkerClick(m.id);
          };
        }
      });

      marker.addTo(markersLayerRef.current!);
    });
  }, [markers, selectedReportId, onMarkerClick]);

  // Render Hotspots (DBSCAN Clusters)
  useEffect(() => {
    if (!mapInstanceRef.current || !hotspotsLayerRef.current) return;

    hotspotsLayerRef.current.clearLayers();

    if (showHotspots && hotspots.length > 0) {
      hotspots.forEach((h) => {
        const circle = L.circle([h.center_latitude, h.center_longitude], {
          radius: h.radius_meters,
          color: h.urgency === 'High' ? '#ef4444' : '#f97316',
          fillColor: h.urgency === 'High' ? '#ef4444' : '#f97316',
          fillOpacity: 0.18,
          weight: 2,
          dashArray: '4, 6',
        });

        circle.bindPopup(`
          <div style="font-size: 13px; max-width: 260px;">
            <div style="font-weight: 700; color: #b91c1c; margin-bottom: 4px;">🚨 ${h.area_name} Hotspot (${h.hotspot_id})</div>
            <p style="color: #334155; margin-bottom: 6px;">${h.insight_summary}</p>
            <div style="font-size: 11px; color: #64748b; border-top: 1px solid #f1f5f9; padding-top: 4px;">
              <strong>${h.total_reports} reports</strong> • ${h.dominant_category} • Avg Priority: ${h.average_priority_score}
            </div>
          </div>
        `);

        circle.addTo(hotspotsLayerRef.current!);
      });
    }
  }, [hotspots, showHotspots]);

  return (
    <div className={`relative rounded-xl overflow-hidden shadow-inner border border-slate-200 ${className}`} style={{ height }}>
      <div ref={mapContainerRef} className="w-full h-full" />
    </div>
  );
};
