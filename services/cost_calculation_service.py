"""
Cost Calculation Service - Provides realistic cost estimates for travel planning
Based on real-world data, cost of living indices, and distance-based calculations
"""

import logging
from typing import Dict, Optional, Tuple
from math import radians, sin, cos, sqrt, atan2

logger = logging.getLogger(__name__)

# Import OpenRouteService for accurate geocoding
try:
    from services.openroute_service import OpenRouteService
    OPENROUTE_AVAILABLE = True
except ImportError:
    OPENROUTE_AVAILABLE = False
    logger.warning("OpenRouteService not available, using fallback geocoding")

class CostCalculationService:
    """Service for calculating realistic travel costs based on destination and user preferences"""
    
    # City coordinates database for geocoding
    CITY_COORDINATES = {
        # India - Major cities
        'mumbai': (19.0760, 72.8777),
        'delhi': (28.7041, 77.1025),
        'bangalore': (12.9716, 77.5946),
        'bengaluru': (12.9716, 77.5946),
        'chennai': (13.0827, 80.2707),
        'kolkata': (22.5726, 88.3639),
        'hyderabad': (17.3850, 78.4867),
        'pune': (18.5204, 73.8567),
        'ahmedabad': (23.0225, 72.5714),
        'jaipur': (26.9124, 75.7873),
        'goa': (15.2993, 74.1240),
        'kerala': (10.8505, 76.2711),
        'marathahalli': (12.9591, 77.7011),
        'whitefield': (12.9698, 77.7500),
        'koramangala': (12.9352, 77.6245),
        
        # Asia
        'bangkok': (13.7563, 100.5018),
        'tokyo': (35.6762, 139.6503),
        'singapore': (1.3521, 103.8198),
        'hong kong': (22.3193, 114.1694),
        'seoul': (37.5665, 126.9780),
        'beijing': (39.9042, 116.4074),
        'shanghai': (31.2304, 121.4737),
        'kuala lumpur': (3.1390, 101.6869),
        'bali': (-8.3405, 115.0920),
        'dubai': (25.2048, 55.2708),
        
        # Europe
        'london': (51.5074, -0.1278),
        'paris': (48.8566, 2.3522),
        'rome': (41.9028, 12.4964),
        'barcelona': (41.3851, 2.1734),
        'amsterdam': (52.3676, 4.9041),
        'berlin': (52.5200, 13.4050),
        
        # Americas
        'new york': (40.7128, -74.0060),
        'los angeles': (34.0522, -118.2437),
        'san francisco': (37.7749, -122.4194),
        'miami': (25.7617, -80.1918),
        'toronto': (43.6532, -79.3832),
    }
    
    # Cost of living data (normalized to base index where Mumbai = 100)
    COST_OF_LIVING_INDEX = {
        # India
        'mumbai': 100, 'delhi': 95, 'bangalore': 98, 'bengaluru': 98,
        'chennai': 85, 'kolkata': 80, 'hyderabad': 90, 'pune': 92,
        'ahmedabad': 80, 'jaipur': 75, 'goa': 110, 'kerala': 85,
        
        # Asia
        'bangkok': 85, 'tokyo': 180, 'singapore': 165, 'hong kong': 170,
        'seoul': 150, 'beijing': 120, 'shanghai': 130, 'kuala lumpur': 75,
        'bali': 70, 'phuket': 80, 'hanoi': 65, 'ho chi minh': 70,
        'dubai': 140, 'istanbul': 90, 'manila': 70,
        
        # Europe
        'london': 190, 'paris': 180, 'rome': 160, 'barcelona': 155,
        'amsterdam': 175, 'berlin': 165, 'vienna': 160, 'prague': 120,
        'budapest': 100, 'madrid': 150, 'lisbon': 130, 'athens': 120,
        
        # Americas
        'new york': 200, 'los angeles': 185, 'san francisco': 195,
        'chicago': 170, 'miami': 165, 'toronto': 170, 'vancouver': 175,
        'mexico city': 85, 'cancun': 95, 'rio de janeiro': 90,
        'buenos aires': 80, 'lima': 75,
        
        # Oceania
        'sydney': 180, 'melbourne': 175, 'auckland': 170,
        
        # Africa
        'cape town': 95, 'cairo': 70, 'marrakech': 75, 'nairobi': 80,
    }
    
    # Base daily costs in INR for mid-range budget in Mumbai (index 100)
    BASE_DAILY_COSTS = {
        'accommodation': 2000,
        'food': 800,
        'local_transport': 400,
        'activities': 500,
    }
    
    # Budget multipliers
    BUDGET_MULTIPLIERS = {
        'budget': 0.6,
        'mid-range': 1.0,
        'luxury': 2.5,
    }
    
    @staticmethod
    def geocode_city(city_name: str) -> Optional[Tuple[float, float]]:
        """
        Get coordinates for a city name
        Uses OpenRouteService if available, falls back to hardcoded coordinates
        """
        city_lower = city_name.lower().strip()
        
        # Try OpenRouteService first for accurate, real-time geocoding
        if OPENROUTE_AVAILABLE:
            try:
                ors = OpenRouteService()
                result = ors.geocode(city_name, limit=1)
                if result and result.get('latitude') and result.get('longitude'):
                    logger.info(f"OpenRouteService geocoded '{city_name}' to ({result['latitude']}, {result['longitude']})")
                    return (result['latitude'], result['longitude'])
            except Exception as e:
                logger.warning(f"OpenRouteService geocoding failed for '{city_name}': {e}, falling back to local database")
        
        # Fallback to local database
        if city_lower in CostCalculationService.CITY_COORDINATES:
            return CostCalculationService.CITY_COORDINATES[city_lower]
        
        for city, coords in CostCalculationService.CITY_COORDINATES.items():
            if city in city_lower or city_lower in city:
                logger.info(f"Local database geocoded '{city_name}' to {city}: {coords}")
                return coords
        
        logger.warning(f"Could not geocode city: {city_name}")
        return None
    
    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates using Haversine formula"""
        R = 6371
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    @staticmethod
    def calculate_transportation_cost(distance_km: float) -> Dict[str, any]:
        """
        Calculate realistic transportation costs based on distance for Indian travel
        Returns costs for: Auto/Rickshaw, Bus, Train, Cab/Taxi, Flight
        Based on real Indian market rates (2024)
        """
        transport_options = {}
        
        # Short distance (< 20 km) - Local/Intracity
        if distance_km < 20:
            transport_options = {
                'auto': {
                    'cost': max(50, distance_km * 15),  # ₹15-20 per km
                    'name': 'Auto/Rickshaw',
                    'icon': '🛺',
                    'duration_minutes': int(distance_km * 3),  # ~20 kmph in city
                    'available': True
                },
                'cab': {
                    'cost': max(80, distance_km * 18),  # ₹18-25 per km
                    'name': 'Cab/Taxi',
                    'icon': '🚕',
                    'duration_minutes': int(distance_km * 2.5),
                    'available': True
                },
                'bus': {
                    'cost': max(20, distance_km * 2),  # ₹2-5 per km
                    'name': 'Local Bus',
                    'icon': '🚌',
                    'duration_minutes': int(distance_km * 4),
                    'available': True
                },
                'recommended': 'auto',
                'recommended_cost': max(50, distance_km * 15)
            }
        
        # Medium distance (20-100 km) - Intercity
        elif distance_km < 100:
            transport_options = {
                'bus': {
                    'cost': max(100, distance_km * 1.5),  # ₹1.5-2 per km
                    'name': 'AC Bus',
                    'icon': '🚌',
                    'duration_minutes': int(distance_km * 1.5),  # ~40 kmph
                    'available': True
                },
                'train': {
                    'cost': max(150, distance_km * 2),  # ₹2-3 per km
                    'name': 'Train (2nd AC)',
                    'icon': '🚆',
                    'duration_minutes': int(distance_km * 1.2),  # ~50 kmph
                    'available': True
                },
                'cab': {
                    'cost': max(500, distance_km * 12),  # ₹12-15 per km
                    'name': 'Cab/Taxi',
                    'icon': '🚕',
                    'duration_minutes': int(distance_km * 1.2),
                    'available': True
                },
                'recommended': 'train',
                'recommended_cost': max(150, distance_km * 2)
            }
        
        # Long distance (100-500 km) - Interstate
        elif distance_km < 500:
            transport_options = {
                'bus': {
                    'cost': max(400, distance_km * 1.2),  # ₹1-1.5 per km (Sleeper/AC)
                    'name': 'AC Sleeper Bus',
                    'icon': '🚌',
                    'duration_minutes': int(distance_km * 1.5),  # ~40 kmph
                    'available': True
                },
                'train': {
                    'cost': max(600, distance_km * 1.8),  # ₹1.5-2.5 per km (AC coaches)
                    'name': 'Train (2AC/3AC)',
                    'icon': '🚆',
                    'duration_minutes': int(distance_km * 1),  # ~60 kmph
                    'available': True
                },
                'flight': {
                    'cost': max(2500, min(8000, distance_km * 5)),  # Budget airlines
                    'name': 'Flight (Economy)',
                    'icon': '✈️',
                    'duration_minutes': int(distance_km * 0.5) + 120,  # Flight + airport time
                    'available': distance_km > 300
                },
                'cab': {
                    'cost': max(3000, distance_km * 10),  # ₹10-12 per km
                    'name': 'Cab/Taxi',
                    'icon': '🚕',
                    'duration_minutes': int(distance_km * 1.2),
                    'available': True
                },
                'recommended': 'train',
                'recommended_cost': max(600, distance_km * 1.8)
            }
        
        # Very long distance (500-1500 km) - Cross-country
        elif distance_km < 1500:
            transport_options = {
                'train': {
                    'cost': max(1200, distance_km * 1.5),  # ₹1-2 per km
                    'name': 'Train (AC/Sleeper)',
                    'icon': '🚆',
                    'duration_minutes': int(distance_km * 0.8),  # ~75 kmph
                    'available': True
                },
                'flight': {
                    'cost': max(3500, min(12000, distance_km * 4)),
                    'name': 'Flight (Economy)',
                    'icon': '✈️',
                    'duration_minutes': int(distance_km * 0.4) + 150,
                    'available': True
                },
                'bus': {
                    'cost': max(1000, distance_km * 1),
                    'name': 'AC Sleeper Bus',
                    'icon': '🚌',
                    'duration_minutes': int(distance_km * 1.5),
                    'available': True
                },
                'recommended': 'flight',
                'recommended_cost': max(3500, min(12000, distance_km * 4))
            }
        
        # International/Very long (> 1500 km)
        else:
            flight_cost = min(50000, max(5000, distance_km * 3.5))
            transport_options = {
                'flight': {
                    'cost': flight_cost,
                    'name': 'Flight (Economy)',
                    'icon': '✈️',
                    'duration_minutes': int(distance_km * 0.35) + 180,
                    'available': True
                },
                'train': {
                    'cost': max(2000, distance_km * 1.2),
                    'name': 'Train (AC)',
                    'icon': '🚆',
                    'duration_minutes': int(distance_km * 0.8),
                    'available': distance_km < 3000
                },
                'recommended': 'flight',
                'recommended_cost': flight_cost
            }
        
        # Add formatted duration for each available transport
        for mode, details in transport_options.items():
            if isinstance(details, dict) and 'duration_minutes' in details:
                hours = details['duration_minutes'] // 60
                minutes = details['duration_minutes'] % 60
                if hours > 0:
                    details['duration_formatted'] = f"{hours}h {minutes}m"
                else:
                    details['duration_formatted'] = f"{minutes}m"
                
                # Round costs
                details['cost'] = round(details['cost'])
        
        return transport_options
    
    @staticmethod
    def get_destination_cost_index(destination: str) -> float:
        """Get cost of living index for a destination"""
        destination_lower = destination.lower().strip()
        
        if destination_lower in CostCalculationService.COST_OF_LIVING_INDEX:
            return CostCalculationService.COST_OF_LIVING_INDEX[destination_lower] / 100.0
        
        for city, index in CostCalculationService.COST_OF_LIVING_INDEX.items():
            if city in destination_lower or destination_lower in city:
                return index / 100.0
        
        logger.info(f"Destination '{destination}' not found in cost index, using default 1.0")
        return 1.0
    
    @staticmethod
    def calculate_daily_costs(destination: str, budget: str = 'mid-range') -> Dict[str, float]:
        """Calculate realistic daily costs for a destination"""
        cost_index = CostCalculationService.get_destination_cost_index(destination)
        budget_multiplier = CostCalculationService.BUDGET_MULTIPLIERS.get(budget.lower(), 1.0)
        
        daily_costs = {}
        for category, base_cost in CostCalculationService.BASE_DAILY_COSTS.items():
            daily_costs[category] = round(base_cost * cost_index * budget_multiplier)
        
        daily_costs['total'] = sum(daily_costs.values())
        
        return daily_costs
    
    @staticmethod
    def calculate_trip_costs(
        destination: str,
        duration_days: int,
        budget: str = 'mid-range',
        travelers: int = 1,
        user_latitude: Optional[float] = None,
        user_longitude: Optional[float] = None,
        dest_latitude: Optional[float] = None,
        dest_longitude: Optional[float] = None
    ) -> Dict[str, any]:
        """Calculate comprehensive trip costs with realistic estimates"""
        daily_costs = CostCalculationService.calculate_daily_costs(destination, budget)
        
        accommodation_nights = max(1, duration_days - 1)
        total_accommodation = daily_costs['accommodation'] * accommodation_nights * travelers
        
        total_food = daily_costs['food'] * duration_days * travelers
        total_local_transport = daily_costs['local_transport'] * duration_days * travelers
        total_activities = daily_costs['activities'] * duration_days * travelers
        
        transportation_to_dest = 0
        transport_details = None
        distance_km = None
        
        if user_latitude and user_longitude and dest_latitude and dest_longitude:
            distance_km = CostCalculationService.calculate_distance(
                user_latitude, user_longitude, dest_latitude, dest_longitude
            )
            transport_options = CostCalculationService.calculate_transportation_cost(distance_km)
            
            # Get recommended transport cost
            recommended_mode = transport_options.get('recommended', 'train')
            recommended_cost = transport_options.get('recommended_cost', 1000)
            transportation_to_dest = round(recommended_cost * 2 * travelers)  # Round trip
            
            # Build detailed transport options for all modes
            transport_modes = {}
            for mode, details in transport_options.items():
                if isinstance(details, dict) and 'cost' in details:
                    transport_modes[mode] = {
                        'name': details['name'],
                        'icon': details['icon'],
                        'one_way_cost': details['cost'],
                        'round_trip_cost': details['cost'] * 2 * travelers,
                        'duration': details.get('duration_formatted', 'N/A'),
                        'duration_minutes': details.get('duration_minutes', 0),
                        'available': details.get('available', True)
                    }
            
            transport_details = {
                'distance_km': round(distance_km, 1),
                'recommended_mode': recommended_mode,
                'recommended_cost_one_way': round(recommended_cost),
                'recommended_cost_round_trip': transportation_to_dest,
                'all_options': transport_modes
            }
        
        misc_costs = round((total_accommodation + total_food + total_local_transport + total_activities) * 0.1)
        
        total_cost = (
            total_accommodation +
            total_food +
            total_local_transport +
            total_activities +
            transportation_to_dest +
            misc_costs
        )
        
        result = {
            'destination': destination,
            'duration_days': duration_days,
            'budget_category': budget,
            'travelers': travelers,
            'currency': 'INR',
            'cost_breakdown': {
                'accommodation': round(total_accommodation),
                'food': round(total_food),
                'transportation_local': round(total_local_transport),
                'transportation_to_destination': round(transportation_to_dest),
                'activities': round(total_activities),
                'miscellaneous': round(misc_costs),
                'total': round(total_cost)
            },
            'per_person_cost': round(total_cost / travelers) if travelers > 0 else 0,
            'daily_breakdown': {
                'accommodation_per_night': daily_costs['accommodation'],
                'food_per_day': daily_costs['food'],
                'local_transport_per_day': daily_costs['local_transport'],
                'activities_per_day': daily_costs['activities']
            },
            'cost_index': CostCalculationService.get_destination_cost_index(destination),
        }
        
        if transport_details:
            result['transportation_details'] = transport_details
            result['distance_km'] = distance_km
        
        return result
    
    @staticmethod
    def format_cost_summary(costs: Dict) -> str:
        """Format cost breakdown into a readable summary"""
        summary = f"""
