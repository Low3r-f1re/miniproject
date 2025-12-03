"""Service for fetching relevant images from Unsplash API"""
import requests
import os
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

class ImageService:
    """Service for fetching travel and location images"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('UNSPLASH_ACCESS_KEY')
        self.base_url = "https://api.unsplash.com"
    
    def search_image(self, query: str, orientation: str = "landscape") -> Optional[str]:
        """
        Search for an image on Unsplash and return the URL.
        
        Args:
            query: Search term for the image
            orientation: Image orientation (landscape, portrait, squarish)
            
        Returns:
            URL of the image or None if not found
        """
        if not self.api_key:
            logger.warning("Unsplash API key not configured, using placeholder")
            return self._get_placeholder_image(query)
        
        try:
            response = requests.get(
                f"{self.base_url}/search/photos",
                params={
                    "query": query,
                    "per_page": 1,
                    "orientation": orientation
                },
                headers={
                    "Authorization": f"Client-ID {self.api_key}"
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('results') and len(data['results']) > 0:
                    return data['results'][0]['urls']['regular']
            
            logger.warning(f"No image found for query: {query}")
            return self._get_placeholder_image(query)
            
        except Exception as e:
            logger.error(f"Error fetching image from Unsplash: {e}")
            return self._get_placeholder_image(query)
    
    def get_destination_image(self, destination: str) -> Optional[str]:
        """Get an image for a destination."""
        return self.search_image(f"{destination} travel destination")
    
    def get_activity_image(self, activity_name: str, location: str = "") -> Optional[str]:
        """Get an image for an activity with improved specificity."""
        # Build a more focused query that prioritizes relevant keywords
        # Extract key nouns and remove generic words
        activity_lower = activity_name.lower()
        
        # Define stop words to remove from activity names
        stop_words = {'morning', 'evening', 'afternoon', 'visit', 'trip', 'tour', 'experience', 'the', 'a', 'an', 'at', 'in', 'to'}
        
        # Split and filter activity name
        words = [w for w in activity_lower.split() if w not in stop_words]
        cleaned_activity = ' '.join(words) if words else activity_name
        
        # Build query prioritizing location and specific activity
        if location:
            # Put location first for better geographic relevance
            query = f"{location} {cleaned_activity}"
        else:
            query = cleaned_activity
            
        return self.search_image(query)
    
    def get_restaurant_image(self, restaurant_type: str, cuisine: str = "") -> Optional[str]:
        """Get an image for a restaurant with improved query."""
        # Build specific query prioritizing cuisine and food
        if cuisine:
            # Prioritize cuisine type with food keyword
            query = f"{cuisine} food dish"
        else:
            query = f"{restaurant_type} food restaurant"
        return self.search_image(query.strip())
    
    def _get_placeholder_image(self, query: str) -> str:
        """
        Generate a contextually relevant placeholder image URL.
        Uses foodish.api for food images and picsum for other categories.
        """
        query_lower = query.lower()
        
        # Define category keywords
        food_keywords = ['food', 'dish', 'cuisine', 'restaurant', 'dining', 'meal', 'south indian', 'italian', 'chinese', 'japanese', 'mexican', 'thai', 'indian']
        
        # Check if query is food-related
        is_food_related = any(keyword in query_lower for keyword in food_keywords)
        
        if is_food_related:
            # Use foodish API for consistent food images as placeholders
            # This ensures restaurant/food queries always show food images
            # The API returns random food images - we'll use a hash of the query for consistency
            food_categories = ['biryani', 'butter-chicken', 'dosa', 'idly', 'rice', 'samosa', 'pasta', 'burger', 'pizza']
            # Pick a category based on query hash for consistency
            category_index = abs(hash(query)) % len(food_categories)
            return f"https://foodish-api.com/images/{food_categories[category_index]}/{food_categories[category_index]}1.jpg"
        
        # For non-food queries, use picsum with category-based seeds
        categories = {
            'nature': {'keywords': ['mountain', 'beach', 'forest', 'lake', 'nature', 'outdoor'], 'seed_range': (200, 299)},
            'city': {'keywords': ['city', 'urban', 'building', 'architecture', 'street', 'downtown'], 'seed_range': (300, 399)},
            'culture': {'keywords': ['temple', 'museum', 'monument', 'palace', 'heritage', 'historical'], 'seed_range': (400, 499)},
            'activity': {'keywords': ['activity', 'sport', 'adventure', 'hiking', 'climbing', 'diving'], 'seed_range': (500, 599)},
            'travel': {'keywords': ['travel', 'destination', 'tourism', 'vacation', 'trip'], 'seed_range': (600, 699)},
        }
        
        # Find matching category
        matched_category = None
        for category, info in categories.items():
            if any(keyword in query_lower for keyword in info['keywords']):
                matched_category = category
                break
        
        # Generate seed within category range or use general range
        if matched_category:
            seed_min, seed_max = categories[matched_category]['seed_range']
            seed = seed_min + (abs(hash(query)) % (seed_max - seed_min + 1))
        else:
            # Generic travel/destination images for unmatched queries
            seed = 600 + (abs(hash(query)) % 100)
        
        return f"https://picsum.photos/seed/{seed}/800/600"
    
    def batch_search_images(self, queries: List[str]) -> Dict[str, str]:
        """
        Search for multiple images at once.
        
        Args:
            queries: List of search terms
            
        Returns:
            Dictionary mapping queries to image URLs
        """
        results = {}
        for query in queries:
            results[query] = self.search_image(query)
        return results
