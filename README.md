# 🌍 Travel Planner - AI-Powered Trip Planning Application

A comprehensive Flask-based travel planning application with AI-powered recommendations, real-time collaboration, and intelligent route planning.

## ✨ Features

- 🤖 **AI Trip Planning** - Generate personalized itineraries using Gemini AI and OpenRouter
- 🗺️ **Interactive Maps** - Leaflet maps with OpenRouteService integration
- 📍 **Location-Based Recommendations** - Find destinations near you
- 💰 **Budget Calculator** - Realistic cost estimates with currency conversion
- 🍽️ **Restaurant Recommendations** - AI-powered dining suggestions
- 🚗 **Route Planning** - Get directions and travel time estimates
- 👥 **Collaborative Planning** - Plan trips with friends
- 🌐 **Multi-language Support** - English, Hindi, Kannada
- 🔐 **Secure Authentication** - User login with password reset
- 📱 **Responsive Design** - Works on desktop and mobile

## 🚀 Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- pip
- Git

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/YOUR-USERNAME/YOUR-REPO.git
cd travel
```

2. **Create virtual environment**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your API keys:
# - GEMINI_API_KEY (get from https://makersuite.google.com/app/apikey)
# - OPENROUTER_API_KEY (get from https://openrouter.ai/keys)
# - SECRET_KEY (generate a random string)
```

5. **Initialize the database**
```bash
flask db upgrade
# or
python -c "from app import create_app; from extensions import db; app = create_app(); app.app_context().push(); db.create_all()"
```

6. **Run the application**
```bash
python app.py
# or
flask run
```

7. **Access the app**
```
http://localhost:5000
```

## 🌐 Deployment to Render.com (Production)

This app is configured for easy deployment to Render.com's free tier.

### Quick Deploy

1. **Push to GitHub**
```bash
git add .
git commit -m "Ready for deployment"
git push origin main
```

2. **Deploy on Render**
   - Go to https://dashboard.render.com
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Render will detect `render.yaml` and set everything up automatically

3. **Add API Keys**
   - In Render dashboard, go to Environment
   - Add `GEMINI_API_KEY` and `OPENROUTER_API_KEY`

📖 **Full deployment guide:** See [DEPLOYMENT.md](./DEPLOYMENT.md)

## 📁 Project Structure

```
travel/
├── app.py                    # Main Flask application
├── wsgi.py                   # Production WSGI entry point
├── config.py                 # Configuration settings
├── models.py                 # Database models
├── extensions.py             # Flask extensions
├── requirements.txt          # Python dependencies
├── render.yaml              # Render.com deployment config
├── build.sh                 # Build script for deployment
├── DEPLOYMENT.md            # Detailed deployment guide
├── alembic/                 # Database migrations
├── services/                # Business logic services
│   ├── gemini_service.py    # Gemini AI integration
│   ├── openrouter_service.py # OpenRouter AI integration
│   ├── openroute_service.py # OpenRouteService maps/routing
│   ├── recommendation_service.py
│   ├── cost_calculation_service.py
│   └── image_service.py
├── static/                  # CSS, JS, images
├── templates/               # HTML templates
└── utils/                   # Utility functions
```

## 🔑 Environment Variables

### Required for Production
- `SECRET_KEY` - Flask secret key (auto-generated on Render)
- `DATABASE_URL` - Database connection (auto-set on Render)
- `GEMINI_API_KEY` - Google Gemini AI API key
- `OPENROUTER_API_KEY` - OpenRouter API key
- `FLASK_ENV` - Set to `production`

### Optional
- `MAIL_SERVER`, `MAIL_USERNAME`, `MAIL_PASSWORD` - For email notifications
- `PUBLIC_GOOGLE_MAPS_KEY` - If using Google Maps (optional)
- `BABEL_DEFAULT_LOCALE` - Default language (default: `en`)

See `.env.example` for complete list.

## 🛠️ Technology Stack

**Backend:**
- Flask 2.3+ - Web framework
- SQLAlchemy - ORM
- PostgreSQL - Production database
- SQLite - Development database
- Flask-Login - Authentication
- Flask-Babel - Internationalization

**AI & APIs:**
- Google Gemini AI - Trip planning
- OpenRouter - Alternative AI provider
- OpenRouteService - Maps and routing
- Unsplash API - Destination images

**Frontend:**
- Leaflet.js - Interactive maps
- Vanilla JavaScript - Frontend logic
- CSS3 - Styling

**Deployment:**
- Render.com - Hosting platform
- Gunicorn - WSGI server
- PostgreSQL - Production database

## 📊 Database Schema

- **User** - User accounts with location data
- **Destination** - Travel destinations with details
- **TripPlan** - User trip plans
- **TripParticipant** - Collaborative trip participants
- **TripActivity** - Activities in trip plans

## 🔧 Development Commands

```bash
# Run development server
python app.py

# Run with Flask CLI
flask run

# Initialize database
flask db init

# Create migration
flask db migrate -m "description"

# Apply migrations
flask db upgrade

# Create admin user
flask create-admin admin@example.com password123

# Create regular user
flask create-user user@example.com password123 --name "John Doe"
```

## 🧪 Testing

```bash
# Run tests (if implemented)
pytest

# Check code style
flake8 .

# Format code
black .
```

## 🌍 Internationalization

Supported languages:
- 🇬🇧 English (`en`)
- 🇮🇳 Hindi (`hi`)
- 🇮🇳 Kannada (`kn`)

Add translations in `static/translations/`

## 📝 API Endpoints

### Authentication
- `POST /api/signup` - Register new user
- `POST /api/login` - Login
- `POST /api/logout` - Logout
- `GET /api/me` - Get current user

### Destinations
- `GET /api/destinations` - List all destinations
- `POST /api/destinations` - Create destination
- `GET /api/destinations/<id>` - Get destination
- `PUT /api/destinations/<id>` - Update destination
- `DELETE /api/destinations/<id>` - Delete destination

### Recommendations
- `GET /api/recommendations` - Get personalized recommendations
- `GET /api/recommendations/trending` - Get trending destinations
- `POST /api/trip-plan` - Generate AI trip plan
- `GET /api/restaurant-recommendations` - Get restaurant suggestions

### Routing & Maps
- `POST /api/directions` - Get directions between points
- `GET /api/geocode` - Geocode location to coordinates
- `GET /api/reverse-geocode` - Reverse geocode coordinates
- `POST /api/location/validate` - Validate user location

See API documentation for complete list.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🆘 Support

- 📖 [Deployment Guide](./DEPLOYMENT.md)
- 🐛 [Report Issues](https://github.com/YOUR-USERNAME/YOUR-REPO/issues)
- 💬 [Discussions](https://github.com/YOUR-USERNAME/YOUR-REPO/discussions)

## 🙏 Acknowledgments

- Google Gemini AI for intelligent trip planning
- OpenRouteService for maps and routing
- Unsplash for beautiful destination images
- Render.com for free hosting
- All contributors and users

## 📈 Roadmap

- [ ] Add more AI providers
- [ ] Implement real-time collaboration
- [ ] Add weather integration
- [ ] Mobile app (React Native)
- [ ] Social features (share trips)
- [ ] Advanced budget analytics
- [ ] Booking integration

---

**Made with ❤️ for travelers**

Deploy your own instance: [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com)