Cost Breakdown for {costs['destination']} ({costs['duration_days']} days, {costs['travelers']} traveler(s)):

Daily Rates:
• Accommodation: ₹{costs['daily_breakdown']['accommodation_per_night']:,.0f} per night
• Food: ₹{costs['daily_breakdown']['food_per_day']:,.0f} per day
• Local Transport: ₹{costs['daily_breakdown']['local_transport_per_day']:,.0f} per day
• Activities: ₹{costs['daily_breakdown']['activities_per_day']:,.0f} per day

Total Trip Costs:
• Accommodation: ₹{costs['cost_breakdown']['accommodation']:,.0f}
• Food: ₹{costs['cost_breakdown']['food']:,.0f}
• Local Transportation: ₹{costs['cost_breakdown']['transportation_local']:,.0f}
"""
        
        if costs['cost_breakdown'].get('transportation_to_destination', 0) > 0:
            summary += f"• Transportation to Destination: ₹{costs['cost_breakdown']['transportation_to_destination']:,.0f}\n"
            if 'transportation_details' in costs:
                summary += f"  (Round trip, {costs['transportation_details']['recommended_mode']}, {costs['transportation_details']['distance_km']} km)\n"
        
        summary += f"""• Activities & Attractions: ₹{costs['cost_breakdown']['activities']:,.0f}
• Miscellaneous: ₹{costs['cost_breakdown']['miscellaneous']:,.0f}

TOTAL TRIP COST: ₹{costs['cost_breakdown']['total']:,.0f}
Per Person: ₹{costs['per_person_cost']:,.0f}

Note: Costs are calculated based on real cost-of-living data and distance-based transportation pricing.
Budget level: {costs['budget_category']}
"""
        
        return summary
