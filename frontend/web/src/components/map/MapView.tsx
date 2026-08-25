import { useRef, useCallback } from 'react';
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
    features: stops.map(stop => ({
      type: 'Feature' as const,
      geometry: { type: 'Point' as const, coordinates: [stop.longitude, stop.latitude] },
      properties: { id: stop.id, type: stop.type, selected: state.selectedStop?.id === stop.id },
    })),
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

      {/* Route polylines */}
      {routes.map(route => (
        <Source key={route.id} id={route.id} type="geojson" data={{
          type: 'Feature',
          geometry: { type: 'LineString', coordinates: route.polyline },
          properties: {},
        }}>
          <Layer
            id={`${route.id}-line`}
            type="line"
            paint={{
              'line-color': route.color,
              'line-width': 3,
              'line-opacity': 0.6,
            }}
            layout={{ 'line-cap': 'round', 'line-join': 'round' }}
          />
        </Source>
      ))}

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
