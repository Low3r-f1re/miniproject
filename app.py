import os
import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_babel import Babel, gettext as _
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError, OperationalError
from dotenv import load_dotenv
from itsdangerous import SignatureExpired, BadSignature
# from flask_limiter import Limiter
# from flask_limiter.util import get_remote_address
# from flask_migrate import Migrate

from config import Config
from extensions import db, login_manager, init_extensions
from models import User, Destination, TripPlan, TripParticipant, TripActivity
from services.recommendation_service import RecommendationService
from services.gemini_service import GeminiService
from services.openrouter_service import OpenRouterService
from services.image_service import ImageService
from services.cost_calculation_service import CostCalculationService
from services.openroute_service import OpenRouteService
from utils.security import get_token_serializer, generate_reset_token, verify_reset_token, is_password_strong, validate_email_address

def create_app(config_name=None):
    """Application factory function"""
    # Load environment variables from .env file if it exists
    load_dotenv()
    
    # Initialize Flask app
    app = Flask(__name__,
               static_folder='static',
               template_folder='templates')
    
    # Configure the app
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    # Load the appropriate configuration
    try:
        app.config.from_object(f'config.{config_name.capitalize()}Config')
    except (ImportError, AttributeError):
        app.logger.warning(f'No specific configuration for {config_name}, using default')
        from config import config
        app.config.from_object(config['default'])
    
    # Initialize extensions
    app = init_extensions(app)
    
    # Initialize rate limiter
    # limiter = Limiter(
    #     app=app,
    #     key_func=get_remote_address,
    #     default_limits=app.config.get('RATELIMIT_DEFAULT', '200 per day;50 per hour').split(';')
    # )
    
    # Initialize Babel for internationalization
    babel = Babel()
    babel.init_app(app)
    
    # Make token_serializer available in templates
    app.jinja_env.globals['token_serializer'] = get_token_serializer
    
    # Initialize the application
    app.config['CONFIG_NAME'] = config_name
    app.logger.info(f'Starting application in {config_name} mode')

    def get_locale():
        # Check if language is set in session
        lang = session.get('language')
        if lang and lang in app.config['BABEL_SUPPORTED_LOCALES']:
            return lang
        # Otherwise, try to guess from browser
        return request.accept_languages.best_match(app.config['BABEL_SUPPORTED_LOCALES']) or app.config['BABEL_DEFAULT_LOCALE']

    # Set localeselector on the app
    app.babel_localeselector = get_locale

    # Create database tables
    with app.app_context():
        try:
            # Create tables if they don't exist (safe for production)
            db.create_all()
            print("Database tables created successfully")
        except Exception as e:
            print(f"Database initialization error: {e}")

    # User loader
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Routes
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/signup')
    def signup_page():
        return render_template('signup.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            user = User.query.filter_by(email=email).first()

            if user and check_password_hash(user.password_hash, password):
                # Login the user
                login_user(user)
                return redirect(url_for('index'))
            else:
                flash('Invalid email or password', 'error')
                return redirect(url_for('login'))

        return render_template('login.html')

    @app.route('/destinations')
    @login_required
    def destinations_page():
        return render_template('destinations.html')

    @app.route('/recommendations')
    @login_required
    def recommendations_page():
        return render_template('recommendations.html')

    @app.route('/settings')
    @login_required
    def settings_page():
        return render_template('settings.html')

    @app.route('/api/me')
    def api_me():
        if current_user.is_authenticated:
            return jsonify({
                'authenticated': True, 
                'name': current_user.name, 
                'email': current_user.email,
                'home_city': current_user.home_city,
                'home_country': current_user.home_country,
                'home_latitude': current_user.home_latitude,
                'home_longitude': current_user.home_longitude,
                'currency_code': current_user.currency_code
            }), 200
        return jsonify({'authenticated': False}), 200

    @app.route('/api/config')
    def api_config():
        """Provide frontend configuration (Google Maps removed - using Leaflet + OpenRouteService)"""
        return jsonify({
            'realtimeUrl': os.environ.get('REALTIME_WS_URL', '')
        }), 200

    @app.route('/registration')
    def registration_page():
        return render_template('registration.html')

    @app.route('/api/login', methods=['POST'])
    def api_login():
        # Accept JSON (fetch) or form-encoded submissions
        if request.is_json:
            data = request.get_json(force=True, silent=True) or {}
            email = (data.get('email') or '').strip().lower()
            password = data.get('password') or ''
        else:
            email = (request.form.get('email') or '').strip().lower()
            password = request.form.get('password') or ''

        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400

        try:
            user = User.query.filter_by(email=email).first()
        except Exception as e:
            app.logger.exception('Database error during login lookup')
            return jsonify({'error': 'Database error: ' + str(e)}), 500

        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({'error': 'Invalid email or password'}), 401

        login_user(user)
        return jsonify({'message': 'Login successful'}), 200

    @app.route('/forgot-password', methods=['GET', 'POST'])
    # @limiter.limit("5 per hour")  # Rate limit to 5 requests per hour per IP
    def forgot_password():
        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()

            # Validate email format
            is_valid, email_or_error = validate_email_address(email)
            if not is_valid:
                flash(_(f'Invalid email address: {email_or_error}'), 'error')
                return redirect(url_for('forgot_password'))
                
            email = email_or_error  # Use normalized email

            try:
                user = User.query.filter_by(email=email).first()
                
                # Always return success message, even if email doesn't exist (security best practice)
                if user:
                    # Generate a secure token that expires in 1 hour
                    reset_token = generate_reset_token(email)
                    
                    # Store token hash in database (not the actual token)
                    user.reset_token = generate_password_hash(reset_token)
                    user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
                    db.session.commit()
                    
                    # In a real app, you would send an email here with the reset link
                    # For now, we'll just log it and redirect with the token in the URL (for testing)
                    reset_url = url_for('reset_password', token=reset_token, _external=True)
                    
                    # Log the reset URL (remove this in production)
                    app.logger.info(f'Password reset URL for {email}: {reset_url}')
                    
                    # In production, you would send an email here
                    # send_password_reset_email(user.email, reset_url)
                    
                    flash(_('If an account exists with that email, you will receive password reset instructions.'), 'info')
                else:
                    # Still show success message even if email doesn't exist (security best practice)
                    flash(_('If an account exists with that email, you will receive password reset instructions.'), 'info')
                
                return redirect(url_for('login'))
                
            except Exception as e:
                app.logger.exception('Error in forgot password')
                db.session.rollback()
                flash(_('An error occurred. Please try again later.'), 'error')
                return redirect(url_for('forgot_password'))

        return render_template('forgot_password.html')

    @app.route('/reset-password/<token>', methods=['GET', 'POST'])
    # @limiter.limit("5 per hour")  # Rate limit to 5 requests per hour per IP
    def reset_password(token):
        # For GET requests, just show the form with the token
        if request.method == 'GET':
            return render_template('reset_password.html', token=token)
        
        # For POST requests, process the password reset
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Basic validation
        if not token:
            flash(_('Invalid reset token'), 'error')
            return redirect(url_for('forgot_password'))
        
        # Validate password strength
        is_strong, strength_message = is_password_strong(password)
        if not is_strong:
            flash(_(f'Password is not strong enough: {strength_message}'), 'error')
            return render_template('reset_password.html', token=token), 400
            
        if password != confirm_password:
            flash(_('Passwords do not match'), 'error')
            return render_template('reset_password.html', token=token), 400
        
        try:
            # Verify the token and get the email
            email = verify_reset_token(token)
            if not email:
                flash(_('Invalid or expired reset token'), 'error')
                return redirect(url_for('forgot_password'))
            
            # Find user by email
            user = User.query.filter_by(email=email).first()
            if not user or not user.reset_token:
                flash(_('Invalid or expired reset token'), 'error')
                return redirect(url_for('forgot_password'))
                
            # Verify the token hash matches
            if not check_password_hash(user.reset_token, token):
                flash(_('Invalid or expired reset token'), 'error')
                return redirect(url_for('forgot_password'))
                
            # Check if token is expired (redundant check since verify_reset_token checks this)
            if user.reset_token_expires and user.reset_token_expires < datetime.utcnow():
                flash(_('Reset token has expired. Please request a new one.'), 'error')
                return redirect(url_for('forgot_password'))
            
            # Update password and clear reset token
            user.set_password(password)
            user.reset_token = None
            user.reset_token_expires = None
            db.session.commit()
            
            # Log the successful password reset
            app.logger.info(f'Password reset successful for user: {user.email}')
            
            flash(_('Password reset successful! You can now log in with your new password.'), 'success')
            return redirect(url_for('login'))
            
        except SignatureExpired:
            flash(_('Reset token has expired. Please request a new one.'), 'error')
            return redirect(url_for('forgot_password'))
            
        except Exception as e:
            app.logger.exception('Error resetting password')
            flash(_('An error occurred while resetting your password. Please try again.'), 'error')
            return redirect(url_for('forgot_password'))

    @app.route('/logout')
    def logout():
        logout_user()
        return redirect(url_for('index'))

    @app.route('/api/logout', methods=['POST'])
    def api_logout():
        logout_user()
        return jsonify({'message': 'Logged out'}), 200

    @app.route('/set_language/<lang>')
    def set_language(lang):
        if lang in app.config['BABEL_SUPPORTED_LOCALES']:
            session['language'] = lang
        return redirect(request.referrer or url_for('index'))

    @app.route('/set_language', methods=['POST'])
    def set_language_post():
        lang = request.form.get('language')
        if lang in app.config['BABEL_SUPPORTED_LOCALES']:
            session['language'] = lang
        return redirect(request.referrer or url_for('index'))

    @app.route('/api/check-email', methods=['POST'])
    def api_check_email():
        """Check if an email is already registered"""
        data = request.get_json(force=True, silent=True) or {}
        email = (data.get('email') or '').strip().lower()

        if not email:
            return jsonify({'error': 'Email is required'}), 400

        try:
            existing = User.query.filter_by(email=email).first()
            if existing:
                return jsonify({'exists': True, 'message': 'This email is already registered'}), 200
            else:
                return jsonify({'exists': False, 'message': 'Email is available'}), 200
        except Exception as e:
            app.logger.exception('Error checking email')
            return jsonify({'error': 'Could not check email availability'}), 500

    @app.route('/api/signup', methods=['POST'])
    def api_signup():
        # Try to parse JSON first (works for fetch/curl). Fall back to form data.
        # Debug logging removed to avoid logging sensitive data (raw request body)

        data = request.get_json(force=True, silent=True) or {}
        if data:
            name = (data.get('name') or '').strip()
            email = (data.get('email') or '').strip().lower()
            password = data.get('password') or ''
            confirm_password = data.get('confirmpassword') or ''
        else:
            # fallback for normal form submissions
            name = (request.form.get('name') or '').strip()
            email = (request.form.get('email') or '').strip().lower()
            password = request.form.get('password') or ''
            confirm_password = request.form.get('confirmpassword') or ''

        if not name or not email or len(password) < 6:
            return jsonify({'error': 'Invalid signup data — name, email, and password (>=6) required.'}), 400

        if password != confirm_password:
            return jsonify({'error': 'Passwords do not match'}), 400

        try:
            # Check for existing user
            existing = User.query.filter_by(email=email).first()
        except OperationalError as e:
            # Likely DB connection/config error
            app.logger.exception('Database operational error during signup lookup')
            return jsonify({'error': 'Database connection error: ' + str(e)}), 500
        except Exception as e:
            app.logger.exception('Unexpected error during signup lookup')
            return jsonify({'error': 'Database error: ' + str(e)}), 500

        if existing:
            return jsonify({'error': 'Email already registered'}), 409

        try:
            user = User(name=name, email=email)
            # Use model helper to hash password
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            # Log the user in immediately after successful signup
            try:
                login_user(user)
            except Exception:
                # If login fails for any reason, continue — user was still created
                app.logger.exception('Failed to login user after signup')

            app.logger.info('Created new user: %s', email)
            return jsonify({'message': 'Signup successful', 'email': user.email, 'name': user.name}), 201
        except IntegrityError as ie:
            # Unique constraint failed
            db.session.rollback()
            app.logger.exception('IntegrityError creating user')
            return jsonify({'error': 'Email already registered (integrity)'}), 409
        except OperationalError as oe:
            db.session.rollback()
            app.logger.exception('OperationalError on user create')
            return jsonify({'error': 'Database connection error: ' + str(oe)}), 500
        except Exception as e:
            try:
                db.session.rollback()
            except Exception:
                pass
            app.logger.exception('Unexpected error creating user')
            return jsonify({'error': 'Could not create user: ' + str(e)}), 500

    @app.route('/submit_registration', methods=['POST'])
    def submit_registration():
        firstname = request.form.get('firstname', '').strip()
        lastname = request.form.get('lastname', '').strip()
        email = request.form.get('emailid', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirmpassword', '')

        # Basic validation
        if not firstname or not email or not password:
            flash('All required fields must be filled.', 'error')
            return redirect(url_for('registration_page'))

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('registration_page'))

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return redirect(url_for('registration_page'))

        # Check for existing user
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('An account with this email already exists.', 'error')
            return redirect(url_for('registration_page'))

        # Create new user
        name = f"{firstname} {lastname}".strip()
        user = User(name=name, email=email)
        user.set_password(password)

        try:
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash('Account created successfully! Welcome to TourWithMe.', 'success')
            return redirect(url_for('index'))
        except IntegrityError:
            db.session.rollback()
            flash('An error occurred while creating your account. Please try again.', 'error')
            return redirect(url_for('registration_page'))
        except Exception as e:
            db.session.rollback()
            app.logger.exception('Error creating user via form')
            flash('An unexpected error occurred. Please try again.', 'error')
            return redirect(url_for('registration_page'))

    @app.route('/api/destinations', methods=['GET', 'POST'])
    @login_required
    def api_destinations():
        if request.method == 'GET':
            try:
                dests = Destination.query.order_by(Destination.created_at.desc()).all()
                out = [
                    {
                        'id': d.id,
                        'title': d.title,
                        'description': d.description,
                        'website': d.website,
                        'category': d.category,
                        'budget_tier': d.budget_tier,
                        'latitude': d.latitude,
                        'longitude': d.longitude,
                        'average_cost_per_day': d.average_cost_per_day,
                        'best_time_to_visit': d.best_time_to_visit,
                        'rating': d.rating,
                        'review_count': d.review_count,
                        'popularity_score': d.popularity_score,
                        'tags': d.tags.split(',') if d.tags else [],
                        'estimated_duration_hours': d.estimated_duration_hours,
                        'country': d.country,
                        'city': d.city,
                        'created_at': d.created_at.isoformat() if d.created_at else None
                    } for d in dests
                ]
                return jsonify(out), 200
            except Exception as e:
                app.logger.exception('Error fetching destinations')
                return jsonify({'error': 'Database error: ' + str(e)}), 500

        # POST - create a destination
        data = request.get_json(force=True, silent=True) or {}
        title = (data.get('title') or '').strip()
        description = (data.get('description') or '').strip()
        website = (data.get('website') or '').strip()
        category = (data.get('category') or '').strip()
        budget_tier = (data.get('budget_tier') or '').strip()
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        country = (data.get('country') or '').strip()
        city = (data.get('city') or '').strip()
        average_cost_per_day = data.get('average_cost_per_day')
        best_time_to_visit = (data.get('best_time_to_visit') or '').strip()
        rating = data.get('rating')
        review_count = data.get('review_count', 0)
        tags = (data.get('tags') or '').strip()
        estimated_duration_hours = data.get('estimated_duration_hours')

        if not title:
            return jsonify({'error': 'Title is required'}), 400

        try:
            dest = Destination(
                title=title,
                description=description or None,
                website=website or None,
                category=category or None,
                budget_tier=budget_tier or None,
                latitude=latitude,
                longitude=longitude,
                country=country or None,
                city=city or None,
                average_cost_per_day=average_cost_per_day,
                best_time_to_visit=best_time_to_visit or None,
                rating=rating,
                review_count=review_count,
                tags=tags or None,
                estimated_duration_hours=estimated_duration_hours
            )
            db.session.add(dest)
            db.session.commit()
            return jsonify({'message': 'Destination created', 'id': dest.id}), 201
        except Exception as e:
            try:
                db.session.rollback()
            except Exception:
                pass
            app.logger.exception('Error creating destination')
            return jsonify({'error': 'Could not create destination: ' + str(e)}), 500

    @app.route('/api/destinations/<int:dest_id>', methods=['DELETE'])
    def api_delete_destination(dest_id):
        try:
            dest = Destination.query.get(dest_id)
            if not dest:
                return jsonify({'error': 'Not found'}), 404
            db.session.delete(dest)
            db.session.commit()
            return jsonify({'message': 'Deleted'}), 200
        except Exception as e:
            app.logger.exception('Error deleting destination')
            return jsonify({'error': 'Could not delete: ' + str(e)}), 500

    @app.route('/api/destinations/<int:dest_id>', methods=['PUT'])
    def api_update_destination(dest_id):
        # Update an existing destination (JSON body expected)
        data = request.get_json(force=True, silent=True) or {}
        try:
            dest = Destination.query.get(dest_id)
            if not dest:
                return jsonify({'error': 'Not found'}), 404

            # Allowed fields
            allowed_fields = [
                'title', 'description', 'website', 'category', 'budget_tier',
                'latitude', 'longitude', 'country', 'city', 'average_cost_per_day',
                'best_time_to_visit', 'rating', 'review_count', 'tags', 'estimated_duration_hours'
            ]

            for field in allowed_fields:
                if field in data:
                    val = data.get(field)
                    # coerce empty strings to None for nullable fields
                    if isinstance(val, str) and val.strip() == '':
                        val = None
                    setattr(dest, field, val)

            db.session.add(dest)
            db.session.commit()

            return jsonify({'message': 'Updated', 'id': dest.id,
                            'title': dest.title, 'description': dest.description,
                            'website': dest.website, 'category': dest.category,
                            'budget_tier': dest.budget_tier, 'latitude': dest.latitude,
                            'longitude': dest.longitude, 'country': dest.country,
                            'city': dest.city, 'average_cost_per_day': dest.average_cost_per_day,
                            'best_time_to_visit': dest.best_time_to_visit, 'rating': dest.rating,
                            'review_count': dest.review_count, 'tags': dest.tags,
                            'estimated_duration_hours': dest.estimated_duration_hours}), 200
        except Exception as e:
            try:
                db.session.rollback()
            except Exception:
                pass
            app.logger.exception('Error updating destination')
            return jsonify({'error': 'Could not update: ' + str(e)}), 500

    @app.route('/api/user/location', methods=['PUT'])
    @login_required
    def api_update_user_location():
        """Update user's home location for accurate budget calculations"""
        try:
            data = request.get_json(force=True, silent=True) or {}
            
            # Update location fields
            if 'home_city' in data:
                current_user.home_city = data['home_city'].strip() if data['home_city'] else None
            if 'home_country' in data:
                current_user.home_country = data['home_country'].strip() if data['home_country'] else None
            if 'home_latitude' in data:
                current_user.home_latitude = float(data['home_latitude']) if data['home_latitude'] else None
            if 'home_longitude' in data:
                current_user.home_longitude = float(data['home_longitude']) if data['home_longitude'] else None
            if 'currency_code' in data:
                currency = data['currency_code'].strip().upper() if data['currency_code'] else 'USD'
                # Basic validation for currency code (should be 3 letters)
                if len(currency) == 3 and currency.isalpha():
                    current_user.currency_code = currency
            
            db.session.commit()
            
            return jsonify({
                'message': 'Location updated successfully',
                'home_city': current_user.home_city,
                'home_country': current_user.home_country,
                'home_latitude': current_user.home_latitude,
                'home_longitude': current_user.home_longitude,
                'currency_code': current_user.currency_code
            }), 200
            
        except Exception as e:
            db.session.rollback()
            app.logger.exception('Error updating user location')
            return jsonify({'error': 'Could not update location: ' + str(e)}), 500

    @app.route('/api/recommendations', methods=['GET'])
    @login_required
    def api_recommendations():
        try:
            # Parse query parameters
            user_lat = request.args.get('user_lat', type=float)
            user_lon = request.args.get('user_lon', type=float)
            budget_min = request.args.get('budget_min', type=float)
            budget_max = request.args.get('budget_max', type=float)
            categories = request.args.get('categories')
            tags = request.args.get('tags')
            min_rating = request.args.get('min_rating', type=float)
            max_distance_km = request.args.get('max_distance_km', type=float)
            limit = request.args.get('limit', 10, type=int)
            sort_by = request.args.get('sort_by', 'popularity')
            trip_duration_days = request.args.get('trip_duration_days', 3, type=int)
            use_user_location = request.args.get('use_user_location', 'true').lower() == 'true'

            # Automatically use user's saved location if not provided and use_user_location is true
            if use_user_location and not user_lat and not user_lon:
                if current_user.home_latitude and current_user.home_longitude:
                    user_lat = current_user.home_latitude
                    user_lon = current_user.home_longitude
                    app.logger.info(f'Using saved location for user {current_user.email}: ({user_lat}, {user_lon})')

            # Parse comma-separated values
            categories_list = categories.split(',') if categories else None
            tags_list = tags.split(',') if tags else None

            # Get user's currency or default to USD
            user_currency = current_user.currency_code if hasattr(current_user, 'currency_code') and current_user.currency_code else 'USD'

            recommendations = RecommendationService.get_recommendations(
                user_lat=user_lat,
                user_lon=user_lon,
                budget_min=budget_min,
                budget_max=budget_max,
                categories=categories_list,
                tags=tags_list,
                min_rating=min_rating,
                max_distance_km=max_distance_km,
                limit=limit,
                sort_by=sort_by,
                user_currency=user_currency,
                trip_duration_days=trip_duration_days
            )

            # Add helpful message if no location is available
            response = {
                'recommendations': recommendations,
                'using_saved_location': bool(use_user_location and user_lat and user_lon),
                'location_info': {
                    'latitude': user_lat,
                    'longitude': user_lon,
                    'city': current_user.home_city if hasattr(current_user, 'home_city') else None,
                    'country': current_user.home_country if hasattr(current_user, 'home_country') else None
                } if user_lat and user_lon else None,
                'currency': user_currency,
                'trip_duration_days': trip_duration_days
            }

            return jsonify(response), 200
        except Exception as e:
            app.logger.exception('Error getting recommendations')
            return jsonify({'error': 'Could not get recommendations: ' + str(e)}), 500

    @app.route('/api/recommendations/trending', methods=['GET'])
    @login_required
    def api_trending_recommendations():
        try:
            limit = request.args.get('limit', 10, type=int)
            recommendations = RecommendationService.get_trending_destinations(limit=limit)
            return jsonify(recommendations), 200
        except Exception as e:
            app.logger.exception('Error getting trending recommendations')
            return jsonify({'error': 'Could not get trending recommendations: ' + str(e)}), 500

    @app.route('/api/recommendations/budget/<float:min_budget>/<float:max_budget>', methods=['GET'])
    @login_required
    def api_budget_recommendations(min_budget, max_budget):
        try:
            limit = request.args.get('limit', 10, type=int)
            recommendations = RecommendationService.get_destinations_by_budget_range(
                min_budget, max_budget, limit=limit
            )
            return jsonify(recommendations), 200
        except Exception as e:
            app.logger.exception('Error getting budget recommendations')
            return jsonify({'error': 'Could not get budget recommendations: ' + str(e)}), 500

    @app.route('/api/recommendations/similar/<int:destination_id>', methods=['GET'])
    @login_required
    def api_similar_recommendations(destination_id):
        try:
            limit = request.args.get('limit', 5, type=int)
            recommendations = RecommendationService.get_similar_destinations(
                destination_id, limit=limit
            )
            return jsonify(recommendations), 200
        except Exception as e:
            app.logger.exception('Error getting similar recommendations')
            return jsonify({'error': 'Could not get similar recommendations: ' + str(e)}), 500

    # Gemini AI-powered routes
    @app.route('/api/trip-plan', methods=['POST'])
    @login_required
    def api_generate_trip_plan():
        """Generate a trip plan using Gemini AI with images"""
        try:
            data = request.get_json(force=True, silent=True) or {}
            destination = (data.get('destination') or '').strip()
            duration_days = data.get('duration_days', 3)
            budget = (data.get('budget') or 'mid-range').strip()
            interests = data.get('interests', [])
            travelers = data.get('travelers', 1)
            start_date = data.get('start_date')

            if not destination:
                return jsonify({'error': 'Destination is required'}), 400

            # Get user's home location - prioritize request body over saved profile
            user_home_city = data.get('user_home_city') or (current_user.home_city if hasattr(current_user, 'home_city') else None)
            user_home_country = data.get('user_home_country') or (current_user.home_country if hasattr(current_user, 'home_country') else None)
            user_latitude = current_user.home_latitude if hasattr(current_user, 'home_latitude') else None
            user_longitude = current_user.home_longitude if hasattr(current_user, 'home_longitude') else None

            # If no coordinates but we have a city name, try to geocode it
            if not user_latitude or not user_longitude:
                if user_home_city:
                    coords = CostCalculationService.geocode_city(user_home_city)
                    if coords:
                        user_latitude, user_longitude = coords
                        app.logger.info(f"Geocoded user city '{user_home_city}' to coordinates: {coords}")

            # Try to get destination coordinates (if destination is in database)
            dest_latitude = None
            dest_longitude = None
            destination_obj = Destination.query.filter(
                db.func.lower(Destination.title).like(f'%{destination.lower()}%')
            ).first()
            if destination_obj:
                dest_latitude = destination_obj.latitude
                dest_longitude = destination_obj.longitude
            
            # If no coordinates from database, try geocoding the destination
            if not dest_latitude or not dest_longitude:
                coords = CostCalculationService.geocode_city(destination)
                if coords:
                    dest_latitude, dest_longitude = coords
                    app.logger.info(f"Geocoded destination '{destination}' to coordinates: {coords}")

            # Calculate realistic costs using CostCalculationService
            calculated_costs = CostCalculationService.calculate_trip_costs(
                destination=destination,
                duration_days=duration_days,
                budget=budget,
                travelers=travelers,
                user_latitude=user_latitude,
                user_longitude=user_longitude,
                dest_latitude=dest_latitude,
                dest_longitude=dest_longitude
            )
            
            app.logger.info(f"Calculated costs for {destination}: {calculated_costs['cost_breakdown']['total']} INR")

            # Try OpenRouter first, fallback to Gemini
            openrouter_service = OpenRouterService(api_key=app.config['OPENROUTER_API_KEY'])
            trip_plan = openrouter_service.generate_trip_plan(
                destination=destination,
                duration_days=duration_days,
                budget=budget,
                interests=interests,
                travelers=travelers,
                start_date=start_date,
                user_home_city=user_home_city,
                user_home_country=user_home_country,
                user_latitude=user_latitude,
                user_longitude=user_longitude,
                dest_latitude=dest_latitude,
                dest_longitude=dest_longitude
            )

            if 'error' in trip_plan:
                # Check if it's a configuration error (expected when Gemini package not installed)
                if 'Gemini API not configured' in trip_plan['error']:
                    return jsonify(trip_plan), 503  # Service Unavailable
                return jsonify(trip_plan), 500

            # Replace AI-generated costs with calculated realistic costs
            trip_plan['estimated_costs'] = calculated_costs['cost_breakdown']
            trip_plan['cost_details'] = {
                'per_person_cost': calculated_costs['per_person_cost'],
                'daily_breakdown': calculated_costs['daily_breakdown'],
                'cost_index': calculated_costs['cost_index'],
                'currency': calculated_costs['currency']
            }
            
            # Add transportation details if available
            if 'transportation_details' in calculated_costs:
                trip_plan['travel_from_home'] = calculated_costs['transportation_details']
                trip_plan['distance_km'] = calculated_costs['distance_km']
            
            # Add cost summary
            trip_plan['cost_summary'] = CostCalculationService.format_cost_summary(calculated_costs)
            
            # Add destination coordinates for route viewing
            trip_plan['destination_latitude'] = dest_latitude
            trip_plan['destination_longitude'] = dest_longitude

            # Add images to the trip plan
            image_service = ImageService()
            
            # Add destination image
            trip_plan['destination_image'] = image_service.get_destination_image(destination)
            
            # Add images to activities
            if 'itinerary' in trip_plan:
                for day in trip_plan['itinerary']:
                    if 'activities' in day and isinstance(day['activities'], list):
                        for activity in day['activities']:
                            if isinstance(activity, dict) and 'name' in activity:
                                activity['image_url'] = image_service.get_activity_image(
                                    activity['name'], 
                                    destination
                                )

            return jsonify(trip_plan), 200
        except Exception as e:
            app.logger.exception('Error generating trip plan')
            return jsonify({'error': 'Could not generate trip plan: ' + str(e)}), 500

    @app.route('/api/restaurant-recommendations', methods=['GET'])
    @login_required
    def api_restaurant_recommendations():
        """Get restaurant recommendations using Gemini AI with relevant images"""
        try:
            location = request.args.get('location', '').strip()
            cuisine_preferences = request.args.get('cuisine')
            budget = request.args.get('budget', 'mid-range')
            dietary_restrictions = request.args.get('dietary_restrictions')
            group_size = request.args.get('group_size', 2, type=int)
            
            # New filters
            meal_type = request.args.get('meal_type', '').strip()
            popularity = request.args.get('popularity', 'all').strip()
            user_lat = request.args.get('user_lat', type=float)
            user_lon = request.args.get('user_lon', type=float)
            max_distance_km = request.args.get('max_distance_km', type=float)

            if not location:
                return jsonify({'error': 'Location is required'}), 400

            cuisine_list = cuisine_preferences.split(',') if cuisine_preferences else None
            dietary_list = dietary_restrictions.split(',') if dietary_restrictions else None
            meal_type_list = meal_type.split(',') if meal_type else None

            # Add user location context to the response
            user_location_context = None
            if current_user.home_city and current_user.home_country:
                user_location_context = {
                    'city': current_user.home_city,
                    'country': current_user.home_country,
                    'is_local': location.lower() in current_user.home_city.lower() if current_user.home_city else False
                }

            # Try OpenRouter first, fallback to Gemini
            openrouter_service = OpenRouterService(api_key=app.config['OPENROUTER_API_KEY'])
            recommendations = openrouter_service.get_restaurant_recommendations(
                location=location,
                cuisine_preferences=cuisine_list,
                budget=budget,
                dietary_restrictions=dietary_list,
                group_size=group_size,
                meal_type=meal_type_list,
                popularity=popularity,
                user_lat=user_lat,
                user_lon=user_lon,
                max_distance_km=max_distance_km
            )

            if 'error' in recommendations:
                # Check if it's a configuration error (expected when Gemini package not installed)
                if 'Gemini API not configured' in recommendations['error']:
                    return jsonify(recommendations), 503  # Service Unavailable
                return jsonify(recommendations), 500

            # Add relevant images to each restaurant recommendation
            image_service = ImageService()
            
            if 'recommendations' in recommendations and isinstance(recommendations['recommendations'], list):
                for restaurant in recommendations['recommendations']:
                    if isinstance(restaurant, dict):
                        # Get restaurant details
                        name = restaurant.get('name', '')
                        cuisine = restaurant.get('cuisine', '')
                        restaurant_type = restaurant.get('type', 'restaurant')
                        
                        # Use the improved get_restaurant_image method
                        # Priority: cuisine-based imagery over generic restaurant photos
                        if cuisine:
                            # Use cuisine for more relevant food imagery
                            restaurant['image_url'] = image_service.get_restaurant_image(
                                restaurant_type=restaurant_type,
                                cuisine=cuisine
                            )
                        elif name:
                            # Fallback to name-based search if no cuisine
                            restaurant['image_url'] = image_service.search_image(f"{name} restaurant {location}")
                        else:
                            # Last resort: location-based restaurant search
                            restaurant['image_url'] = image_service.search_image(f"{location} restaurant food")
                        
                        # Add images for signature dishes if they exist
                        if 'signature_dishes' in restaurant and isinstance(restaurant['signature_dishes'], list):
                            for dish in restaurant['signature_dishes']:
                                if isinstance(dish, dict) and 'name' in dish:
                                    dish_name = dish['name']
                                    # Use cuisine context for dish images
                                    if cuisine:
                                        dish['image_url'] = image_service.search_image(f"{cuisine} {dish_name}")
                                    else:
                                        dish['image_url'] = image_service.search_image(f"{dish_name} food dish")

            # Add user location context to the response
            if user_location_context:
                recommendations['user_location'] = user_location_context

            return jsonify(recommendations), 200
        except Exception as e:
            app.logger.exception('Error getting restaurant recommendations')
            return jsonify({'error': 'Could not get restaurant recommendations: ' + str(e)}), 500

    # Trip planning and collaboration routes
    @app.route('/api/trip-plans', methods=['GET', 'POST'])
    @login_required
    def api_trip_plans():
        if request.method == 'GET':
            try:
                # Get user's trip plans
                trip_plans = TripPlan.query.filter_by(creator_id=current_user.id).all()
                out = []
                for plan in trip_plans:
                    out.append({
                        'id': plan.id,
                        'title': plan.title,
                        'description': plan.description,
                        'start_date': plan.start_date.isoformat() if plan.start_date else None,
                        'end_date': plan.end_date.isoformat() if plan.end_date else None,
                        'budget': plan.budget,
                        'max_participants': plan.max_participants,
                        'is_collaborative': plan.is_collaborative,
                        'created_at': plan.created_at.isoformat(),
                        'participant_count': len(plan.participants)
                    })
                return jsonify(out), 200
            except Exception as e:
                app.logger.exception('Error fetching trip plans')
                return jsonify({'error': 'Database error: ' + str(e)}), 500

        # POST - create a trip plan
        data = request.get_json(force=True, silent=True) or {}
        title = (data.get('title') or '').strip()
        description = (data.get('description') or '').strip()
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        budget = data.get('budget')
        max_participants = data.get('max_participants', 1)
        is_collaborative = data.get('is_collaborative', False)

        if not title:
            return jsonify({'error': 'Title is required'}), 400

        try:
            start_date = datetime.fromisoformat(start_date_str) if start_date_str else None
            end_date = datetime.fromisoformat(end_date_str) if end_date_str else None

            trip_plan = TripPlan(
                title=title,
                description=description or None,
                start_date=start_date,
                end_date=end_date,
                budget=budget,
                max_participants=max_participants,
                is_collaborative=is_collaborative,
                creator_id=current_user.id
            )
            db.session.add(trip_plan)
            db.session.commit()

            # Add creator as participant
            participant = TripParticipant(
                trip_plan_id=trip_plan.id,
                user_id=current_user.id,
                role='creator'
            )
            db.session.add(participant)
            db.session.commit()

            return jsonify({'message': 'Trip plan created', 'id': trip_plan.id}), 201
        except Exception as e:
            try:
                db.session.rollback()
            except Exception:
                pass
            app.logger.exception('Error creating trip plan')
            return jsonify({'error': 'Could not create trip plan: ' + str(e)}), 500

    @app.route('/api/trip-plans/<int:plan_id>', methods=['GET', 'PUT', 'DELETE'])
    @login_required
    def api_trip_plan_detail(plan_id):
        try:
            trip_plan = TripPlan.query.get(plan_id)
            if not trip_plan:
                return jsonify({'error': 'Trip plan not found'}), 404

            # Check if user has access to this plan
            is_participant = any(p.user_id == current_user.id for p in trip_plan.participants)
            if not is_participant:
                return jsonify({'error': 'Access denied'}), 403

        except Exception as e:
            app.logger.exception('Error accessing trip plan')
            return jsonify({'error': 'Database error: ' + str(e)}), 500

        if request.method == 'GET':
            try:
                activities = []
                for activity in trip_plan.activities:
                    activities.append({
                        'id': activity.id,
                        'title': activity.title,
                        'description': activity.description,
                        'activity_date': activity.activity_date.isoformat() if activity.activity_date else None,
                        'start_time': str(activity.start_time) if activity.start_time else None,
                        'end_time': str(activity.end_time) if activity.end_time else None,
                        'cost': activity.cost,
                        'category': activity.category,
                        'latitude': activity.latitude,
                        'longitude': activity.longitude,
                        'created_by': activity.created_by
                    })

                participants = []
                for participant in trip_plan.participants:
                    participants.append({
                        'user_id': participant.user_id,
                        'name': participant.user.name,
                        'email': participant.user.email,
                        'role': participant.role,
                        'joined_at': participant.joined_at.isoformat()
                    })

                plan_data = {
                    'id': trip_plan.id,
                    'title': trip_plan.title,
                    'description': trip_plan.description,
                    'start_date': trip_plan.start_date.isoformat() if trip_plan.start_date else None,
                    'end_date': trip_plan.end_date.isoformat() if trip_plan.end_date else None,
                    'budget': trip_plan.budget,
                    'max_participants': trip_plan.max_participants,
                    'is_collaborative': trip_plan.is_collaborative,
                    'created_at': trip_plan.created_at.isoformat(),
                    'activities': activities,
                    'participants': participants
                }
                return jsonify(plan_data), 200
            except Exception as e:
                app.logger.exception('Error fetching trip plan details')
                return jsonify({'error': 'Could not fetch trip plan details: ' + str(e)}), 500

        elif request.method == 'PUT':
            # Check if user is creator or has edit permissions
            user_role = next((p.role for p in trip_plan.participants if p.user_id == current_user.id), None)
            if user_role not in ['creator', 'editor']:
                return jsonify({'error': 'Insufficient permissions'}), 403

            data = request.get_json(force=True, silent=True) or {}
            try:
                allowed_fields = ['title', 'description', 'start_date', 'end_date', 'budget', 'max_participants', 'is_collaborative']

                for field in allowed_fields:
                    if field in data:
                        val = data.get(field)
                        if field in ['start_date', 'end_date'] and val:
                            val = datetime.fromisoformat(val)
                        setattr(trip_plan, field, val)

                db.session.commit()
                return jsonify({'message': 'Trip plan updated', 'id': trip_plan.id}), 200
            except Exception as e:
                try:
                    db.session.rollback()
                except Exception:
                    pass
                app.logger.exception('Error updating trip plan')
                return jsonify({'error': 'Could not update trip plan: ' + str(e)}), 500

        elif request.method == 'DELETE':
            # Only creator can delete
            if trip_plan.creator_id != current_user.id:
                return jsonify({'error': 'Only creator can delete trip plan'}), 403

            try:
                db.session.delete(trip_plan)
                db.session.commit()
                return jsonify({'message': 'Trip plan deleted'}), 200
            except Exception as e:
                try:
                    db.session.rollback()
                except Exception:
                    pass
                app.logger.exception('Error deleting trip plan')
                return jsonify({'error': 'Could not delete trip plan: ' + str(e)}), 500

    @app.route('/api/trip-plans/<int:plan_id>/invite', methods=['POST'])
    @login_required
    def api_invite_to_trip_plan(plan_id):
        """Invite users to collaborate on a trip plan"""
        try:
            trip_plan = TripPlan.query.get(plan_id)
            if not trip_plan:
                return jsonify({'error': 'Trip plan not found'}), 404

            if trip_plan.creator_id != current_user.id:
                return jsonify({'error': 'Only creator can send invites'}), 403

            data = request.get_json(force=True, silent=True) or {}
            email = (data.get('email') or '').strip().lower()

            if not email:
                return jsonify({'error': 'Email is required'}), 400

            # Check if user exists
            user = User.query.filter_by(email=email).first()
            if not user:
                return jsonify({'error': 'User not found'}), 404

            # Check if already a participant
            existing = TripParticipant.query.filter_by(trip_plan_id=plan_id, user_id=user.id).first()
            if existing:
                return jsonify({'error': 'User is already a participant'}), 409

            # Check participant limit
            if len(trip_plan.participants) >= trip_plan.max_participants:
                return jsonify({'error': 'Maximum participants reached'}), 400

            # Add participant
            participant = TripParticipant(
                trip_plan_id=plan_id,
                user_id=user.id,
                role='participant'
            )
            db.session.add(participant)
            db.session.commit()

            return jsonify({'message': 'User invited successfully'}), 200
        except Exception as e:
            try:
                db.session.rollback()
            except Exception:
                pass
            app.logger.exception('Error inviting user to trip plan')
            return jsonify({'error': 'Could not invite user: ' + str(e)}), 500

    @app.route('/api/trip-plans/<int:plan_id>/enhance', methods=['POST'])
    @login_required
    def api_enhance_trip_plan(plan_id):
        """Enhance trip plan with collaborative preferences using Gemini AI"""
        try:
            trip_plan = TripPlan.query.get(plan_id)
            if not trip_plan:
                return jsonify({'error': 'Trip plan not found'}), 404

            # Check if user has access
            is_participant = any(p.user_id == current_user.id for p in trip_plan.participants)
            if not is_participant:
                return jsonify({'error': 'Access denied'}), 403

            data = request.get_json(force=True, silent=True) or {}
            preferences = data.get('preferences', {})

            # Get participant info for enhancement
            collaborators = [p.user.email for p in trip_plan.participants if p.user_id != current_user.id]

            # Convert trip plan to dict for Gemini
            plan_dict = {
                'title': trip_plan.title,
                'description': trip_plan.description,
                'start_date': trip_plan.start_date.isoformat() if trip_plan.start_date else None,
                'end_date': trip_plan.end_date.isoformat() if trip_plan.end_date else None,
                'budget': trip_plan.budget,
                'activities': [
                    {
                        'title': a.title,
                        'description': a.description,
                        'category': a.category,
                        'cost': a.cost
                    } for a in trip_plan.activities
                ]
            }

            gemini_service = GeminiService()
            enhanced_plan = gemini_service.enhance_collaboration_plan(
                existing_plan=plan_dict,
                collaborators=collaborators,
                preferences=preferences
            )

            if 'error' in enhanced_plan:
                # Check if it's a configuration error (expected when Gemini package not installed)
                if 'Gemini API not configured' in enhanced_plan['error']:
                    return jsonify(enhanced_plan), 503  # Service Unavailable
                return jsonify(enhanced_plan), 500

            return jsonify(enhanced_plan), 200
        except Exception as e:
            app.logger.exception('Error enhancing trip plan')
            return jsonify({'error': 'Could not enhance trip plan: ' + str(e)}), 500

    # OpenRouteService API endpoints
    @app.route('/api/geocode', methods=['GET'])
    @login_required
    def api_geocode():
        """Geocode a location string to coordinates using OpenRouteService"""
        try:
            location = request.args.get('location', '').strip()
            if not location:
                return jsonify({'error': 'Location parameter is required'}), 400
            
            ors = OpenRouteService()
            result = ors.geocode(location)
            
            if not result:
                return jsonify({'error': f'Could not geocode location: {location}'}), 404
            
            return jsonify(result), 200
        except Exception as e:
            app.logger.exception('Error geocoding location')
            return jsonify({'error': f'Could not geocode location: {str(e)}'}), 500

    @app.route('/api/reverse-geocode', methods=['GET'])
    @login_required
    def api_reverse_geocode():
        """Reverse geocode coordinates to address using OpenRouteService"""
        try:
            lat = request.args.get('lat', type=float)
            lon = request.args.get('lon', type=float)
            
            if lat is None or lon is None:
                return jsonify({'error': 'Both lat and lon parameters are required'}), 400
            
            ors = OpenRouteService()
            result = ors.reverse_geocode(lat, lon)
            
            if not result:
                return jsonify({'error': f'Could not reverse geocode coordinates: ({lat}, {lon})'}), 404
            
            return jsonify(result), 200
        except Exception as e:
            app.logger.exception('Error reverse geocoding coordinates')
            return jsonify({'error': f'Could not reverse geocode: {str(e)}'}), 500

    @app.route('/api/directions', methods=['POST'])
    @login_required
    def api_get_directions():
        """Get directions between two points using OpenRouteService"""
        try:
            data = request.get_json(force=True, silent=True) or {}
            
            # Get start and end coordinates with proper type conversion
            try:
                start_lat = float(data.get('start_lat'))
                start_lon = float(data.get('start_lon'))
                end_lat = float(data.get('end_lat'))
                end_lon = float(data.get('end_lon'))
            except (TypeError, ValueError) as e:
                app.logger.error(f'Invalid coordinate values: {e}')
                return jsonify({'error': 'Invalid coordinates provided. All coordinates must be valid numbers.'}), 400
            
            # Validate coordinate ranges
            if not (-90 <= start_lat <= 90) or not (-180 <= start_lon <= 180):
                return jsonify({'error': 'Invalid start coordinates. Latitude must be between -90 and 90, longitude between -180 and 180.'}), 400
            
            if not (-90 <= end_lat <= 90) or not (-180 <= end_lon <= 180):
                return jsonify({'error': 'Invalid end coordinates. Latitude must be between -90 and 90, longitude between -180 and 180.'}), 400
            
            # Optional parameters
            profile = data.get('profile', 'driving-car')
            alternatives = data.get('alternatives', 0)
            language = data.get('language', 'en')
            
            app.logger.info(f'Getting directions from ({start_lat}, {start_lon}) to ({end_lat}, {end_lon}) with profile {profile}')
            
            ors = OpenRouteService()
            result = ors.get_directions(
                start_coords=(start_lat, start_lon),
                end_coords=(end_lat, end_lon),
                profile=profile,
                alternatives=alternatives,
                language=language
            )
            
            if not result:
                return jsonify({'error': 'Could not get directions from OpenRouteService'}), 404
            
            return jsonify(result), 200
        except Exception as e:
            app.logger.exception('Error getting directions')
            return jsonify({'error': f'Could not get directions: {str(e)}'}), 500

    @app.route('/api/isochrones', methods=['POST'])
    @login_required
    def api_get_isochrones():
        """Get isochrones (reachability areas) from a point using OpenRouteService"""
        try:
            data = request.get_json(force=True, silent=True) or {}
            
            # Get center coordinates
            lat = data.get('lat', type=float)
            lon = data.get('lon', type=float)
            
            if lat is None or lon is None:
                return jsonify({'error': 'lat and lon are required'}), 400
            
            # Optional parameters
            profile = data.get('profile', 'driving-car')
            range_type = data.get('range_type', 'time')  # 'time' or 'distance'
            ranges = data.get('ranges', [300, 600, 900])  # seconds or meters
            
            ors = OpenRouteService()
            result = ors.get_isochrones(
                coordinates=(lat, lon),
                profile=profile,
                range_type=range_type,
                ranges=ranges
            )
            
            if not result:
                return jsonify({'error': 'Could not generate isochrones'}), 404
            
            return jsonify(result), 200
        except Exception as e:
            app.logger.exception('Error generating isochrones')
            return jsonify({'error': f'Could not generate isochrones: {str(e)}'}), 500

    @app.route('/api/matrix', methods=['POST'])
    @login_required
    def api_get_matrix():
        """Get distance/duration matrix between multiple locations using OpenRouteService"""
        try:
            data = request.get_json(force=True, silent=True) or {}
            
            # Get locations as list of [lat, lon] pairs
            locations = data.get('locations', [])
            
            if not locations or len(locations) < 2:
                return jsonify({'error': 'At least 2 locations are required'}), 400
            
            # Convert to tuples
            location_tuples = [(loc[0], loc[1]) for loc in locations]
            
            # Optional parameters
            profile = data.get('profile', 'driving-car')
            sources = data.get('sources')
            destinations = data.get('destinations')
            
            ors = OpenRouteService()
            result = ors.get_matrix(
                locations=location_tuples,
                profile=profile,
                sources=sources,
                destinations=destinations
            )
            
            if not result:
                return jsonify({'error': 'Could not generate matrix'}), 404
            
            return jsonify(result), 200
        except Exception as e:
            app.logger.exception('Error generating matrix')
            return jsonify({'error': f'Could not generate matrix: {str(e)}'}), 500

    @app.route('/api/restaurant-directions', methods=['POST'])
    @login_required
    def api_restaurant_directions():
        """Get directions from user location to a restaurant"""
        try:
            data = request.get_json(force=True, silent=True) or {}
            
            # Get user location (can be from saved profile or provided)
            user_lat = data.get('user_lat', type=float)
            user_lon = data.get('user_lon', type=float)
            
            # Use saved location if not provided
            if not user_lat or not user_lon:
                if current_user.home_latitude and current_user.home_longitude:
                    user_lat = current_user.home_latitude
                    user_lon = current_user.home_longitude
                else:
                    return jsonify({'error': 'User location not available. Please set your home location in settings.'}), 400
            
            # Get restaurant location
            restaurant_lat = data.get('restaurant_lat', type=float)
            restaurant_lon = data.get('restaurant_lon', type=float)
            restaurant_address = data.get('restaurant_address', '').strip()
            
            # If no coordinates but address provided, geocode it
            if (not restaurant_lat or not restaurant_lon) and restaurant_address:
                ors = OpenRouteService()
                geocode_result = ors.geocode(restaurant_address)
                if geocode_result:
                    restaurant_lat = geocode_result['latitude']
                    restaurant_lon = geocode_result['longitude']
                else:
                    return jsonify({'error': 'Could not geocode restaurant address'}), 404
            
            if not restaurant_lat or not restaurant_lon:
                return jsonify({'error': 'Restaurant location (coordinates or address) is required'}), 400
            
            # Get directions
            profile = data.get('profile', 'driving-car')
            ors = OpenRouteService()
            directions = ors.get_directions(
                start_coords=(user_lat, user_lon),
                end_coords=(restaurant_lat, restaurant_lon),
                profile=profile,
                alternatives=1
            )
            
            if not directions:
                return jsonify({'error': 'Could not get directions to restaurant'}), 404
            
            # Add formatted summary
            directions['summary_text'] = ors.format_directions_summary(directions)
            
            return jsonify(directions), 200
        except Exception as e:
            app.logger.exception('Error getting restaurant directions')
            return jsonify({'error': f'Could not get restaurant directions: {str(e)}'}), 500

    @app.route('/api/location/autocomplete', methods=['GET'])
    @login_required
    def api_location_autocomplete():
        """Autocomplete city/location search using OpenRouteService Geocode API"""
        try:
            query = request.args.get('query', '').strip()
            
            if not query or len(query) < 2:
                return jsonify({'suggestions': []}), 200
            
            # Use OpenRouteService geocode with higher limit for autocomplete
            ors = OpenRouteService()
            
            # Make geocode request
            url = f"{ors.BASE_URL}/geocode/search"
            params = {
                'text': query,
                'size': 10  # Return up to 10 suggestions
            }
            
            response = requests.get(url, headers=ors.headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Process results into autocomplete format
            suggestions = []
            for feature in data.get('features', []):
                coords = feature['geometry']['coordinates']  # [lon, lat]
                props = feature.get('properties', {})
                
                suggestions.append({
                    'name': props.get('name', ''),
                    'label': props.get('label', query),
                    'latitude': coords[1],
                    'longitude': coords[0],
                    'country': props.get('country', ''),
                    'region': props.get('region', ''),
                    'locality': props.get('locality', ''),
                    'confidence': props.get('confidence', 0)
                })
            
            return jsonify({'suggestions': suggestions}), 200
            
        except Exception as e:
            app.logger.exception('Error in location autocomplete')
            return jsonify({'error': 'Could not fetch autocomplete suggestions', 'suggestions': []}), 500

    @app.route('/api/location/validate', methods=['POST'])
    @login_required
    def api_validate_location():
        """
        Validate location with smart priority:
        1. GPS location (from request)
        2. Saved profile location
        3. Manual input
        Returns error if all three are missing
        """
        try:
            data = request.get_json(force=True, silent=True) or {}
            
            # Priority 1: GPS location from request
            gps_lat = data.get('gps_lat', type=float)
            gps_lon = data.get('gps_lon', type=float)
            
            if gps_lat and gps_lon:
                # Validate GPS coordinates are within valid range
                if -90 <= gps_lat <= 90 and -180 <= gps_lon <= 180:
                    return jsonify({
                        'status': 'success',
                        'source': 'gps',
                        'location': {
                            'latitude': gps_lat,
                            'longitude': gps_lon,
                            'type': 'gps'
                        }
                    }), 200
            
            # Priority 2: Saved profile location
            if current_user.home_latitude and current_user.home_longitude:
                return jsonify({
                    'status': 'success',
                    'source': 'saved_profile',
                    'location': {
                        'latitude': current_user.home_latitude,
                        'longitude': current_user.home_longitude,
                        'city': current_user.home_city,
                        'country': current_user.home_country,
                        'type': 'saved'
                    }
                }), 200
            
            # Priority 3: Manual input
            manual_city = data.get('manual_city', '').strip()
            manual_country = data.get('manual_country', '').strip()
            
            if manual_city:
                # Geocode the manual input
                ors = OpenRouteService()
                search_query = f"{manual_city}, {manual_country}" if manual_country else manual_city
                
                geocode_result = ors.geocode(search_query)
                if geocode_result:
                    return jsonify({
                        'status': 'success',
                        'source': 'manual_input',
                        'location': {
                            'latitude': geocode_result['latitude'],
                            'longitude': geocode_result['longitude'],
                            'city': geocode_result.get('locality', manual_city),
                            'country': geocode_result.get('country', manual_country),
                            'type': 'manual'
                        }
                    }), 200
                else:
                    return jsonify({
                        'status': 'error',
                        'code': 'GEOCODE_FAILED',
                        'message': f'Could not geocode location: {search_query}'
                    }), 400
            
            # All three are missing - return error
            return jsonify({
                'status': 'error',
                'code': 'LOCATION_MISSING',
                'message': 'Location required. Enable GPS or enter manually.'
            }), 400
            
        except Exception as e:
            app.logger.exception('Error validating location')
            return jsonify({
                'status': 'error',
                'code': 'VALIDATION_ERROR',
                'message': f'Could not validate location: {str(e)}'
            }), 500

    @app.route('/api/location/nearest-places', methods=['POST'])
    @login_required
    def api_nearest_places():
        """
        Get nearest places using validated location and ORS Matrix API
        Uses smart validation: GPS → Saved → Manual
        """
        try:
            data = request.get_json(force=True, silent=True) or {}
            
            # Validate and get location using priority order
            validation_response = api_validate_location()
            validation_data = validation_response[0].get_json()
            
            if validation_data.get('status') != 'success':
                return validation_response
            
            user_location = validation_data['location']
            user_lat = user_location['latitude']
            user_lon = user_location['longitude']
            
            # Get parameters
            max_distance_km = data.get('max_distance_km', 50)
            limit = data.get('limit', 10)
            category = data.get('category')
            
            # Get destinations from database
            query = Destination.query
            
            if category:
                query = query.filter(Destination.category == category)
            
            # Get all destinations with coordinates
            all_destinations = query.filter(
                Destination.latitude.isnot(None),
                Destination.longitude.isnot(None)
            ).all()
            
            if not all_destinations:
                return jsonify({
                    'status': 'success',
                    'user_location': user_location,
                    'places': [],
                    'message': 'No destinations found'
                }), 200
            
            # Use ORS Matrix API to calculate distances
            ors = OpenRouteService()
            
            # Prepare locations for matrix API
            locations = [(user_lat, user_lon)]  # User location is first
            for dest in all_destinations[:50]:  # Limit to 50 for API constraints
                locations.append((dest.latitude, dest.longitude))
            
            # Get distance matrix
            matrix_result = ors.get_matrix(
                locations=locations,
                profile='driving-car',
                sources=[0],  # Only from user location
                metrics=['distance', 'duration']
            )
            
            if not matrix_result:
                app.logger.error('Failed to get distance matrix')
                return jsonify({
                    'status': 'error',
                    'code': 'MATRIX_FAILED',
                    'message': 'Could not calculate distances'
                }), 500
            
            # Process results
            places = []
            distances_km = matrix_result.get('distances_km', [[]])[0]  # First row (from user)
            durations_min = matrix_result.get('durations_minutes', [[]])[0]
            
            for i, dest in enumerate(all_destinations[:50]):
                dest_index = i + 1  # +1 because user is at index 0
                
                if dest_index < len(distances_km):
                    distance_km = distances_km[dest_index]
                    duration_min = durations_min[dest_index] if dest_index < len(durations_min) else None
                    
                    # Filter by max distance
                    if distance_km and distance_km <= max_distance_km:
                        places.append({
                            'id': dest.id,
                            'title': dest.title,
                            'description': dest.description,
                            'category': dest.category,
                            'latitude': dest.latitude,
                            'longitude': dest.longitude,
                            'distance_km': round(distance_km, 2),
                            'duration_minutes': round(duration_min, 0) if duration_min else None,
                            'rating': dest.rating,
                            'average_cost_per_day': dest.average_cost_per_day,
                            'tags': dest.tags.split(',') if dest.tags else []
                        })
            
            # Sort by distance and limit results
            places.sort(key=lambda x: x['distance_km'])
            places = places[:limit]
            
            return jsonify({
                'status': 'success',
                'user_location': user_location,
                'location_source': validation_data['source'],
                'places': places,
                'total_found': len(places)
            }), 200
            
        except Exception as e:
            app.logger.exception('Error getting nearest places')
            return jsonify({
                'status': 'error',
                'code': 'NEAREST_PLACES_ERROR',
                'message': f'Could not find nearest places: {str(e)}'
            }), 500

    @app.route('/location-permission')
    def location_permission_page():
        """Render the location permission page"""
        return render_template('location_permission.html')

    @app.route('/test_location_feature.html')
    def test_location_feature():
        """Serve the location feature test page"""
        from flask import send_from_directory
        import os
        return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'test_location_feature.html')

    # Add other routes as needed...

    # Debug: print registered endpoints to help diagnose url_for BuildErrors
    try:
        endpoints = sorted({rule.endpoint for rule in app.url_map.iter_rules()})
        print("Registered endpoints:", endpoints)
    except Exception:
        pass

    return app

app = create_app()

def register_commands(app):
    """Register custom CLI commands"""
    import click
    from flask.cli import with_appcontext
    
    @app.cli.command('init-db')
    @with_appcontext
    def init_db():
        """Initialize the database and create tables"""
        try:
            # Create all database tables
            db.create_all()
            
            # Create upload directory if it doesn't exist
            upload_dir = os.path.join(app.root_path, 'uploads')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
                click.echo(f'Created upload directory: {upload_dir}')
                
            click.echo('Database tables created successfully')
        except Exception as e:
            click.echo(f'Error creating database tables: {e}', err=True)
            raise
    
    @app.cli.command('create-admin')
    @click.argument('email')
    @click.argument('password')
    @with_appcontext
    def create_admin(email, password):
        """Create an admin user"""
        from werkzeug.security import generate_password_hash
        
        try:
            # Validate email
            is_valid, email_or_error = validate_email_address(email)
            if not is_valid:
                click.echo(f'Invalid email address: {email_or_error}', err=True)
                return
                
            # Check if user already exists
            if User.query.filter_by(email=email).first():
                click.echo(f'User with email {email} already exists')
                return
                
            # Create admin user
            admin = User(
                email=email,
                name='Admin',
                is_admin=True,
                is_verified=True  # Mark as verified since we're creating it manually
            )
            admin.set_password(password)
            
            db.session.add(admin)
            db.session.commit()
            
            click.echo(f'Admin user {email} created successfully')
        except Exception as e:
            db.session.rollback()
            click.echo(f'Error creating admin user: {e}', err=True)
            raise
    
    @app.cli.command('create-user')
    @click.argument('email')
    @click.argument('password')
    @click.option('--name', default='', help='Full name of the user')
    @click.option('--admin', is_flag=True, help='Make the user an admin')
    @with_appcontext
    def create_user(email, password, name, admin):
        """Create a new user"""
        from werkzeug.security import generate_password_hash
        
        try:
            # Validate email
            is_valid, email_or_error = validate_email_address(email)
            if not is_valid:
                click.echo(f'Invalid email address: {email_or_error}', err=True)
                return
                
            # Check if user already exists
            if User.query.filter_by(email=email).first():
                click.echo(f'User with email {email} already exists')
                return
                
            # Create user
            user = User(
                email=email,
                name=name if name else email.split('@')[0],
                is_admin=bool(admin),
                is_verified=True  # Mark as verified since we're creating it manually
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            user_type = 'admin user' if admin else 'user'
            click.echo(f'Successfully created {user_type} with email: {email}')
        except Exception as e:
            db.session.rollback()
            click.echo(f'Error creating user: {e}', err=True)
            raise

# Register CLI commands
app = create_app()
register_commands(app)

if __name__ == '__main__':
    # Run Flask server on HTTP localhost:5000
    # Geolocation works on localhost without HTTPS
    print("✅ Starting server with HTTP on localhost...")
    print("   Server will be available at: http://localhost:5000")
    print("   📍 Geolocation enabled - works on localhost without HTTPS")
    print("   🗺️  OpenRouteService integration active")
    
    app.run(host='localhost', port=5000, debug=True)
