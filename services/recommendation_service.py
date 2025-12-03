import math
import logging
from typing import List, Dict, Optional, Tuple
from models import Destination, db
from sqlalchemy import func, or_, and_

logger = logging.getLogger(__name__)

# Import OpenRouteService for route information
try:
    from services.openroute_service import OpenRouteService
    OPENROUTE_AVAILABLE = True
except ImportError:
    OPENROUTE_AVAILABLE = False
    logger.warning("OpenRouteService not available for route enhancement")

class RecommendationService:
    """Service for recommending destinations based on user preferences and criteria."""

    # Earth's radius in kilometers
    EARTH_RADIUS_KM = 6371

    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula."""
        # Convert to radians
        lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
        lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return RecommendationService.EARTH_RADIUS_KM * c

    @staticmethod
    def calculate_transportation_cost(distance_km: float) -> Dict[str, float]:
        """
        Calculate transportation costs based on distance with realistic pricing tiers.
        
        Args:
            distance_km: Distance in kilometers
            
        Returns:
            Dictionary with different transportation options and costs
        """
        costs = {}
        
        if distance_km < 50:
            # Local travel - bus/taxi
            costs['bus'] = round(distance_km * 0.50, 2)  # $0.50/km
            costs['taxi'] = round(distance_km * 1.50, 2)  # $1.50/km
            costs['recommended'] = costs['bus']
        elif distance_km < 300:
            # Regional travel - bus/train
            costs['bus'] = round(50 + (distance_km - 50) * 0.15, 2)
            costs['train'] = round(40 + (distance_km - 50) * 0.20, 2)
            costs['taxi'] = round(distance_km * 1.20, 2)
            costs['recommended'] = costs['bus']
        elif distance_km < 1000:
            # Medium distance - train/budget flight
            costs['train'] = round(80 + (distance_km - 300) * 0.12, 2)
            costs['budget_flight'] = round(100 + (distance_km - 300) * 0.25, 2)
            costs['standard_flight'] = round(150 + (distance_km - 300) * 0.35, 2)
            costs['recommended'] = costs['budget_flight']
        elif distance_km < 3000:
            # Long distance - flights
            costs['budget_flight'] = round(250 + (distance_km - 1000) * 0.15, 2)
            costs['standard_flight'] = round(400 + (distance_km - 1000) * 0.20, 2)
            costs['premium_flight'] = round(800 + (distance_km - 1000) * 0.30, 2)
            costs['recommended'] = costs['budget_flight']
        else:
            # International/Very long distance
            costs['budget_flight'] = round(550 + (distance_km - 3000) * 0.08, 2)
            costs['standard_flight'] = round(900 + (distance_km - 3000) * 0.12, 2)
            costs['business_flight'] = round(2000 + (distance_km - 3000) * 0.25, 2)
            costs['recommended'] = costs['budget_flight']
            
        return costs

    @staticmethod
    def calculate_comprehensive_budget(
        distance_km: float,
        duration_days: int,
        destination_daily_cost: float,
        budget_tier: Optional[str] = 'mid-range'
    ) -> Dict[str, float]:
        """
        Calculate comprehensive trip budget including all major expenses.
        
        Args:
            distance_km: Distance to destination
            duration_days: Trip duration in days
            destination_daily_cost: Average daily cost at destination
            budget_tier: Budget category (budget/mid-range/luxury)
            
        Returns:
            Dictionary with detailed cost breakdown
        """
        # Transportation costs (round trip)
        transport_costs = RecommendationService.calculate_transportation_cost(distance_km)
        transport_total = transport_costs['recommended'] * 2  # Round trip
        
        # Accommodation costs vary by tier
        accommodation_multiplier = {
            'budget': 0.6,
            'mid-range': 1.0,
            'luxury': 2.5
        }.get(budget_tier, 1.0)
        
        accommodation_per_night = destination_daily_cost * 0.4 * accommodation_multiplier
        accommodation_total = accommodation_per_night * duration_days
        
        # Food costs
        food_multiplier = {
            'budget': 0.7,
            'mid-range': 1.0,
            'luxury': 2.0
        }.get(budget_tier, 1.0)
        
        food_per_day = destination_daily_cost * 0.35 * food_multiplier
        food_total = food_per_day * duration_days
        
        # Local transportation (at destination)
        local_transport_per_day = destination_daily_cost * 0.15 * accommodation_multiplier
        local_transport_total = local_transport_per_day * duration_days
        
        # Activities and entertainment
        activities_per_day = destination_daily_cost * 0.10
        activities_total = activities_per_day * duration_days
        
        # Miscellaneous (shopping, tips, etc.)
        misc_total = (food_total + activities_total) * 0.15
        
        # Travel insurance (approximately 5% of total trip cost)
        subtotal = transport_total + accommodation_total + food_total + local_transport_total + activities_total + misc_total
        insurance = subtotal * 0.05
        
        # Total with contingency buffer (10%)
        total_before_contingency = subtotal + insurance
        contingency = total_before_contingency * 0.10
        grand_total = total_before_contingency + contingency
        
        return {
            'transportation': round(transport_total, 2),
            'transportation_options': transport_costs,
            'accommodation': round(accommodation_total, 2),
            'accommodation_per_night': round(accommodation_per_night, 2),
            'food': round(food_total, 2),
            'food_per_day': round(food_per_day, 2),
            'local_transport': round(local_transport_total, 2),
            'activities': round(activities_total, 2),
            'miscellaneous': round(misc_total, 2),
            'insurance': round(insurance, 2),
            'contingency': round(contingency, 2),
            'subtotal': round(subtotal, 2),
            'total': round(grand_total, 2),
            'per_day_average': round(grand_total / duration_days, 2) if duration_days > 0 else 0
        }

    @staticmethod
    def get_recommendations(
        user_lat: Optional[float] = None,
        user_lon: Optional[float] = None,
        budget_min: Optional[float] = None,
        budget_max: Optional[float] = None,
        categories: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        min_rating: Optional[float] = None,
        max_distance_km: Optional[float] = None,
        limit: int = 10,
        sort_by: str = 'popularity',
        user_currency: str = 'USD',
        trip_duration_days: int = 3
    ) -> List[Dict]:
        """
        Get destination recommendations based on criteria.

        Args:
            user_lat: User's latitude for distance calculations
            user_lon: User's longitude for distance calculations
            budget_min: Minimum budget per day
            budget_max: Maximum budget per day
            categories: List of destination categories to filter by
            tags: List of tags to filter by
            min_rating: Minimum rating (1-5)
            max_distance_km: Maximum distance from user location
            limit: Maximum number of recommendations to return
            sort_by: Sort criteria ('popularity', 'rating', 'distance', 'cost')
            user_currency: User's preferred currency code (ISO 4217)

        Returns:
            List of destination dictionaries with recommendation scores
        """
        query = Destination.query

        # Apply filters
        if budget_min is not None:
            query = query.filter(Destination.average_cost_per_day >= budget_min)

        if budget_max is not None:
            query = query.filter(Destination.average_cost_per_day <= budget_max)

        if categories:
            query = query.filter(Destination.category.in_(categories))

        if min_rating is not None:
            query = query.filter(Destination.rating >= min_rating)

        # Tag filtering (comma-separated in database)
        if tags:
            tag_filters = []
            for tag in tags:
                tag_filters.append(Destination.tags.like(f'%{tag}%'))
            if tag_filters:
                query = query.filter(or_(*tag_filters))

        # Get destinations
        destinations = query.all()

        # Calculate recommendations with scores
        recommendations = []

        for dest in destinations:
            score = 0
            distance = None

            # Distance calculation and filtering
            if user_lat is not None and user_lon is not None and dest.latitude and dest.longitude:
                distance = RecommendationService.calculate_distance(
                    user_lat, user_lon, dest.latitude, dest.longitude
                )
                if max_distance_km and distance > max_distance_km:
                    continue
            elif max_distance_km and (not dest.latitude or not dest.longitude):
                # Skip destinations without coordinates if distance filtering is requested
                continue

            # Calculate comprehensive budget breakdown if distance is available
            budget_breakdown = None
            transportation_options = None
            total_trip_cost = None
            
            if distance is not None and dest.average_cost_per_day:
                budget_breakdown = RecommendationService.calculate_comprehensive_budget(
                    distance_km=distance,
                    duration_days=trip_duration_days,
                    destination_daily_cost=dest.average_cost_per_day,
                    budget_tier=dest.budget_tier or 'mid-range'
                )
                transportation_options = budget_breakdown['transportation_options']
                total_trip_cost = budget_breakdown['total']

            # Calculate recommendation score based on multiple factors
            score += (dest.popularity_score or 0) * 0.4  # 40% weight on popularity
            score += (dest.rating or 3.0) * 0.3  # 30% weight on rating
            score += (dest.review_count or 0) * 0.01  # 10% weight on review count
            
            # Affordability score based on total trip cost (if available)
            if total_trip_cost:
                # Normalize cost score (lower cost = higher score)
                # Assume $5000 is expensive for a trip
                affordability_score = max(0, (5000 - total_trip_cost) / 5000) * 5
                score += affordability_score * 0.2  # 20% weight on affordability
            else:
                score += (5.0 - (dest.average_cost_per_day or 100) / 50) * 0.2

            # Distance bonus (closer destinations get higher scores)
            if distance is not None and max_distance_km:
                distance_score = max(0, (max_distance_km - distance) / max_distance_km)
                score += distance_score * 0.1  # 10% weight on distance

            # Create recommendation object with comprehensive details
            recommendation = {
                'id': dest.id,
                'title': dest.title,
                'description': dest.description,
                'category': dest.category,
                'budget_tier': dest.budget_tier,
                'latitude': dest.latitude,
                'longitude': dest.longitude,
                'website': dest.website,
                'country': dest.country,
                'city': dest.city,
                'average_cost_per_day': dest.average_cost_per_day,
                'best_time_to_visit': dest.best_time_to_visit,
                'rating': dest.rating,
                'review_count': dest.review_count,
                'popularity_score': dest.popularity_score,
                'tags': dest.tags.split(',') if dest.tags else [],
                'estimated_duration_hours': dest.estimated_duration_hours,
                'distance_km': round(distance, 1) if distance else None,
                'trip_duration_days': trip_duration_days,
                'currency': user_currency,
                'recommendation_score': round(score, 2),
                'created_at': dest.created_at.isoformat() if dest.created_at else None,
                # Comprehensive budget information
                'budget_breakdown': budget_breakdown,
                'transportation_options': transportation_options,
                'total_trip_cost': total_trip_cost,
                'estimated_cost_per_day': budget_breakdown['per_day_average'] if budget_breakdown else None,
            }

            recommendations.append(recommendation)

        # Sort recommendations
        if sort_by == 'distance' and user_lat and user_lon:
            recommendations.sort(key=lambda x: x['distance_km'] or float('inf'))
        elif sort_by == 'rating':
            recommendations.sort(key=lambda x: x['rating'] or 0, reverse=True)
        elif sort_by == 'cost':
            recommendations.sort(key=lambda x: x['average_cost_per_day'] or float('inf'))
        else:  # popularity (default)
            recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)

        return recommendations[:limit]

    @staticmethod
    def get_similar_destinations(destination_id: int, limit: int = 5) -> List[Dict]:
        """Get destinations similar to the given destination."""
        dest = Destination.query.get(destination_id)
        if not dest:
            return []

        # Find similar destinations based on category and tags
        similar_query = Destination.query.filter(Destination.id != destination_id)

        if dest.category:
            similar_query = similar_query.filter(Destination.category == dest.category)

        if dest.tags:
            # Find destinations with overlapping tags
            tag_filters = []
            for tag in dest.tags.split(','):
                tag = tag.strip()
                if tag:
                    tag_filters.append(Destination.tags.like(f'%{tag}%'))
            if tag_filters:
                similar_query = similar_query.filter(or_(*tag_filters))

        similar_destinations = similar_query.limit(limit).all()

        return [{
            'id': d.id,
            'title': d.title,
            'description': d.description,
            'category': d.category,
            'rating': d.rating,
            'average_cost_per_day': d.average_cost_per_day,
            'tags': d.tags.split(',') if d.tags else []
        } for d in similar_destinations]

    @staticmethod
    def get_trending_destinations(limit: int = 10) -> List[Dict]:
        """Get trending destinations based on popularity and recent activity."""
        destinations = Destination.query.filter(
            Destination.popularity_score > 0
        ).order_by(Destination.popularity_score.desc()).limit(limit).all()

        return [{
            'id': dest.id,
            'title': dest.title,
            'description': dest.description,
            'category': dest.category,
            'rating': dest.rating,
            'popularity_score': dest.popularity_score,
            'review_count': dest.review_count,
            'tags': dest.tags.split(',') if dest.tags else []
        } for dest in destinations]

    @staticmethod
    def get_destinations_by_budget_range(min_budget: float, max_budget: float, limit: int = 10) -> List[Dict]:
        """Get destinations within a specific budget range."""
        destinations = Destination.query.filter(
            and_(
                Destination.average_cost_per_day >= min_budget,
                Destination.average_cost_per_day <= max_budget
            )
        ).order_by(Destination.rating.desc()).limit(limit).all()

        return [{
            'id': dest.id,
            'title': dest.title,
            'description': dest.description,
            'category': dest.category,
            'average_cost_per_day': dest.average_cost_per_day,
            'rating': dest.rating,
            'budget_tier': dest.budget_tier
        } for dest in destinations]

    @staticmethod
    def update_popularity_scores():
        """Update popularity scores for all destinations based on various factors."""
        destinations = Destination.query.all()

        for dest in destinations:
            # Calculate popularity based on rating, review count, and recency
            base_score = (dest.rating or 3.0) * 0.5
            review_score = min((dest.review_count or 0) / 100, 1.0) * 0.3  # Cap at 100 reviews
            recency_score = 0.2  # Could be based on creation date or last activity

            dest.popularity_score = base_score + review_score + recency_score

        db.session.commit()
        return len(destinations)
