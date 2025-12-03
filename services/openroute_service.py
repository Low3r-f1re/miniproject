"""
OpenRouteService Integration - Provides geocoding, directions, isochrones, and routing
Documentation: https://openrouteservice.org/dev/#/api-docs
"""

import os
import requests
import logging
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)


class OpenRouteService:
    """Service for integrating with OpenRouteService API"""
    
    BASE_URL = "https://api.openrouteservice.org"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenRouteService with API key"""
        self.api_key = api_key or os.environ.get('OPENROUTE_API_KEY')
        if not self.api_key:
            logger.warning("OpenRouteService API key not configured")
        
        self.headers = {
            'Authorization': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def geocode(self, location: str, limit: int = 1) -> Optional[Dict[str, Any]]:
        """
        Geocode a location string to coordinates
        
        Args:
            location: Address or place name to geocode
            limit: Maximum number of results to return
            
        Returns:
            Dictionary with geocoding results including coordinates
        """
        if not self.api_key:
            logger.error("OpenRouteService API key not configured")
            return None
        
        try:
            url = f"{self.BASE_URL}/geocode/search"
            params = {
                'text': location,
                'size': limit
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('features'):
                logger.warning(f"No geocoding results found for: {location}")
                return None
            
            # Return the first (best) result
            feature = data['features'][0]
            coordinates = feature['geometry']['coordinates']  # [lon, lat]
            properties = feature.get('properties', {})
            
            result = {
                'latitude': coordinates[1],
                'longitude': coordinates[0],
                'label': properties.get('label', location),
                'name': properties.get('name', ''),
                'country': properties.get('country', ''),
                'region': properties.get('region', ''),
                'locality': properties.get('locality', ''),
                'confidence': properties.get('confidence', 0),
                'all_results': data['features']  # Include all results for reference
            }
            
            logger.info(f"Geocoded '{location}' to ({result['latitude']}, {result['longitude']})")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error geocoding location '{location}': {e}")
            return None
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"Error parsing geocoding response: {e}")
            return None
    
    def reverse_geocode(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """
        Reverse geocode coordinates to address
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Dictionary with address information
        """
        if not self.api_key:
            logger.error("OpenRouteService API key not configured")
            return None
        
        try:
            url = f"{self.BASE_URL}/geocode/reverse"
            params = {
                'point.lon': longitude,
                'point.lat': latitude,
                'size': 1
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('features'):
                logger.warning(f"No reverse geocoding results found for: ({latitude}, {longitude})")
                return None
            
            feature = data['features'][0]
            properties = feature.get('properties', {})
            
            result = {
                'label': properties.get('label', ''),
                'name': properties.get('name', ''),
                'street': properties.get('street', ''),
                'locality': properties.get('locality', ''),
                'region': properties.get('region', ''),
                'country': properties.get('country', ''),
                'postal_code': properties.get('postalcode', ''),
                'confidence': properties.get('confidence', 0)
            }
            
            logger.info(f"Reverse geocoded ({latitude}, {longitude}) to '{result['label']}'")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error reverse geocoding coordinates ({latitude}, {longitude}): {e}")
            return None
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"Error parsing reverse geocoding response: {e}")
            return None
    
    def get_directions(
        self,
        start_coords: Tuple[float, float],
        end_coords: Tuple[float, float],
        profile: str = 'driving-car',
        alternatives: int = 0,
        format: str = 'json',
        units: str = 'km',
        language: str = 'en'
    ) -> Optional[Dict[str, Any]]:
        """
        Get directions between two points
        
        Args:
            start_coords: (latitude, longitude) of start point
            end_coords: (latitude, longitude) of end point
            profile: Transport mode - 'driving-car', 'driving-hgv', 'cycling-regular', 
                     'cycling-road', 'cycling-mountain', 'cycling-electric', 
                     'foot-walking', 'foot-hiking', 'wheelchair'
            alternatives: Number of alternative routes (0-3)
            format: Response format ('json', 'geojson')
            units: Distance units ('m', 'km', 'mi')
            language: Language for instructions
            
        Returns:
            Dictionary with route information including distance, duration, and steps
        """
        if not self.api_key:
            logger.error("OpenRouteService API key not configured")
            return None
        
        try:
            url = f"{self.BASE_URL}/v2/directions/{profile}"
            
            # OpenRouteService expects coordinates as [lon, lat]
            coordinates = [
                [start_coords[1], start_coords[0]],
                [end_coords[1], end_coords[0]]
            ]
            
            # OpenRouteService v2 directions uses JSON body
            payload = {
                'coordinates': coordinates,
                'instructions': True,
                'language': language
            }
            
            # Only add alternative_routes if alternatives > 0
            if alternatives > 0:
                payload['alternative_routes'] = {
                    'target_count': alternatives
                }
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('routes'):
                logger.warning(f"No routes found from {start_coords} to {end_coords}")
                return None
            
            # Process the main route
            route = data['routes'][0]
            summary = route.get('summary', {})
            
            result = {
                'distance_km': summary.get('distance', 0) / 1000 if units == 'm' else summary.get('distance', 0),
                'duration_seconds': summary.get('duration', 0),
                'duration_minutes': round(summary.get('duration', 0) / 60, 1),
                'duration_hours': round(summary.get('duration', 0) / 3600, 2),
                'profile': profile,
                'geometry': route.get('geometry', None),
                'steps': self._process_route_steps(route.get('segments', [])),
                'bbox': route.get('bbox', None),
                'ascent': summary.get('ascent', 0),
                'descent': summary.get('descent', 0),
                'raw_route': route  # Include full route data
            }
            
            # Add alternative routes if available
            if len(data['routes']) > 1:
                result['alternatives'] = []
                for alt_route in data['routes'][1:]:
                    alt_summary = alt_route.get('summary', {})
                    result['alternatives'].append({
                        'distance_km': alt_summary.get('distance', 0) / 1000 if units == 'm' else alt_summary.get('distance', 0),
                        'duration_minutes': round(alt_summary.get('duration', 0) / 60, 1),
                        'geometry': alt_route.get('geometry', None)
                    })
            
            logger.info(f"Got directions from {start_coords} to {end_coords}: "
                       f"{result['distance_km']:.1f} km, {result['duration_minutes']:.1f} min")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting directions: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing directions response: {e}")
            return None
    
    def _process_route_steps(self, segments: List[Dict]) -> List[Dict]:
        """Process route segments into readable turn-by-turn instructions"""
        steps = []
        
        for segment in segments:
            for step in segment.get('steps', []):
                steps.append({
                    'instruction': step.get('instruction', ''),
                    'distance_km': step.get('distance', 0) / 1000,
                    'duration_seconds': step.get('duration', 0),
                    'type': step.get('type', ''),
                    'name': step.get('name', ''),
                    'way_points': step.get('way_points', [])
                })
        
        return steps
    
    def get_isochrones(
        self,
        coordinates: Tuple[float, float],
        profile: str = 'driving-car',
        range_type: str = 'time',
        ranges: List[int] = [300, 600, 900],  # seconds or meters
        units: str = 'km',
        location_type: str = 'start'
    ) -> Optional[Dict[str, Any]]:
        """
        Get isochrones (reachability areas) from a point
        
        Args:
            coordinates: (latitude, longitude) of center point
            profile: Transport mode (same as directions)
            range_type: 'time' (seconds) or 'distance' (meters)
            ranges: List of range values (e.g., [300, 600, 900] for 5, 10, 15 minutes)
            units: Distance units for display
            location_type: 'start' or 'destination'
            
        Returns:
            Dictionary with isochrone polygons and metadata
        """
        if not self.api_key:
            logger.error("OpenRouteService API key not configured")
            return None
        
        try:
            url = f"{self.BASE_URL}/v2/isochrones/{profile}"
            
            payload = {
                'locations': [[coordinates[1], coordinates[0]]],  # [lon, lat]
                'range': ranges
            }
            
            # Add range_type if specified
            if range_type:
                payload['range_type'] = range_type
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('features'):
                logger.warning(f"No isochrones generated for {coordinates}")
                return None
            
            result = {
                'center': coordinates,
                'profile': profile,
                'range_type': range_type,
                'polygons': [],
                'raw_data': data
            }
            
            for feature in data['features']:
                properties = feature.get('properties', {})
                result['polygons'].append({
                    'value': properties.get('value', 0),
                    'center': properties.get('center', coordinates),
                    'geometry': feature.get('geometry', None),
                    'area_km2': properties.get('area', 0) / 1_000_000 if units == 'm' else properties.get('area', 0)
                })
            
            logger.info(f"Generated {len(result['polygons'])} isochrones for {coordinates}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting isochrones: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing isochrones response: {e}")
            return None
    
    def get_matrix(
        self,
        locations: List[Tuple[float, float]],
        profile: str = 'driving-car',
        sources: Optional[List[int]] = None,
        destinations: Optional[List[int]] = None,
        metrics: List[str] = ['distance', 'duration'],
        units: str = 'km'
    ) -> Optional[Dict[str, Any]]:
        """
        Get distance/duration matrix between multiple locations
        
        Args:
            locations: List of (latitude, longitude) tuples
            profile: Transport mode
            sources: Indices of source locations (default: all)
            destinations: Indices of destination locations (default: all)
            metrics: List of metrics to calculate ('distance', 'duration')
            units: Distance units
            
        Returns:
            Dictionary with distance and duration matrices
        """
        if not self.api_key:
            logger.error("OpenRouteService API key not configured")
            return None
        
        try:
            url = f"{self.BASE_URL}/v2/matrix/{profile}"
            
            # Convert to [lon, lat] format
            coordinates = [[loc[1], loc[0]] for loc in locations]
            
            payload = {
                'locations': coordinates,
                'metrics': metrics,
                'units': units
            }
            
            if sources is not None:
                payload['sources'] = sources
            if destinations is not None:
                payload['destinations'] = destinations
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            result = {
                'profile': profile,
                'locations': locations,
                'sources': sources or list(range(len(locations))),
                'destinations': destinations or list(range(len(locations))),
                'distances': data.get('distances', []),
                'durations': data.get('durations', []),
                'raw_data': data
            }
            
            # Convert distances to km if in meters
            if units == 'm' and result['distances']:
                result['distances_km'] = [[d/1000 if d else None for d in row] for row in result['distances']]
            
            # Convert durations to minutes
            if result['durations']:
                result['durations_minutes'] = [[d/60 if d else None for d in row] for row in result['durations']]
            
            logger.info(f"Generated matrix for {len(locations)} locations")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting matrix: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing matrix response: {e}")
            return None
    
    def optimize_route(
        self,
        locations: List[Tuple[float, float]],
        profile: str = 'driving-car',
        jobs: Optional[List[Dict]] = None,
        vehicles: Optional[List[Dict]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Optimize route for multiple waypoints using Vehicle Routing Problem (VRP) solver
        
        Args:
            locations: List of (latitude, longitude) tuples for waypoints
            profile: Transport mode
            jobs: Optional list of job specifications
            vehicles: Optional list of vehicle specifications
            
        Returns:
            Dictionary with optimized route
        """
        if not self.api_key:
            logger.error("OpenRouteService API key not configured")
            return None
        
        try:
            url = f"{self.BASE_URL}/optimization"
            
            # Convert to [lon, lat] format
            coordinates = [[loc[1], loc[0]] for loc in locations]
            
            # Create default jobs if not provided
            if jobs is None:
                jobs = [
                    {
                        'id': i,
                        'location': coord
                    }
                    for i, coord in enumerate(coordinates)
                ]
            
            # Create default vehicle if not provided
            if vehicles is None:
                vehicles = [{
                    'id': 1,
                    'profile': profile,
                    'start': coordinates[0],
                    'end': coordinates[0]
                }]
            
            payload = {
                'jobs': jobs,
                'vehicles': vehicles
            }
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=20)
            response.raise_for_status()
            
            data = response.json()
            
            logger.info(f"Optimized route for {len(locations)} locations")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error optimizing route: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing optimization response: {e}")
            return None
    
    def format_directions_summary(self, directions: Dict[str, Any]) -> str:
        """Format directions into a readable summary"""
        if not directions:
            return "No directions available"
        
        summary = f"""
Route Summary:
• Distance: {directions['distance_km']:.1f} km
• Duration: {directions['duration_hours']:.1f} hours ({directions['duration_minutes']:.0f} minutes)
• Transport Mode: {directions['profile'].replace('-', ' ').title()}
"""
        
        if directions.get('ascent') or directions.get('descent'):
            summary += f"• Elevation: ↑{directions.get('ascent', 0):.0f}m / ↓{directions.get('descent', 0):.0f}m\n"
        
        if directions.get('steps'):
            summary += f"\nTurn-by-Turn Directions ({len(directions['steps'])} steps):\n"
            for i, step in enumerate(directions['steps'][:10], 1):  # Show first 10 steps
                summary += f"{i}. {step['instruction']} ({step['distance_km']:.2f} km)\n"
            
            if len(directions['steps']) > 10:
                summary += f"... and {len(directions['steps']) - 10} more steps\n"
        
        if directions.get('alternatives'):
            summary += f"\nAlternative Routes Available: {len(directions['alternatives'])}\n"
            for i, alt in enumerate(directions['alternatives'], 1):
                summary += f"  Alt {i}: {alt['distance_km']:.1f} km, {alt['duration_minutes']:.0f} min\n"
        
        return summary
