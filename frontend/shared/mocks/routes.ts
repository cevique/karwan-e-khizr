// ── Karwan-e-Khizr: Mock Transit Routes ──
// Demo data only — polylines are simplified approximations for visualization.

import type { TransitRoute } from '../types';

export const mockRoutes: TransitRoute[] = [
  {
    id: 'route-green',
    name: 'Green Line',
    shortName: 'RL-02',
    color: '#1B8A4A',
    type: 'bus',
    stops: [
      'stop-saddar',
      'stop-6th-road',
      'stop-committee-chowk',
      'stop-ibn-e-sina',
      'stop-ammaar-chowk',
      'stop-afaq-shaheed',
      'stop-g9-markaz',
      'stop-blue-area',
      'stop-f8',
    ],
    polyline: [
      [73.0506, 33.5936],
      [73.0575, 33.6080],
      [73.0540, 33.6165],
      [73.0530, 33.6406],
      [73.0580, 33.6241],
      [73.0632, 33.6549],
      [73.0215, 33.6710],
      [73.0468, 33.6978],
      [73.0484, 33.7013],
    ],
    frequency: 'Every 6–8 min',
    operatingHours: '6:00 AM – 10:00 PM',
  },
  {
    id: 'route-blue',
    name: 'Blue Line',
    shortName: 'BL-01',
    color: '#1B3A5C',
    type: 'bus',
    stops: [
      'stop-rawalpindi-station',
      'stop-saddar',
      'stop-blue-area',
      'stop-kashmir-chowk',
      'stop-f10-markaz',
    ],
    polyline: [
      [73.0455, 33.5975],
      [73.0506, 33.5936],
      [73.0468, 33.6978],
      [73.0501, 33.6899],
      [73.0218, 33.7085],
    ],
    frequency: 'Every 10–12 min',
    operatingHours: '6:30 AM – 9:30 PM',
  },
  {
    id: 'route-orange',
    name: 'Orange Line',
    shortName: 'OL-03',
    color: '#D4880F',
    type: 'metro',
    stops: [
      'stop-rawalpindi-station',
      'stop-committee-chowk',
      'stop-6th-road',
      'stop-kashmir-chowk',
      'stop-g9-markaz',
    ],
    polyline: [
      [73.0455, 33.5975],
      [73.0540, 33.6165],
      [73.0575, 33.6080],
      [73.0501, 33.6899],
      [73.0215, 33.6710],
    ],
    frequency: 'Every 8–10 min',
    operatingHours: '7:00 AM – 9:00 PM',
  },
];
