try:
    import google.generativeai as genai  # type: ignore
    GEMINI_AVAILABLE = True
except (ImportError, TypeError) as e:
    genai = None
    GEMINI_AVAILABLE = False
    print(f"Gemini AI not available: {e}")

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class GeminiService:
    """Service for interacting with Google's Gemini API for travel planning and recommendations."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY')
        if self.api_key and GEMINI_AVAILABLE:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        else:
            if not GEMINI_AVAILABLE:
                logger.warning("google-generativeai package not installed")
            else:
                logger.warning("Gemini API key not provided")
            self.model = None

    def generate_trip_plan(self, destination: str, duration_days: int, budget: str,
                          interests: List[str], travelers: int = 1,
                          start_date: str = None) -> Dict[str, Any]:
        """
        Generate a comprehensive trip plan using Gemini AI.

        Args:
            destination: Target destination/city
            duration_days: Number of days for the trip
            budget: Budget category (budget, mid-range, luxury)
            interests: List of interests (culture, food, adventure, etc.)
            travelers: Number of travelers
            start_date: Optional start date for the trip

        Returns:
            Dictionary containing trip plan details
        """
        if not self.model:
            return {"error": "Gemini API not configured"}

        prompt = f"""
        Create a detailed {duration_days}-day trip itinerary for {travelers} traveler(s) visiting {destination}.
        Budget category: {budget}
        Interests: {', '.join(interests)}
        {f'Starting date: {start_date}' if start_date else ''}

        Please provide a comprehensive trip plan including:
        1. Daily itinerary with activities, meals, and transportation
        2. Estimated costs breakdown
        3. Best time to visit and weather considerations
        4. Local transportation recommendations
        5. Safety tips and cultural etiquette
        6. Packing suggestions
        7. Emergency contacts and useful apps

        Format the response as a JSON object with the following structure:
        {{
            "destination": "{destination}",
            "duration_days": {duration_days},
            "budget_category": "{budget}",
            "travelers": {travelers},
            "itinerary": [
                {{
                    "day": 1,
                    "date": "YYYY-MM-DD",
                    "activities": ["activity1", "activity2"],
                    "meals": ["breakfast", "lunch", "dinner"],
                    "transportation": "details",
                    "accommodation": "suggestion"
                }}
            ],
            "estimated_costs": {{
                "accommodation": 0,
                "food": 0,
                "transportation": 0,
                "activities": 0,
                "miscellaneous": 0,
                "total": 0
            }},
            "recommendations": {{
                "best_time_to_visit": "season",
                "weather_tips": "tips",
                "safety_tips": ["tip1", "tip2"],
                "cultural_tips": ["tip1", "tip2"],
                "packing_list": ["item1", "item2"]
            }},
            "local_transportation": {{
                "options": ["option1", "option2"],
                "recommendations": "details"
            }}
        }}
        """

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()

            # Clean up response if it has markdown formatting
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

            # Parse JSON response
            trip_plan = json.loads(response_text)
            trip_plan['generated_at'] = datetime.now().isoformat()
            trip_plan['ai_generated'] = True

            return trip_plan

        except Exception as e:
            logger.error(f"Error generating trip plan: {e}")
            return {"error": f"Failed to generate trip plan: {str(e)}"}

    def get_restaurant_recommendations(self, location: str, cuisine_preferences: List[str] = None,
                                     budget: str = "mid-range", dietary_restrictions: List[str] = None,
                                     group_size: int = 2) -> Dict[str, Any]:
        """
        Get restaurant recommendations for a location using Gemini AI.

        Args:
            location: City or area to find restaurants
            cuisine_preferences: Preferred cuisines
            budget: Budget category
            dietary_restrictions: Dietary restrictions to consider
            group_size: Number of people dining

        Returns:
            Dictionary containing restaurant recommendations
        """
        if not self.model:
            return {"error": "Gemini API not configured"}

        prompt = f"""
        Recommend restaurants in {location} for {group_size} people.
        Budget: {budget}
        {f'Cuisine preferences: {", ".join(cuisine_preferences)}' if cuisine_preferences else ''}
        {f'Dietary restrictions: {", ".join(dietary_restrictions)}' if dietary_restrictions else ''}

        Provide 5-8 restaurant recommendations with the following details for each:
        - Restaurant name
        - Cuisine type
        - Price range ($, $$, $$$, $$$$)
        - Rating (out of 5)
        - Key dishes/specialties
        - Atmosphere/dining experience
        - Best time to visit
        - Reservation requirements
        - Location/address
        - Why it's recommended for this group

        Format as JSON:
        {{
            "location": "{location}",
            "recommendations": [
                {{
                    "name": "Restaurant Name",
                    "cuisine": "Cuisine Type",
                    "price_range": "$$",
                    "rating": 4.5,
                    "specialties": ["dish1", "dish2"],
                    "atmosphere": "description",
                    "best_time": "lunch/dinner",
                    "reservation_needed": true/false,
                    "address": "address",
                    "recommendation_reason": "why it's good for this group"
                }}
            ],
            "additional_tips": ["tip1", "tip2"]
        }}
        """

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()

            # Clean up response
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

            recommendations = json.loads(response_text)
            recommendations['generated_at'] = datetime.now().isoformat()

            return recommendations

        except Exception as e:
            logger.error(f"Error getting restaurant recommendations: {e}")
            return {"error": f"Failed to get restaurant recommendations: {str(e)}"}

    def enhance_collaboration_plan(self, existing_plan: Dict[str, Any], collaborators: List[str],
                                 preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance an existing trip plan based on collaborator preferences.

        Args:
            existing_plan: Current trip plan
            collaborators: List of collaborator names/emails
            preferences: Dictionary of preferences from collaborators

        Returns:
            Enhanced trip plan incorporating collaboration
        """
        if not self.model:
            return {"error": "Gemini API not configured"}

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
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()

            # Clean up response
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

            enhanced_plan = json.loads(response_text)
            enhanced_plan['enhanced_at'] = datetime.now().isoformat()
            enhanced_plan['collaborators_count'] = len(collaborators)

            return enhanced_plan

        except Exception as e:
            logger.error(f"Error enhancing collaboration plan: {e}")
            return {"error": f"Failed to enhance collaboration plan: {str(e)}"}

    def get_offline_content(self, destination: str, content_type: str = "general") -> Dict[str, Any]:
        """
        Generate offline-friendly content for destinations.

        Args:
            destination: Target destination
            content_type: Type of content (general, emergency, transportation, etc.)

        Returns:
            Offline content dictionary
        """
        if not self.model:
            return {"error": "Gemini API not configured"}

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
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()

            # Clean up response
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

            offline_content = json.loads(response_text)
            return offline_content

        except Exception as e:
            logger.error(f"Error generating offline content: {e}")
            return {"error": f"Failed to generate offline content: {str(e)}"}
