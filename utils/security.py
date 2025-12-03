from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app

def get_token_serializer():
    """Get a configured token serializer instance"""
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

def generate_reset_token(email):
    """Generate a secure password reset token"""
    serializer = get_token_serializer()
    return serializer.dumps(email, salt='password-reset-salt')

def verify_reset_token(token, max_age=3600):
    """Verify a password reset token and return the email if valid"""
    if not token:
        return None
        
    serializer = get_token_serializer()
    try:
        email = serializer.loads(
            token,
            salt='password-reset-salt',
            max_age=max_age  # 1 hour expiration by default
        )
        return email
    except:
        return None

def is_password_strong(password):
    """Check if a password meets strength requirements"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one number"
    if not any(char.isupper() for char in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(char.islower() for char in password):
        return False, "Password must contain at least one lowercase letter"
    return True, ""

def validate_email_address(email):
    """Validate an email address format"""
    from email_validator import validate_email, EmailNotValidError
    try:
        valid = validate_email(email)
        return True, valid.email  # Return normalized email
    except EmailNotValidError as e:
        return False, str(e)
