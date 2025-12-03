import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class OfflineCache:
    """Simple offline cache for storing trip plans and recommendations."""

    def __init__(self, cache_dir: str = 'cache'):
        self.cache_dir = cache_dir
        self.trip_plans_file = os.path.join(cache_dir, 'trip_plans.json')
        self.recommendations_file = os.path.join(cache_dir, 'recommendations.json')

        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)

        # Initialize cache files if they don't exist
        for cache_file in [self.trip_plans_file, self.recommendations_file]:
            if not os.path.exists(cache_file):
                with open(cache_file, 'w') as f:
                    json.dump({}, f)

    def _load_cache(self, cache_file: str) -> Dict[str, Any]:
        """Load cache data from file."""
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_cache(self, cache_file: str, data: Dict[str, Any]):
        """Save cache data to file."""
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving cache to {cache_file}: {e}")

    def cache_trip_plan(self, plan_id: int, trip_plan: Dict[str, Any], user_id: int):
        """Cache a trip plan for offline access."""
        cache_data = self._load_cache(self.trip_plans_file)
        cache_key = f"{user_id}_{plan_id}"

        cache_data[cache_key] = {
            'plan_id': plan_id,
            'user_id': user_id,
            'data': trip_plan,
            'cached_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=30)).isoformat()  # Cache for 30 days
        }

        self._save_cache(self.trip_plans_file, cache_data)
        logger.info(f"Cached trip plan {plan_id} for user {user_id}")

    def get_cached_trip_plan(self, plan_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a cached trip plan."""
        cache_data = self._load_cache(self.trip_plans_file)
        cache_key = f"{user_id}_{plan_id}"

        if cache_key not in cache_data:
            return None

        cached_item = cache_data[cache_key]
        expires_at = datetime.fromisoformat(cached_item['expires_at'])

        if datetime.now() > expires_at:
            # Cache expired, remove it
            del cache_data[cache_key]
            self._save_cache(self.trip_plans_file, cache_data)
            return None

        return cached_item['data']

    def cache_recommendations(self, location: str, recommendations: Dict[str, Any], query_params: Dict[str, Any]):
        """Cache recommendations for offline access."""
        cache_data = self._load_cache(self.recommendations_file)
        cache_key = f"{location}_{hash(str(sorted(query_params.items())))}"

        cache_data[cache_key] = {
            'location': location,
            'query_params': query_params,
            'data': recommendations,
            'cached_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=7)).isoformat()  # Cache for 7 days
        }

        self._save_cache(self.recommendations_file, cache_data)
        logger.info(f"Cached recommendations for {location}")

    def get_cached_recommendations(self, location: str, query_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Retrieve cached recommendations."""
        cache_data = self._load_cache(self.recommendations_file)
        cache_key = f"{location}_{hash(str(sorted(query_params.items())))}"

        if cache_key not in cache_data:
            return None

        cached_item = cache_data[cache_key]
        expires_at = datetime.fromisoformat(cached_item['expires_at'])

        if datetime.now() > expires_at:
            # Cache expired, remove it
            del cache_data[cache_key]
            self._save_cache(self.recommendations_file, cache_data)
            return None

        return cached_item['data']



    def get_all_cached_trip_plans(self, user_id: int) -> Dict[str, Any]:
        """Get all cached trip plans for a user."""
        cache_data = self._load_cache(self.trip_plans_file)
        user_plans = {}

        for cache_key, cached_item in cache_data.items():
            if cache_key.startswith(f"{user_id}_"):
                expires_at = datetime.fromisoformat(cached_item['expires_at'])
                if datetime.now() <= expires_at:
                    plan_id = cached_item['plan_id']
                    user_plans[str(plan_id)] = cached_item['data']

        return user_plans

    def clear_expired_cache(self):
        """Clear all expired cache entries."""
        current_time = datetime.now()

        # Clear expired trip plans
        cache_data = self._load_cache(self.trip_plans_file)
        valid_cache = {}
        for cache_key, cached_item in cache_data.items():
            expires_at = datetime.fromisoformat(cached_item['expires_at'])
            if current_time <= expires_at:
                valid_cache[cache_key] = cached_item
        self._save_cache(self.trip_plans_file, valid_cache)

        # Clear expired recommendations
        cache_data = self._load_cache(self.recommendations_file)
        valid_cache = {}
        for cache_key, cached_item in cache_data.items():
            expires_at = datetime.fromisoformat(cached_item['expires_at'])
            if current_time <= expires_at:
                valid_cache[cache_key] = cached_item
        self._save_cache(self.recommendations_file, valid_cache)

        logger.info("Cleared expired cache entries")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        trip_plans = self._load_cache(self.trip_plans_file)
        recommendations = self._load_cache(self.recommendations_file)

        return {
            'trip_plans_count': len(trip_plans),
            'recommendations_count': len(recommendations),
            'total_cached_items': len(trip_plans) + len(recommendations)
        }
