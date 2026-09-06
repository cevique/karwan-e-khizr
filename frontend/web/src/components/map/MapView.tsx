import { useRef, useCallback, useEffect } from 'react';
import Map, { Source, Layer, NavigationControl } from 'react-map-gl/maplibre';
import type { MapRef, MapLayerMouseEvent } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import { DEFAULT_CENTER, DEFAULT_ZOOM, MAP_STYLE_LIGHT } from '@shared/index';
import { useApp } from '../../App';

interface MapViewProps {
  style?: React.CSSProperties;
  interactive?: boolean;
}

export function MapView({ style, interactive = true }: MapViewProps) {
  const mapRef = useRef<MapRef>(null);
  const { selectBus, selectStop, state, transit } = useApp();

  const { vehicles, stops, routes } = transit;
  const routeStops = state.routeStops;

  // Fly to selected bus position
  useEffect(() => {
    if (state.selectedBus && mapRef.current) {
      mapRef.current.flyTo({
        center: [state.selectedBus.longitude, state.selectedBus.latitude],
        zoom: 15,
        duration: 800,
      });
    }
  }, [state.selectedBus]);

  // Listen for custom flyTo events (e.g., from Locate Me button)
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail && mapRef.current) {
        mapRef.current.flyTo({
          center: [detail.lng, detail.lat],
          zoom: detail.zoom ?? 14,
          duration: 800,
        });
      }
    };
    window.addEventListener('map-flyto', handler);
    return () => window.removeEventListener('map-flyto', handler);
  }, []);

  const handleBusClick = useCallback((e: MapLayerMouseEvent) => {
    const feature = e.features?.[0];
    if (!feature?.properties) return;
    const bus = vehicles.find(b => b.id === feature.properties?.id);
    if (bus) selectBus(bus);
  }, [selectBus, vehicles]);

  const handleStopClick = useCallback((e: MapLayerMouseEvent) => {
    const feature = e.features?.[0];
    if (!feature?.properties) return;
    const stop = stops.find(s => s.id === feature.properties?.id);
    if (stop) selectStop(stop);
  }, [selectStop, stops]);

  const busFeatures = {
    type: 'FeatureCollection' as const,
    features: vehicles.map(bus => ({
      type: 'Feature' as const,
      geometry: { type: 'Point' as const, coordinates: [bus.longitude, bus.latitude] },
      properties: { id: bus.id, routeColor: bus.routeColor, status: bus.status },
    })),
  };

  const stopFeatures = {
    type: 'FeatureCollection' as const,
    features: stops
      .filter(stop => stop.latitude != null && stop.longitude != null)
      .map(stop => ({
        type: 'Feature' as const,
        geometry: { type: 'Point' as const, coordinates: [stop.longitude!, stop.latitude!] },
        properties: { id: stop.id, type: stop.type, selected: state.selectedStop?.id === stop.id },
      })),
  };

  // Route stops highlight layer
  const routeStopFeatures = {
    type: 'FeatureCollection' as const,
    features: (routeStops?.stops ?? [])
      .filter(s => s.lat != null && s.lon != null)
      .map((s, i) => ({
        type: 'Feature' as const,
        geometry: { type: 'Point' as const, coordinates: [s.lon!, s.lat!] },
        properties: { id: s.stopId, name: s.stopName, sequence: i + 1 },
      })),
  };

  // Route polyline from stop coordinates
  const routeLineFeatures = {
    type: 'FeatureCollection' as const,
    features: routeStops && routeStops.stops.length >= 2 ? [{
      type: 'Feature' as const,
      geometry: {
        type: 'LineString' as const,
        coordinates: routeStops.stops
          .filter(s => s.lat != null && s.lon != null)
          .map(s => [s.lon!, s.lat!]),
      },
      properties: {},
    }] : [],
  };

  return (
    <Map
      ref={mapRef}
      initialViewState={{
        longitude: DEFAULT_CENTER[0],
        latitude: DEFAULT_CENTER[1],
        zoom: DEFAULT_ZOOM,
      }}
      style={{ width: '100%', height: '100%', ...style }}
      mapStyle={MAP_STYLE_LIGHT}
      interactiveLayerIds={['bus-markers', 'stop-markers']}
      onClick={(e) => {
        const feature = e.features?.[0];
        if (!feature) {
          selectBus(null);
          selectStop(null);
          return;
        }
        if (feature.layer.id === 'bus-markers') handleBusClick(e);
        else if (feature.layer.id === 'stop-markers') handleStopClick(e);
      }}
    >
      {interactive && <NavigationControl position="bottom-right" showCompass={false} />}

      {/* Selected route polyline */}
      {routeStops && (
        <Source id="route-line" type="geojson" data={routeLineFeatures}>
          <Layer
            id="route-line-layer"
            type="line"
            paint={{
              'line-color': routeStops.color ?? '#1B8A4A',
              'line-width': 4,
              'line-opacity': 0.8,
            }}
            layout={{ 'line-cap': 'round', 'line-join': 'round' }}
          />
        </Source>
      )}

      {/* Selected route stop markers */}
      {routeStops && (
        <Source id="route-stops" type="geojson" data={routeStopFeatures}>
          <Layer
            id="route-stop-markers"
            type="circle"
            paint={{
              'circle-radius': 10,
              'circle-color': routeStops.color ?? '#1B8A4A',
              'circle-stroke-width': 3,
              'circle-stroke-color': '#FFFFFF',
            }}
          />
          <Layer
            id="route-stop-labels"
            type="symbol"
            layout={{
              'text-field': ['get', 'sequence'],
              'text-size': 10,
              'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
            }}
            paint={{
              'text-color': '#FFFFFF',
            }}
          />
        </Source>
      )}

      {/* Stop markers */}
      <Source id="stops" type="geojson" data={stopFeatures}>
        <Layer
          id="stop-markers"
          type="circle"
          paint={{
            'circle-radius': 6,
            'circle-color': ['case',
              ['==', ['get', 'selected'], true], '#1B8A4A',
              '#1B3A5C',
            ],
            'circle-stroke-width': 2,
            'circle-stroke-color': '#FFFFFF',
          }}
        />
      </Source>

      {/* Bus markers */}
      <Source id="buses" type="geojson" data={busFeatures}>
        <Layer
          id="bus-markers"
          type="circle"
          paint={{
            'circle-radius': 8,
            'circle-color': ['get', 'routeColor'],
            'circle-stroke-width': 3,
            'circle-stroke-color': '#FFFFFF',
          }}
        />
        <Layer
          id="bus-markers-inner"
          type="circle"
          paint={{
            'circle-radius': 3,
            'circle-color': '#FFFFFF',
          }}
        />
      </Source>
    </Map>
  );
}
