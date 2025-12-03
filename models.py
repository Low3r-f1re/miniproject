from datetime import datetime
from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    preferred_language = db.Column(db.String(10), default='en')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reset_token = db.Column(db.String(255), nullable=True, unique=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)
    
    # Location fields for accurate budget calculations
    home_city = db.Column(db.String(100), nullable=True)
    home_country = db.Column(db.String(100), nullable=True)
    home_latitude = db.Column(db.Float, nullable=True)
    home_longitude = db.Column(db.Float, nullable=True)
    currency_code = db.Column(db.String(3), default='USD')  # ISO 4217 currency code

    # Relationships
    trip_plans = db.relationship('TripPlan', backref='creator', lazy=True)
    trip_participants = db.relationship('TripParticipant', backref='user', lazy=True)

    def __repr__(self):
        return f"<User {self.email}>"

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

class Destination(db.Model):
    __tablename__ = 'destinations'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=True)
    budget_tier = db.Column(db.String(30), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    website = db.Column(db.String(255), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    # New fields for recommendations
    average_cost_per_day = db.Column(db.Float, nullable=True)  # Average daily cost in USD
    best_time_to_visit = db.Column(db.String(100), nullable=True)  # e.g., "March-May, September-November"
    rating = db.Column(db.Float, nullable=True)  # Average rating 1-5
    review_count = db.Column(db.Integer, default=0)
    popularity_score = db.Column(db.Float, default=0.0)  # Calculated popularity score
    tags = db.Column(db.Text, nullable=True)  # Comma-separated tags like "beach,adventure,culture"
    estimated_duration_hours = db.Column(db.Float, nullable=True)  # Typical visit duration
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    restaurants = db.relationship('Restaurant', backref='destination', lazy=True)
    trip_activities = db.relationship('TripActivity', backref='destination', lazy=True)

    def __repr__(self):
        return f"<Destination {self.title}>"

class Restaurant(db.Model):
    __tablename__ = 'restaurants'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    cuisine_type = db.Column(db.String(100), nullable=True)
    price_range = db.Column(db.String(20), nullable=True)  # $, $$, $$$, $$$$
    rating = db.Column(db.Float, nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    address = db.Column(db.Text, nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    website = db.Column(db.String(255), nullable=True)
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id'), nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Restaurant {self.name}>"

class TripPlan(db.Model):
    __tablename__ = 'trip_plans'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    budget = db.Column(db.Float, nullable=True)
    max_participants = db.Column(db.Integer, default=1)
    is_collaborative = db.Column(db.Boolean, default=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    participants = db.relationship('TripParticipant', backref='trip_plan', lazy=True, cascade='all, delete-orphan')
    activities = db.relationship('TripActivity', backref='trip_plan', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<TripPlan {self.title}>"

class TripParticipant(db.Model):
    __tablename__ = 'trip_participants'
    id = db.Column(db.Integer, primary_key=True)
    trip_plan_id = db.Column(db.Integer, db.ForeignKey('trip_plans.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(50), default='participant')  # creator, participant, viewer
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('trip_plan_id', 'user_id', name='unique_trip_participant'),)

    def __repr__(self):
        return f"<TripParticipant {self.user_id} in {self.trip_plan_id}>"

class TripActivity(db.Model):
    __tablename__ = 'trip_activities'
    id = db.Column(db.Integer, primary_key=True)
    trip_plan_id = db.Column(db.Integer, db.ForeignKey('trip_plans.id'), nullable=False)
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    activity_date = db.Column(db.Date, nullable=True)
    start_time = db.Column(db.Time, nullable=True)
    end_time = db.Column(db.Time, nullable=True)
    cost = db.Column(db.Float, nullable=True)
    category = db.Column(db.String(50), nullable=True)  # sightseeing, dining, accommodation, transport
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<TripActivity {self.title}>"

class TranslationCache(db.Model):
    __tablename__ = 'translation_cache'
    id = db.Column(db.Integer, primary_key=True)
    source_text = db.Column(db.Text, nullable=False)
    translated_text = db.Column(db.Text, nullable=False)
    source_lang = db.Column(db.String(10), nullable=False)
    target_lang = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('source_text', 'source_lang', 'target_lang', name='unique_translation'),)

    def __repr__(self):
        return f"<Translation {self.source_lang}->{self.target_lang}>"


class SearchHistory(db.Model):
    __tablename__ = 'search_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    search_type = db.Column(db.String(50), nullable=False)  # 'trip_plan', 'restaurant', 'destination'
    search_term = db.Column(db.String(200), nullable=False)
    search_params = db.Column(db.JSON, nullable=True)
    results_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
