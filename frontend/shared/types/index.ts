// ── Karwan-e-Khizr: Shared Transit Types ──

export interface Location {
  latitude: number;
  longitude: number;
}

export interface Bus {
  id: string;
  routeId: string;
  routeName: string;
  routeColor: string;
  latitude: number;
  longitude: number;
  heading: number;
  speed: number; // km/h
  status: 'active' | 'delayed' | 'inactive';
  nextStopId: string;
  nextStopName: string;
  eta: number; // minutes
  vehicleNumber: string;
}

export interface Stop {
  id: string;
  name: string;
  nameUrdu?: string;
  latitude: number;
  longitude: number;
  routeIds: string[];
  type: 'bus-stop' | 'metro-station' | 'terminal';
}

export interface TransitRoute {
  id: string;
  name: string;
  shortName: string;
  color: string;
  type: 'bus' | 'metro';
  stops: string[]; // stop IDs in order
  polyline: [number, number][]; // [lng, lat] pairs
  frequency: string; // e.g., "Every 6-8 min"
  operatingHours: string; // e.g., "6:00 AM – 10:00 PM"
}

export type JourneySegmentType = 'walk' | 'bus' | 'metro' | 'transfer';

export interface WalkSegment {
  type: 'walk';
  duration: number; // minutes
  distance: number; // meters
  from: { name: string; latitude: number; longitude: number };
  to: { name: string; latitude: number; longitude: number };
}

export interface TransitSegment {
  type: 'bus' | 'metro';
  routeId: string;
  routeName: string;
  routeShortName: string;
  routeColor: string;
  fromStop: { id: string; name: string; latitude: number; longitude: number };
  toStop: { id: string; name: string; latitude: number; longitude: number };
  duration: number; // minutes
  stops: number; // number of stops
  direction: string;
}

export interface TransferSegment {
  type: 'transfer';
  duration: number; // minutes
  fromStopName: string;
  toStopName: string;
}

export type JourneySegment = WalkSegment | TransitSegment | TransferSegment;

export interface Journey {
  id: string;
  segments: JourneySegment[];
  totalDuration: number; // minutes
  totalWalkDistance: number; // meters
  fare: number; // PKR
  fareLabel: string;
  tag?: 'fastest' | 'fewest-transfers' | 'least-walking' | 'recommended';
}

export interface SearchResult {
  id: string;
  name: string;
  nameUrdu?: string;
  type: 'place' | 'stop' | 'station';
  latitude: number;
  longitude: number;
  subtitle?: string;
}
