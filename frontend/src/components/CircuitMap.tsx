"use client";

import { useEffect, useRef, useState } from "react";
import { Circuit, CircuitCorner, WindForecastPoint } from "@/types";

interface Props {
  circuit: Circuit;
  corners: CircuitCorner[];
  windForecast: WindForecastPoint[];
  selectedHourIndex: number;
}

function decomposeWind(
  windSpeedKmh: number,
  windDirectionDeg: number,
  cornerBearingDeg: number
): { headwind: number; crosswind: number; crossDir: "left" | "right" } {
  const windToDeg = (windDirectionDeg + 180) % 360;
  const relAngleRad = ((windToDeg - cornerBearingDeg) * Math.PI) / 180;
  const headwind = -windSpeedKmh * Math.cos(relAngleRad);
  const crosswind = windSpeedKmh * Math.sin(relAngleRad);
  return {
    headwind: Math.round(headwind * 10) / 10,
    crosswind: Math.round(Math.abs(crosswind) * 10) / 10,
    crossDir: crosswind > 0 ? "left" : "right",
  };
}

function headwindColor(headwind: number): string {
  if (headwind > 5) return "#c96060";
  if (headwind < -5) return "#4aad7c";
  return "#d9af42";
}

function precipColor(intensity: number): string {
  if (intensity >= 7.5) return "#bf5858";    // heavy — red
  if (intensity >= 2.5) return "#d9af42";    // moderate — yellow
  if (intensity >= 0.5) return "#5a9dba";    // light — blue
  if (intensity >= 0.05) return "#5aacb8";   // drizzle — cyan
  return "transparent";
}

function precipLabel(intensity: number): string {
  if (intensity >= 7.5) return "HEAVY";
  if (intensity >= 2.5) return "MODERATE";
  if (intensity >= 0.5) return "LIGHT";
  if (intensity >= 0.05) return "DRIZZLE";
  return "DRY";
}

function conditionColor(condition: string): string {
  switch (condition) {
    case "flooded": return "#bf5858";
    case "very_wet": return "#d9af42";
    case "wet": return "#5a9dba";
    case "damp": return "#5aacb8";
    default: return "#4aad7c";
  }
}

function createArrowHtml(
  windDirDeg: number,
  headwind: number,
  crosswind: number,
  speed: number,
  cornerName: string,
  crossDir: "left" | "right"
): string {
  const color = headwindColor(headwind);
  const arrowSize = Math.min(38, Math.max(20, 16 + speed * 0.4));
  const label =
    headwind > 5
      ? "HEAD"
      : headwind < -5
        ? "TAIL"
        : crosswind > speed * 0.5
          ? "CROSS"
          : "LIGHT";
  const absHeadwind = Math.abs(Math.round(headwind));

  return `
    <div style="display:flex;flex-direction:column;align-items:center;pointer-events:auto;cursor:default;font-family:Inter,system-ui,sans-serif;" title="${cornerName}: ${label} ${absHeadwind} km/h, Cross: ${Math.round(crosswind)} km/h ${crossDir}">
      <svg width="${arrowSize}" height="${arrowSize}" viewBox="0 0 40 40" style="filter:drop-shadow(0 1px 4px rgba(0,0,0,0.7));">
        <g transform="rotate(${windDirDeg}, 20, 20)">
          <line x1="20" y1="32" x2="20" y2="10" stroke="${color}" stroke-width="2.5" stroke-linecap="round" />
          <polygon points="20,5 14,15 26,15" fill="${color}" />
        </g>
        <circle cx="20" cy="20" r="2.5" fill="${color}" opacity="0.5" />
      </svg>
      <div style="
        background:rgba(11,10,14,0.88);
        color:${color};
        font-size:8px;
        font-weight:600;
        padding:1px 4px;
        border-radius:3px;
        white-space:nowrap;
        margin-top:-2px;
        letter-spacing:0.6px;
        border:1px solid ${color}30;
      ">${cornerName}</div>
      <div style="
        background:rgba(11,10,14,0.8);
        color:#ede9e0;
        font-size:7px;
        font-weight:500;
        padding:0px 3px;
        border-radius:2px;
        white-space:nowrap;
        margin-top:1px;
        letter-spacing:0.3px;
      ">${label} ${absHeadwind}</div>
    </div>
  `;
}

