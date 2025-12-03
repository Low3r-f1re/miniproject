import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import os
import hashlib

logger = logging.getLogger(__name__)

# Simple in-memory cache with expiration
class SimpleCache:
    def __init__(self, expiration_minutes=60):
        self.cache = {}
        self.expiration_minutes = expiration_minutes
    
    def get(self, key):
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(minutes=self.expiration_minutes):
                return data
            else:
                del self.cache[key]
        return None
    
    def set(self, key, value):
        self.cache[key] = (value, datetime.now())
    
    def clear(self):
        self.cache.clear()

class OpenRouterService:
    """Service for interacting with OpenRouter API for travel planning and recommendations using Grok model."""

    # Class-level cache shared across instances
    _trip_plan_cache = SimpleCache(expiration_minutes=120)  # 2 hours
    _restaurant_cache = SimpleCache(expiration_minutes=60)  # 1 hour

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('OPENROUTER_API_KEY')
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "x-ai/grok-4.1-fast:free"  # Using Grok model as specified
    
    @staticmethod
    def _generate_cache_key(data: Dict) -> str:
        """Generate a cache key from request data"""
        cache_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()

    def generate_trip_plan(self, destination: str, duration_days: int, budget: str,
                          interests: List[str], travelers: int = 1,
                          start_date: str = None, user_home_city: str = None,
                          user_home_country: str = None, user_latitude: float = None,
                          user_longitude: float = None, dest_latitude: float = None,
                          dest_longitude: float = None) -> Dict[str, Any]:
        """
        Generate a comprehensive trip plan using OpenRouter API with Grok model.

        Args:
            destination: Target destination/city
            duration_days: Number of days for the trip
            budget: Budget category (budget, mid-range, luxury)
            interests: List of interests (culture, food, adventure, etc.)
            travelers: Number of travelers
            start_date: Optional start date for the trip
            user_home_city: User's home city (for travel context)
            user_home_country: User's home country (for visa/currency context)
            user_latitude: User's home latitude (for distance calculation)
            user_longitude: User's home longitude (for distance calculation)
            dest_latitude: Destination latitude (for distance calculation)
            dest_longitude: Destination longitude (for distance calculation)

        Returns:
            Dictionary containing trip plan details
        """
        if not self.api_key:
            return {"error": "OpenRouter API key not configured"}
        
        # Import services for routing and distance calculation
        from services.recommendation_service import RecommendationService
        from services.openroute_service import OpenRouteService
        
        # Calculate distance and transportation costs if location data is available
        distance_km = None
        transportation_info = None
        travel_time_info = ""
        location_context = ""
        route_details = None
        
        # Determine currency based on destination (needed early for location context)
        is_indian_destination = any(city in destination.lower() for city in ['india', 'bangalore', 'bengaluru', 'mumbai', 'delhi', 'chennai', 'kolkata', 'hyderabad', 'pune', 'ahmedabad', 'jaipur', 'goa'])
        currency = 'INR (₹)' if is_indian_destination else 'USD ($)'
        currency_symbol = '₹' if is_indian_destination else '$'
        
        if (user_latitude and user_longitude and dest_latitude and dest_longitude):
            # Try to use OpenRouteService for REAL route distance first
            ors = OpenRouteService()
            try:
                directions = ors.get_directions(
                    start_coords=(user_latitude, user_longitude),
                    end_coords=(dest_latitude, dest_longitude),
                    profile='driving-car'
                )
                
                if directions and 'distance_km' in directions:
                    # Use REAL road distance from OpenRouteService
                    distance_km = directions['distance_km']
                    duration_hours = directions['duration_hours']
                    
                    route_details = {
                        'distance_km': distance_km,
                        'duration_hours': duration_hours,
                        'duration_minutes': directions['duration_minutes'],
                        'has_real_route': True,
                        'steps_count': len(directions.get('steps', []))
                    }
                    
                    logger.info(f"Using real OpenRouteService route: {distance_km:.1f} km, {duration_hours:.2f} hours")
                else:
                    # Fallback to straight-line distance
                    distance_km = RecommendationService.calculate_distance(
                        user_latitude, user_longitude, dest_latitude, dest_longitude
                    )
                    logger.info(f"Using Haversine distance (ORS failed): {distance_km:.1f} km")
            except Exception as e:
                # Fallback to straight-line distance if OpenRouteService fails
                logger.warning(f"OpenRouteService failed, using Haversine: {e}")
                distance_km = RecommendationService.calculate_distance(
                    user_latitude, user_longitude, dest_latitude, dest_longitude
                )
            
            transportation_costs = RecommendationService.calculate_transportation_cost(distance_km)
            
            # Build transportation info for AI prompt
            transportation_info = {
                'distance_km': round(distance_km, 1),
                'options': transportation_costs,
                'recommended': transportation_costs.get('recommended', 0)
            }
            
            # Add travel time estimates with enhanced detail if we have real route
            if route_details and route_details.get('has_real_route'):
                # Use real route timing
                hours = int(route_details['duration_hours'])
                minutes = int((route_details['duration_hours'] - hours) * 60)
                travel_time_info = f"\n- REAL driving time: {hours}h {minutes}min via the actual road route"
                travel_time_info += f"\n- Route data: {route_details['steps_count']} navigation steps available"
                
                # Add alternative estimates
                if distance_km < 300:
                    travel_time_info += f"\n- Alternative: Local train/bus available"
                elif distance_km < 1000:
                    travel_time_info += f"\n- Alternative: Flight ~{int(distance_km/800)}h or train ~{int(distance_km/60)}h"
                else:
                    travel_time_info += f"\n- Alternative: Flight recommended (~{int(distance_km/800)}h)"
            else:
                # Use estimated timing (fallback)
                if distance_km < 300:
                    travel_time_info = f"\n- Estimated travel time: ~{int(distance_km/60)} hours by road/train"
                elif distance_km < 1000:
                    travel_time_info = f"\n- Estimated travel time: 1-3 hours by flight or {int(distance_km/60)} hours by train"
                else:
                    travel_time_info = f"\n- Estimated travel time: ~{int(distance_km/800)} hours by flight"
            
            # Build location context for AI with route accuracy indicator
            if user_home_city and user_home_country:
                route_type = "REAL ROAD ROUTE" if route_details and route_details.get('has_real_route') else "ESTIMATED DISTANCE"
                location_context = f"\nTRAVELER'S HOME LOCATION ({route_type}):\n- Traveling from: {user_home_city}, {user_home_country}\n- Distance to destination: {round(distance_km, 1)} km{travel_time_info}\n- Estimated transportation cost: {currency_symbol}{transportation_costs.get('recommended', 0)} one-way ({currency_symbol}{transportation_costs.get('recommended', 0) * 2} round trip)\n- Multiple transport options available with detailed pricing\n"
        
        # Check cache first
        cache_key_data = {
            'destination': destination.lower(),
            'duration_days': duration_days,
            'budget': budget,
            'interests': sorted(interests) if interests else [],
            'travelers': travelers,
            'user_location': f"{user_home_city},{user_home_country}" if user_home_city else None
        }
        cache_key = self._generate_cache_key(cache_key_data)
        
        cached_result = self._trip_plan_cache.get(cache_key)
        if cached_result:
            logger.info(f"Returning cached trip plan for {destination}")
            cached_result['from_cache'] = True
            return cached_result
        
        prompt = f"""
        Create a highly personalized {duration_days}-day trip itinerary for {travelers} traveler(s) visiting {destination}.
        
        TRAVELER PROFILE:
        - Budget category: {budget}
        - Primary interests: {', '.join(interests)}
        - Number of travelers: {travelers}
        {f'- Starting date: {start_date}' if start_date else ''}{location_context}

        IMPORTANT NOTES:
        1. Make this trip plan deeply personalized based on the traveler's interests
        2. Each recommendation should explain WHY it matches their specific interests
        3. Use {currency} for all cost estimates (currency symbol: {currency_symbol})
        4. Provide realistic, accurate pricing for {destination}
        {f'5. Include realistic transportation costs from {user_home_city}, {user_home_country} to {destination} (estimated: {currency_symbol}{transportation_info["recommended"]} one-way)' if transportation_info else ''}
        {f'6. Consider the {round(distance_km, 1)} km distance in your planning and budget estimates' if distance_km else ''}
        {f'7. If traveling internationally from {user_home_country}, include visa requirements and border crossing tips' if user_home_country and user_home_country.lower() not in destination.lower() else ''}

        Please provide a comprehensive trip plan with DETAILED DESCRIPTIONS for each place/activity:

        For EACH location/activity, include:
        1. Detailed description (history, culture, unique features, what makes it special)
        2. Why this place is perfect for their specific interests ({', '.join(interests)})
        3. Insider tips and local insights
        4. Best time of day to visit
        5. Estimated time needed
        6. Hidden gems nearby

        Format the response as a JSON object with this structure:
        {{
            "destination": "{destination}",
            "destination_overview": {{
                "description": "Rich, detailed description of the destination including its history, culture, and what makes it unique",
                "why_perfect_for_you": "Explanation of why this destination matches the traveler's interests",
                "local_vibe": "What the atmosphere and local culture feels like",
                "insider_secret": "A little-known fact or tip about this destination"
            }},
            "duration_days": {duration_days},
            "budget_category": "{budget}",
            "travelers": {travelers},
            "personalization_summary": "Brief explanation of how this itinerary is tailored to the traveler's interests",
            "itinerary": [
                {{
                    "day": 1,
                    "date": "YYYY-MM-DD",
                    "theme": "Day theme based on interests",
                    "activities": [
                        {{
                            "name": "Activity name",
                            "description": "Detailed description including history, significance, and what makes it special",
                            "why_recommended": "Why this activity matches the traveler's interests",
                            "duration_hours": 2,
                            "best_time": "morning/afternoon/evening",
                            "insider_tips": ["tip1", "tip2"],
                            "estimated_cost": 0,
                            "location": "specific address or area"
                        }}
                    ],
                    "meals": [
                        {{
                            "meal_type": "breakfast/lunch/dinner",
                            "restaurant_name": "Name",
                            "description": "What makes this place special, signature dishes",
                            "why_recommended": "How it aligns with interests",
                            "cuisine_type": "type",
                            "estimated_cost": 0,
                            "insider_tip": "Local secret about this place"
                        }}
                    ],
                    "accommodation": {{
                        "type": "hotel/hostel/etc",
                        "description": "What makes this accommodation special",
                        "location": "area name",
                        "estimated_cost": 0
                    }},
                    "hidden_gems": ["Lesser-known spots to explore based on interests"]
                }}
            ],
            "estimated_costs": {{
                "accommodation": 0,
                "food": 0,
                "transportation_local": 0,
                {f'"transportation_to_destination": {transportation_info["recommended"] * 2},' if transportation_info else '"transportation_to_destination": 0,'}
                "activities": 0,
                "miscellaneous": 0,
                "total": 0,
                "breakdown_explanation": "Explanation of costs based on budget category"
            }},
            {f'"travel_from_home": {{"distance_km": {transportation_info["distance_km"]}, "options": {json.dumps(transportation_info["options"])}, "recommended_cost": {transportation_info["recommended"]}, "round_trip_cost": {transportation_info["recommended"] * 2}}},' if transportation_info else ''}
            "recommendations": {{
                "best_time_to_visit": "season with explanation",
                "weather_tips": "Detailed weather information",
                "safety_tips": ["tip1 with context", "tip2 with context"],
                "cultural_tips": ["tip1 with explanation", "tip2 with explanation"],
                "packing_list": ["item1 (why needed)", "item2 (why needed)"],
                "local_customs": ["Important customs to know"],
                "language_basics": {{"phrase": "translation and when to use it"}}
            }},
            "local_transportation": {{
                "options": ["option1 with pros/cons", "option2 with pros/cons"],
                "recommendations": "Personalized transport advice based on itinerary and budget",
                "insider_tips": ["Transportation tips locals use"]
            }},
            "personalized_tips": [
                "Specific tips based on their interests like {', '.join(interests)}"
            ]
        }}
        """

        try:
            response = requests.post(
                url=f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=60,  # 60 second timeout
                data=json.dumps({
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "reasoning": {"enabled": True}
                })
            )

            if response.status_code != 200:
                return {"error": f"OpenRouter API error: {response.status_code} - {response.text}"}

            response_data = response.json()
            response_text = response_data['choices'][0]['message']['content'].strip()

            # Clean up response if it has markdown formatting
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()

            # Additional JSON cleaning
            # Remove any trailing commas before closing braces/brackets
            import re
            response_text = re.sub(r',(\s*[}\]])', r'\1', response_text)
            
            # Try to parse JSON response
            try:
                trip_plan = json.loads(response_text)
            except json.JSONDecodeError as json_err:
                logger.error(f"JSON parsing error: {json_err}")
                logger.error(f"Response text (first 500 chars): {response_text[:500]}")
                logger.error(f"Response text (around error position): {response_text[max(0, json_err.pos-50):min(len(response_text), json_err.pos+50)]}")
                
                # Try to fix common JSON issues
                # Remove any comments (// or /* */)
                response_text = re.sub(r'//.*?$', '', response_text, flags=re.MULTILINE)
                response_text = re.sub(r'/\*.*?\*/', '', response_text, flags=re.DOTALL)
                
                # Try parsing again
                try:
                    trip_plan = json.loads(response_text)
                except json.JSONDecodeError as json_err2:
                    logger.error(f"JSON parsing still failed after cleaning: {json_err2}")
                    raise ValueError(f"Failed to parse JSON response from AI model: {json_err2}")
            
            trip_plan['generated_at'] = datetime.now().isoformat()
            trip_plan['ai_generated'] = True
            
            # Cache the result
            self._trip_plan_cache.set(cache_key, trip_plan)
            logger.info(f"Cached trip plan for {destination}")

            return trip_plan

        except ValueError as ve:
            logger.error(f"Value error in trip plan generation: {ve}")
            # Fallback to static trip plan for Bengaluru
            if destination.lower() == "bengaluru":
                return self._get_bengaluru_fallback_plan(duration_days, budget, interests, travelers, start_date)
            return {"error": f"Failed to generate trip plan: {str(ve)}"}
        except Exception as e:
            logger.error(f"Error generating trip plan with OpenRouter: {e}")
            # Fallback to static trip plan for Bengaluru
            if destination.lower() == "bengaluru":
                return self._get_bengaluru_fallback_plan(duration_days, budget, interests, travelers, start_date)
            return {"error": f"Failed to generate trip plan: {str(e)}"}

    def get_restaurant_recommendations(self, location: str, cuisine_preferences: List[str] = None,
                                     budget: str = "mid-range", dietary_restrictions: List[str] = None,
                                     group_size: int = 2, meal_type: List[str] = None,
                                     popularity: str = "all", user_lat: float = None, 
                                     user_lon: float = None, max_distance_km: float = None) -> Dict[str, Any]:
        """
        Get restaurant recommendations for a location using OpenRouter API with Grok model.

        Args:
            location: City or area to find restaurants
            cuisine_preferences: Preferred cuisines
            budget: Budget category
            dietary_restrictions: Dietary restrictions to consider
            group_size: Number of people dining
            meal_type: Type of meal (breakfast, lunch, dinner, all-day)
            popularity: Filter type (all, popular, trending)
            user_lat: User's latitude for distance filtering
            user_lon: User's longitude for distance filtering
            max_distance_km: Maximum distance from user location

        Returns:
            Dictionary containing restaurant recommendations
        """
        if not self.api_key:
            return {"error": "OpenRouter API key not configured"}

        # Build meal type context
        meal_context = ""
        if meal_type and len(meal_type) > 0:
            meal_list = [m.replace('-', ' ').title() for m in meal_type if m != 'all-day']
            if meal_list:
                meal_context = f"\n- Meal time focus: {', '.join(meal_list)}"
                meal_context += "\n- Recommend restaurants that are best known for these specific meal times"
        
        # Build popularity context
        popularity_context = ""
        if popularity == "popular":
            popularity_context = "\n- FOCUS ON POPULAR RESTAURANTS: Recommend well-established, highly-rated restaurants with a proven track record"
        elif popularity == "trending":
            popularity_context = "\n- FOCUS ON TRENDING SPOTS: Recommend the newest, buzziest restaurants that are currently hot and gaining popularity"
        
        # Build location/distance context
        location_context = ""
        distance_constraint = ""
        if user_lat and user_lon and max_distance_km:
            location_context = f"\n- User's current location: Near coordinates ({user_lat:.4f}, {user_lon:.4f})"
            location_context += f"\n- STRICT DISTANCE REQUIREMENT: Only recommend restaurants within {max_distance_km} km radius from user's location"
            location_context += "\n- Prioritize restaurants that are CLOSEST to the user"
            distance_constraint = f"\n\n🚨 CRITICAL: You MUST ONLY recommend restaurants that are within {max_distance_km} km of the user's location at ({user_lat:.4f}, {user_lon:.4f}). Do NOT recommend restaurants that are farther away. The user wants nearby options within walking/short driving distance."

        prompt = f"""
        Create HIGHLY PERSONALIZED restaurant recommendations for {location} for a group of {group_size} people.
        
        DINER PROFILE:
        - Budget: {budget}
        {f'- Cuisine preferences: {", ".join(cuisine_preferences)}' if cuisine_preferences else ''}
        {f'- Dietary restrictions: {", ".join(dietary_restrictions)}' if dietary_restrictions else ''}
        - Group size: {group_size}{meal_context}{popularity_context}{location_context}{distance_constraint}

        IMPORTANT: Provide restaurants with RICH, DETAILED DESCRIPTIONS that help the diner understand what makes each place special.

        For EACH restaurant, include:
        1. Detailed description of the restaurant (history, chef's background, unique features, what makes it special)
        2. Atmosphere and ambiance (what it feels like to dine there)
        3. Signature dishes with descriptions (not just names, but what makes them special)
        4. Why this restaurant is perfect for their specific preferences and group size
        5. Insider tips (best dishes, when to visit, how to order like a local)
        6. Hidden menu items or local secrets
        7. Cultural significance or local story

        Provide 5-8 restaurant recommendations in this format:
        {{
            "location": "{location}",
            "personalization_summary": "Brief explanation of how these recommendations match the diner's preferences",
            "recommendations": [
                {{
                    "name": "Restaurant Name",
                    "cuisine": "Cuisine Type",
                    "price_range": "$$",
                    "rating": 4.5,
                    "detailed_description": "Rich description including history, chef's background, what makes it unique, and the dining experience",
                    "atmosphere": {{
                        "vibe": "casual/formal/romantic/lively",
                        "description": "Detailed description of what it feels like to dine here",
                        "best_for": "date night/family/business/casual"
                    }},
                    "signature_dishes": [
                        {{
                            "name": "Dish name",
                            "description": "Detailed description including ingredients, preparation, and why it's special",
                            "estimated_price": 0,
                            "why_must_try": "What makes this dish stand out"
                        }}
                    ],
                    "why_perfect_for_you": "Detailed explanation of why this restaurant matches the group's preferences",
                    "insider_tips": [
                        "Specific tips like best time to visit, how to order, hidden menu items"
                    ],
                    "best_time": "lunch/dinner with explanation",
                    "reservation_needed": true/false,
                    "address": "full address",
                    "local_secret": "A little-known fact or insider tip about this restaurant",
                    "cultural_note": "Any cultural significance or local story"
                }}
            ],
            "dining_tips": [
                "Local dining customs and etiquette",
                "How to make the most of your dining experience",
                "Budget-saving tips if applicable"
            ],
            "food_scene_overview": "Brief description of the local food scene in {location}"
        }}
        """

        try:
            response = requests.post(
                url=f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                data=json.dumps({
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "reasoning": {"enabled": True}
                })
            )

            if response.status_code != 200:
                return {"error": f"OpenRouter API error: {response.status_code} - {response.text}"}

            response_data = response.json()
            response_text = response_data['choices'][0]['message']['content'].strip()

            # Clean up response
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()

            # Additional JSON cleaning
            import re
            response_text = re.sub(r',(\s*[}\]])', r'\1', response_text)
            
            # Try to parse JSON response
            try:
                recommendations = json.loads(response_text)
            except json.JSONDecodeError as json_err:
                logger.error(f"JSON parsing error in restaurant recommendations: {json_err}")
                logger.error(f"Response text (first 500 chars): {response_text[:500]}")
                
                # Try to fix common JSON issues
                response_text = re.sub(r'//.*?$', '', response_text, flags=re.MULTILINE)
                response_text = re.sub(r'/\*.*?\*/', '', response_text, flags=re.DOTALL)
                
                try:
                    recommendations = json.loads(response_text)
                except json.JSONDecodeError as json_err2:
                    logger.error(f"JSON parsing still failed after cleaning: {json_err2}")
                    return {"error": f"Failed to parse JSON response: {json_err2}"}
            
            recommendations['generated_at'] = datetime.now().isoformat()

            return recommendations

        except Exception as e:
            logger.error(f"Error getting restaurant recommendations with OpenRouter: {e}")
            return {"error": f"Failed to get restaurant recommendations: {str(e)}"}

    def enhance_collaboration_plan(self, existing_plan: Dict[str, Any], collaborators: List[str],
                                 preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance an existing trip plan based on collaborator preferences using OpenRouter API with Grok model.

        Args:
            existing_plan: Current trip plan
            collaborators: List of collaborator names/emails
            preferences: Dictionary of preferences from collaborators

        Returns:
            Enhanced trip plan incorporating collaboration
        """
        if not self.api_key:
            return {"error": "OpenRouter API key not configured"}

        prompt = f"""
        Enhance this existing trip plan by incorporating preferences from {len(collaborators)} collaborators.

        Current Plan:
        {json.dumps(existing_plan, indent=2)}

        Collaborator Preferences:
        {json.dumps(preferences, indent=2)}

        Please create an enhanced version that:
        1. Balances different preferences and interests
        2. Suggests compromises where preferences conflict
        3. Adds collaborative activities
        4. Adjusts itinerary to accommodate group dynamics
        5. Provides alternative options for different group members
        6. Includes communication tips for the group

        Format as JSON with the same structure as the original plan, plus:
        {{
            "collaborative_enhancements": {{
                "group_activities": ["activity1", "activity2"],
                "compromise_suggestions": ["suggestion1"],
                "alternative_options": ["option1"],
                "communication_tips": ["tip1"]
            }}
        }}
        """

        try:
            response = requests.post(
                url=f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                data=json.dumps({
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "reasoning": {"enabled": True}
                })
            )

            if response.status_code != 200:
                return {"error": f"OpenRouter API error: {response.status_code} - {response.text}"}

            response_data = response.json()
            response_text = response_data['choices'][0]['message']['content'].strip()

            # Clean up response
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()

            # Additional JSON cleaning
            import re
            response_text = re.sub(r',(\s*[}\]])', r'\1', response_text)
            
            # Try to parse JSON response
            try:
                enhanced_plan = json.loads(response_text)
            except json.JSONDecodeError as json_err:
                logger.error(f"JSON parsing error in enhance_collaboration_plan: {json_err}")
                logger.error(f"Response text (first 500 chars): {response_text[:500]}")
                
                # Try to fix common JSON issues
                response_text = re.sub(r'//.*?$', '', response_text, flags=re.MULTILINE)
                response_text = re.sub(r'/\*.*?\*/', '', response_text, flags=re.DOTALL)
                
                try:
                    enhanced_plan = json.loads(response_text)
                except json.JSONDecodeError as json_err2:
                    logger.error(f"JSON parsing still failed after cleaning: {json_err2}")
                    return {"error": f"Failed to parse JSON response: {json_err2}"}
            
            enhanced_plan['enhanced_at'] = datetime.now().isoformat()
            enhanced_plan['collaborators_count'] = len(collaborators)

            return enhanced_plan

        except Exception as e:
            logger.error(f"Error enhancing collaboration plan with OpenRouter: {e}")
            return {"error": f"Failed to enhance collaboration plan: {str(e)}"}

    def get_offline_content(self, destination: str, content_type: str = "general") -> Dict[str, Any]:
        """
        Generate offline-friendly content for destinations using OpenRouter API with Grok model.

        Args:
            destination: Target destination
            content_type: Type of content (general, emergency, transportation, etc.)

        Returns:
            Offline content dictionary
        """
        if not self.api_key:
            return {"error": "OpenRouter API key not configured"}

        content_types = {
            "general": "general travel information, maps, and tips",
            "emergency": "emergency contacts, hospitals, and safety information",
            "transportation": "public transport routes, schedules, and navigation",
            "food": "restaurant information and local food options",
            "attractions": "key attractions and offline guides"
        }

        prompt = f"""
        Create offline-friendly content for {destination} focusing on {content_types.get(content_type, content_type)}.

        Include information that would be useful without internet access:
        - Emergency phone numbers and addresses
        - Public transportation routes and schedules
        - Key landmarks and navigation tips
        - Restaurant information and menus
        - Local customs and language basics
        - Safety information
        - Medical facilities

        Format as JSON:
        {{
            "destination": "{destination}",
            "content_type": "{content_type}",
            "offline_data": {{
                "emergency_contacts": {{
                    "police": "number",
                    "ambulance": "number",
                    "tourist_police": "number"
                }},
                "transportation": {{
                    "bus_routes": ["route1", "route2"],
                    "metro_stations": ["station1"],
                    "taxi_info": "details"
                }},
                "key_locations": [
                    {{
                        "name": "Location Name",
                        "address": "Address",
                        "coordinates": "lat,lng",
                        "description": "description"
                    }}
                ],
                "local_tips": ["tip1", "tip2"],
                "language_basics": {{
                    "hello": "translation",
                    "thank_you": "translation"
                }}
            }},
            "last_updated": "{datetime.now().isoformat()}"
        }}
        """

        try:
            response = requests.post(
                url=f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                data=json.dumps({
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "reasoning": {"enabled": True}
                })
            )

            if response.status_code != 200:
                return {"error": f"OpenRouter API error: {response.status_code} - {response.text}"}

            response_data = response.json()
            response_text = response_data['choices'][0]['message']['content'].strip()

            # Clean up response
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()

            # Additional JSON cleaning
            import re
            response_text = re.sub(r',(\s*[}\]])', r'\1', response_text)
            
            # Try to parse JSON response
            try:
                offline_content = json.loads(response_text)
            except json.JSONDecodeError as json_err:
                logger.error(f"JSON parsing error in get_offline_content: {json_err}")
                logger.error(f"Response text (first 500 chars): {response_text[:500]}")
                
                # Try to fix common JSON issues
                response_text = re.sub(r'//.*?$', '', response_text, flags=re.MULTILINE)
                response_text = re.sub(r'/\*.*?\*/', '', response_text, flags=re.DOTALL)
                
                try:
                    offline_content = json.loads(response_text)
                except json.JSONDecodeError as json_err2:
                    logger.error(f"JSON parsing still failed after cleaning: {json_err2}")
                    return {"error": f"Failed to parse JSON response: {json_err2}"}
            
            return offline_content

        except Exception as e:
            logger.error(f"Error generating offline content with OpenRouter: {e}")
            return {"error": f"Failed to generate offline content: {str(e)}"}

    def _get_bengaluru_fallback_plan(self, duration_days: int, budget: str,
                                    interests: List[str], travelers: int = 1,
                                    start_date: str = None) -> Dict[str, Any]:
        """
        Generate a static fallback trip plan for Bengaluru when API fails.

        Returns:
            Dictionary containing a comprehensive 3-day trip plan for Bengaluru
        """
        # Calculate dates if start_date is provided
        dates = []
        if start_date:
            from datetime import datetime, timedelta
            start = datetime.fromisoformat(start_date)
            for i in range(duration_days):
                dates.append((start + timedelta(days=i)).strftime("%Y-%m-%d"))
        else:
            dates = ["TBD"] * duration_days

        # Base plan structure
        plan = {
            "destination": "Bengaluru",
            "duration_days": duration_days,
            "budget_category": budget,
            "travelers": travelers,
            "itinerary": [],
            "estimated_costs": {
                "accommodation": 4500,  # 3 nights at mid-range hotel
                "food": 1800,  # Meals for 3 days
                "transportation": 1200,  # Local transport
                "activities": 1500,  # Entry fees and activities
                "miscellaneous": 1000,  # Shopping, tips, etc.
                "total": 10000
            },
            "recommendations": {
                "best_time_to_visit": "October to March (winter season)",
                "weather_tips": "Bengaluru has pleasant weather year-round, but pack light layers for cooler evenings",
                "safety_tips": [
                    "Use registered taxis or ride-sharing apps like Ola/Uber",
                    "Keep valuables secure in crowded areas",
                    "Stay aware of traffic when crossing roads",
                    "Drink only bottled or filtered water"
                ],
                "cultural_tips": [
                    "Remove shoes when entering temples and homes",
                    "Use right hand for eating and giving/receiving items",
                    "Bargain politely at local markets",
                    "Respect local customs and dress modestly at religious sites"
                ],
                "packing_list": [
                    "Comfortable walking shoes",
                    "Light jacket or sweater",
                    "Modest clothing for temple visits",
                    "Sunscreen and hat",
                    "Reusable water bottle",
                    "Power adapter for Indian plugs",
                    "Cash (INR) and card backup"
                ]
            },
            "local_transportation": {
                "options": [
                    "Bengaluru Metro (fast and efficient)",
                    "Auto-rickshaws (three-wheeler taxis)",
                    "App-based cabs (Ola, Uber)",
                    "Buses (inexpensive but crowded)"
                ],
                "recommendations": "Use Bengaluru Metro for major routes, Ola/Uber for convenience, and auto-rickshaws for short distances. Always negotiate fares for auto-rickshaws."
            },
            "generated_at": datetime.now().isoformat(),
            "ai_generated": False,
            "fallback": True
        }

        # Create detailed itinerary based on duration
        if duration_days >= 3:
            plan["itinerary"] = [
                {
                    "day": 1,
                    "date": dates[0],
                    "activities": [
                        "Arrive in Bengaluru and check into hotel",
                        "Visit Vidhana Soudha (State Legislature Building) - admire colonial architecture",
                        "Explore Cubbon Park - relax in the green lung of the city",
                        "Visit Bangalore Palace - stunning Indo-Saracenic architecture",
                        "Evening walk in MG Road area"
                    ],
                    "meals": [
                        "Breakfast at hotel",
                        "Lunch at a local South Indian restaurant (dosa, idli)",
                        "Dinner at a rooftop restaurant with city views"
                    ],
                    "transportation": "Airport pickup to hotel, then local taxi/auto-rickshaw",
                    "accommodation": "Check into mid-range hotel in central Bengaluru (₹1,500-2,500/night)"
                },
                {
                    "day": 2,
                    "date": dates[1],
                    "activities": [
                        "Morning visit to ISKCON Temple - spiritual experience and vegetarian food",
                        "Explore Commercial Street for shopping and street food",
                        "Visit Tipu Sultan's Summer Palace (Daria Daulat Bagh)",
                        "Afternoon at Lalbagh Botanical Garden - beautiful gardens and glass house",
                        "Evening at Brigade Road for shopping and cafes"
                    ],
                    "meals": [
                        "Breakfast at hotel or local cafe",
                        "Lunch at a restaurant near Commercial Street",
                        "Dinner at a rooftop cafe or local eatery"
                    ],
                    "transportation": "Metro or taxi between attractions",
                    "accommodation": "Continue at same hotel"
                },
                {
                    "day": 3,
                    "date": dates[2],
                    "activities": [
                        "Morning visit to Wonderla Amusement Park or Nandi Hills day trip",
                        "Afternoon shopping at Forum Mall or local markets",
                        "Visit Bull Temple (Basavanagudi) - unique 16th-century temple",
                        "Evening departure or relax at hotel"
                    ],
                    "meals": [
                        "Breakfast at hotel",
                        "Lunch at a restaurant near your activity",
                        "Dinner at airport or en route"
                    ],
                    "transportation": "Taxi to final destinations, then to airport",
                    "accommodation": "Check out from hotel"
                }
            ]

        # Adjust costs based on budget
        if budget == "budget":
            plan["estimated_costs"] = {
                "accommodation": 2700,  # 3 nights at budget hotel
                "food": 1200,
                "transportation": 800,
                "activities": 800,
                "miscellaneous": 600,
                "total": 6100
            }
        elif budget == "luxury":
            plan["estimated_costs"] = {
                "accommodation": 9000,  # 3 nights at luxury hotel
                "food": 3000,
                "transportation": 2000,
                "activities": 3000,
                "miscellaneous": 2000,
                "total": 19000
            }

        # Add interest-specific recommendations
        if "food" in interests:
            plan["itinerary"][1]["activities"].append("Food tour of Mavalli Tiffin Room and local eateries")
        if "adventure" in interests:
            plan["itinerary"][2]["activities"][0] = "Adventure activities at Wonderla Amusement Park"
        if "culture" in interests:
            plan["itinerary"][0]["activities"].append("Visit local art galleries or cultural centers")
        if "shopping" in interests:
            plan["itinerary"][1]["activities"].append("Extended shopping time at Commercial Street and Brigade Road")

        return plan
