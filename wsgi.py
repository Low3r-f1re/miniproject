#!/usr/bin/env python3
"""
WSGI config for the Flask application.

This module contains the WSGI application used by the production server.
"""
import os
from app import create_app

# Create the application instance
app = create_app(os.getenv('FLASK_ENV') or 'production')

if __name__ == "__main__":
    # This is only used when running the application directly
    # (not through a WSGI server)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