export default function CircuitMap({
  circuit,
  corners,
  windForecast,
  selectedHourIndex,
}: Props) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const markersLayerRef = useRef<any>(null);
  const precipLayerRef = useRef<any>(null);
  const leafletRef = useRef<any>(null);
  const [mapReady, setMapReady] = useState(0);

  useEffect(() => {
    let cancelled = false;

    const initMap = async () => {
      const L = (await import("leaflet")).default;
      if (cancelled) return;
      leafletRef.current = L;

      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
        markersLayerRef.current = null;
        precipLayerRef.current = null;
      }

      if (!mapRef.current) return;

      const map = L.map(mapRef.current).setView(
        [circuit.latitude, circuit.longitude],
        14
      );

      L.tileLayer(
        "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        {
          attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
          maxZoom: 19,
        }
      ).addTo(map);

      // Center marker — warm amber
      L.circleMarker([circuit.latitude, circuit.longitude], {
        radius: 7,
        fillColor: "#d4a04a",
        color: "#e0b65c",
        weight: 2,
        opacity: 0.9,
        fillOpacity: 0.7,
      })
        .addTo(map)
        .bindPopup(`<strong>${circuit.name}</strong><br/>${circuit.country}`);

      // Coverage radius
      L.circle([circuit.latitude, circuit.longitude], {
        radius: 50000,
        fillColor: "#d4a04a",
        fillOpacity: 0.02,
        color: "#d4a04a",
        weight: 1,
        opacity: 0.1,
        dashArray: "4,8",
      }).addTo(map);

      precipLayerRef.current = L.layerGroup().addTo(map);
      markersLayerRef.current = L.layerGroup().addTo(map);
      mapInstanceRef.current = map;
      setMapReady((n) => n + 1);
    };

    initMap();

    return () => {
      cancelled = true;
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
        markersLayerRef.current = null;
        precipLayerRef.current = null;
      }
    };
  }, [circuit]);

  // Update wind markers + precipitation overlay when time changes
  useEffect(() => {
    const L = leafletRef.current;
    const map = mapInstanceRef.current;
    const markersLayer = markersLayerRef.current;
    const precipLayer = precipLayerRef.current;
    if (!L || !map || !markersLayer || !precipLayer) return;

    if (corners.length > 1) {
      const bounds = L.latLngBounds(
        corners.map((c: CircuitCorner) => [c.lat, c.lng] as [number, number])
      );
      bounds.extend([circuit.latitude, circuit.longitude]);
      map.fitBounds(bounds.pad(0.5));
    }

    markersLayer.clearLayers();
    precipLayer.clearLayers();

    if (!windForecast.length || !corners.length) return;

    const idx = Math.min(selectedHourIndex, windForecast.length - 1);
    const forecast = windForecast[idx];
    if (!forecast) return;

    const windSpeed = forecast.speed_kmh;
    const windDir = forecast.direction_deg;
    const intensity = forecast.precipitation_intensity ?? 0;

    // Cloud cover layer — organic cloud shapes across the map
    const cloudCover = forecast.cloud_cover_pct ?? 0;
    const cosLat = Math.cos(circuit.latitude * Math.PI / 180);
    const directionDeg = windDir;

    if (cloudCover > 30) {
      const cloudOpacity = 0.03 + (cloudCover / 100) * 0.12;
      const cloudCount = 6;
      for (let i = 0; i < cloudCount; i++) {
        // Deterministic "random" offsets based on index
        const offsetX = Math.sin(i * 2.4) * 3000;
        const offsetY = Math.cos(i * 3.1) * 3000;
        const radius = 2000 + Math.abs(Math.sin(i * 1.7)) * 3000;
        const cloudLat = circuit.latitude + offsetY / 111320;
        const cloudLng = circuit.longitude + offsetX / (111320 * cosLat);

        L.circle([cloudLat, cloudLng], {
          radius,
          fillColor: "#94a3b8",
          fillOpacity: cloudOpacity,
          color: "#94a3b8",
          weight: 0,
          opacity: 0,
        }).addTo(precipLayer);
      }
    }

    // Rain overlay — organic rain cell with multiple overlapping circles
    if (intensity > 0) {
      const rainColor =
        intensity > 5 ? "#a855f7" :
        intensity > 2 ? "#6366f1" :
        intensity > 0.5 ? "#3b82f6" :
        "#22d3ee";
      const rainOpacity = 0.12 + Math.min(intensity / 8, 0.28);
      const rainRadius = 3000 + Math.min(intensity * 1500, 7000);
      const rainCircleCount = 4;

      for (let i = 0; i < rainCircleCount; i++) {
        const offsetX = Math.sin(i * 2.4) * 2000;
        const offsetY = Math.cos(i * 3.1) * 2000;
        const thisRadius = rainRadius * (0.7 + Math.abs(Math.sin(i * 1.9)) * 0.3);
        const rainLat = circuit.latitude + offsetY / 111320;
        const rainLng = circuit.longitude + offsetX / (111320 * cosLat);

        L.circle([rainLat, rainLng], {
          radius: thisRadius,
          fillColor: rainColor,
          fillOpacity: rainOpacity * (0.7 + Math.abs(Math.cos(i * 2.7)) * 0.3),
          color: rainColor,
          weight: 0,
          opacity: 0,
        }).addTo(precipLayer);
      }

      // Rain movement streaks — 12 polylines spread across the rain cell
      const streakCount = 12;
      const windToRad = ((directionDeg + 180) % 360) * Math.PI / 180;
      for (let i = 0; i < streakCount; i++) {
        // Deterministic spread across the rain cell area
        const spreadX = Math.sin(i * 2.4 + 0.5) * rainRadius * 0.8;
        const spreadY = Math.cos(i * 3.1 + 0.5) * rainRadius * 0.8;
        const streakLen = 800 + Math.abs(Math.sin(i * 1.7)) * 1200;
        const streakWeight = 2 + Math.abs(Math.cos(i * 2.3));
        const streakOpacity = 0.3 + Math.abs(Math.sin(i * 1.4)) * 0.3;

        const startLat = circuit.latitude + spreadY / 111320;
        const startLng = circuit.longitude + spreadX / (111320 * cosLat);
        const endLat = startLat + (Math.cos(windToRad) * streakLen) / 111320;
        const endLng = startLng + (Math.sin(windToRad) * streakLen) / (111320 * cosLat);

        L.polyline([[startLat, startLng], [endLat, endLng]], {
          color: rainColor,
          weight: streakWeight,
          opacity: streakOpacity,
          dashArray: "6,4",
        }).addTo(precipLayer);
      }

      // Rain cell boundary — dashed circle outline
      if (intensity > 0.3) {
        L.circle([circuit.latitude, circuit.longitude], {
          radius: rainRadius,
          fillColor: "transparent",
          fillOpacity: 0,
          color: rainColor,
          weight: 1.5,
          opacity: 0.25,
          dashArray: "8, 6",
        }).addTo(precipLayer);
      }
    }

    // Cloud/wind movement arrow — large arrow showing wind direction across the map
    if (windSpeed > 1) {
      const arrowLen = Math.min(0.06, 0.02 + windSpeed * 0.001); // degrees offset
      const windToRad = ((windDir + 180) % 360) * Math.PI / 180;
      // Arrow starts upwind of circuit, ends downwind
      const startLat = circuit.latitude - Math.cos(windToRad) * arrowLen;
      const startLng = circuit.longitude - (Math.sin(windToRad) * arrowLen) / cosLat;
      const endLat = circuit.latitude + Math.cos(windToRad) * arrowLen;
      const endLng = circuit.longitude + (Math.sin(windToRad) * arrowLen) / cosLat;

      // Arrow color based on speed
      const arrowColor = windSpeed > 40 ? "#c96060" : windSpeed > 20 ? "#d9af42" : "#6a8a9a";
      const arrowOpacity = Math.min(0.6, 0.2 + windSpeed * 0.01);

      L.polyline([[startLat, startLng], [endLat, endLng]], {
        color: arrowColor,
        weight: 2,
        opacity: arrowOpacity,
        dashArray: "8,4",
      }).addTo(precipLayer);

      // Arrowhead at end
      const headSize = arrowLen * 0.35;
      const headAngle1 = windToRad + 2.6; // ~150 degrees
      const headAngle2 = windToRad - 2.6;
      const head1Lat = endLat + Math.cos(headAngle1) * headSize;
      const head1Lng = endLng + (Math.sin(headAngle1) * headSize) / cosLat;
      const head2Lat = endLat + Math.cos(headAngle2) * headSize;
      const head2Lng = endLng + (Math.sin(headAngle2) * headSize) / cosLat;

      L.polyline([[head1Lat, head1Lng], [endLat, endLng], [head2Lat, head2Lng]], {
        color: arrowColor,
        weight: 2,
        opacity: arrowOpacity,
      }).addTo(precipLayer);

      // Wind speed label at midpoint
      const midLat = (startLat + endLat) / 2;
      const midLng = (startLng + endLng) / 2;
      // Offset label perpendicular to wind direction
      const perpLat = midLat + Math.cos(windToRad + Math.PI / 2) * arrowLen * 0.3;
      const perpLng = midLng + (Math.sin(windToRad + Math.PI / 2) * arrowLen * 0.3) / cosLat;

      const windLabel = L.divIcon({
        html: `<div style="
          font-family:Inter,system-ui,sans-serif;
          font-size:9px;
          font-weight:600;
          color:${arrowColor};
          background:rgba(11,10,14,0.85);
          padding:1px 5px;
          border-radius:3px;
          white-space:nowrap;
          border:1px solid ${arrowColor}30;
          letter-spacing:0.5px;
        ">${Math.round(windSpeed)} km/h ${forecast.direction_label}</div>`,
        className: "wind-direction-label",
        iconSize: [80, 20],
        iconAnchor: [40, 10],
      });
      L.marker([perpLat, perpLng], { icon: windLabel, interactive: false }).addTo(precipLayer);
    }

    // Wind corner markers
    corners.forEach((corner) => {
      const { headwind, crosswind, crossDir } = decomposeWind(
        windSpeed,
        windDir,
        corner.bearing
      );

      const html = createArrowHtml(
        windDir,
        headwind,
        crosswind,
        windSpeed,
        corner.name,
        crossDir
      );

      const icon = L.divIcon({
        html,
        className: "wind-corner-marker",
        iconSize: [60, 60],
        iconAnchor: [30, 30],
      });

      L.marker([corner.lat, corner.lng], { icon, interactive: true })
        .addTo(markersLayer)
        .bindPopup(
          `<div style="font-family:Inter,system-ui,sans-serif;font-size:12px;line-height:1.5;color:#ede9e0">
            <strong style="color:#e0b65c">${corner.name}</strong><br/>
            <span style="color:${headwindColor(headwind)}">
              ${headwind > 0 ? "Headwind" : "Tailwind"}: ${Math.abs(Math.round(headwind))} km/h
            </span><br/>
            Crosswind: ${Math.round(crosswind)} km/h (${crossDir})<br/>
            <span style="color:#9a9490">Wind: ${windSpeed} km/h from ${forecast.direction_label}</span><br/>
            <span style="color:#9a9490">Bearing: ${corner.bearing}°</span>
          </div>`
        );
    });
  }, [mapReady, corners, windForecast, selectedHourIndex, circuit.latitude, circuit.longitude]);

  // Get current forecast for precipitation badge
  const currentForecast = windForecast[Math.min(selectedHourIndex, windForecast.length - 1)];
  const intensity = currentForecast?.precipitation_intensity ?? 0;
  const probability = currentForecast?.precipitation_probability ?? 0;
  const condition = currentForecast?.track_condition ?? "dry";

  return (
    <div
      className="overflow-hidden"
      style={{
        borderRadius: '10px',
        border: '1px solid var(--border-color)',
        boxShadow: 'var(--shadow-card)',
      }}
    >
      <div
        className="flex items-center justify-between px-3.5 py-2"
        style={{ background: 'var(--bg-card)' }}
      >
        <h3 className="section-heading">Wind Map</h3>
        <div className="flex items-center gap-3">
          {/* Precipitation badge */}
          {intensity >= 0.05 && (
            <div
              className="flex items-center gap-1.5 px-2 py-0.5 rounded text-[8px] font-semibold tracking-wider"
              style={{
                background: `color-mix(in srgb, ${precipColor(intensity)} 15%, transparent)`,
                color: precipColor(intensity),
                border: `1px solid color-mix(in srgb, ${precipColor(intensity)} 25%, transparent)`,
              }}
            >
              <span className="w-[5px] h-[5px] rounded-full" style={{ backgroundColor: precipColor(intensity) }} />
              {precipLabel(intensity)} {intensity.toFixed(1)} mm/hr
              {probability > 0 && (
                <span className="opacity-70 ml-0.5">{probability}%</span>
              )}
            </div>
          )}
          {/* Track condition badge */}
          {condition !== "dry" && intensity < 0.05 && (
            <div
              className="flex items-center gap-1 px-2 py-0.5 rounded text-[8px] font-semibold tracking-wider uppercase"
              style={{
                background: `color-mix(in srgb, ${conditionColor(condition)} 15%, transparent)`,
                color: conditionColor(condition),
                border: `1px solid color-mix(in srgb, ${conditionColor(condition)} 25%, transparent)`,
              }}
            >
              <span className="w-[5px] h-[5px] rounded-full" style={{ backgroundColor: conditionColor(condition) }} />
              {condition.replace("_", " ")}
            </div>
          )}
          <div className="flex items-center gap-2 text-[8px] text-[var(--text-muted)]">
            <span className="flex items-center gap-1">
              <span className="w-[6px] h-[6px] rounded-full" style={{ backgroundColor: "#c96060" }} />
              Head
            </span>
            <span className="flex items-center gap-1">
              <span className="w-[6px] h-[6px] rounded-full" style={{ backgroundColor: "#4aad7c" }} />
              Tail
            </span>
            <span className="flex items-center gap-1">
              <span className="w-[6px] h-[6px] rounded-full" style={{ backgroundColor: "#d9af42" }} />
              Cross
            </span>
          </div>
          <span className="text-[9px] text-[var(--text-muted)] font-mono">
            {corners.length > 1 ? `${corners.length} pts` : "50km"}
          </span>
        </div>
      </div>
      <div ref={mapRef} style={{ height: "380px", width: "100%" }} />
    </div>
  );
}
