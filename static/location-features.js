/**
 * Location Features Module
 * Enhanced location detection, distance calculation, and routing features
 * for TourWithMe Modern UI
 */

(function() {
    'use strict';

    // Module state
    const LocationFeatures = {
        userLocation: null,
        userMarker: null,
        watchId: null,
        isTracking: false,
        map: null
    };

    /**
     * Initialize location features for a given map
     */
    window.initLocationFeatures = function(mapInstance) {
        LocationFeatures.map = mapInstance;
        console.log('Location features initialized');
    };

    /**
     * Add "Use My Location" button to input field
     */
    window.addUseLocationButton = function(inputId) {
        const input = document.getElementById(inputId);
        if (!input) {
            console.warn(`Input field ${inputId} not found`);
            return;
        }

        // Check if button already exists
        if (input.parentElement.querySelector('.use-location-btn')) {
            return;
        }

        const wrapper = input.parentElement;
        if (!wrapper.classList.contains('modern-input-wrapper')) {
            const newWrapper = document.createElement('div');
            newWrapper.className = 'modern-input-wrapper';
            input.parentNode.insertBefore(newWrapper, input);
            newWrapper.appendChild(input);
        }

        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'use-location-btn modern-btn-location';
        btn.innerHTML = '<i class="fas fa-location-arrow"></i> Use My Location';
        btn.style.cssText = `
            position: absolute;
            right: 8px;
            top: 50%;
            transform: translateY(-50%);
            z-index: 10;
        `;

        btn.addEventListener('click', async function() {
            await useMyLocation(inputId);
        });

        input.parentElement.appendChild(btn);
    };

    /**
     * Use user's current location
     */
    async function useMyLocation(inputId) {
        const input = document.getElementById(inputId);
        const btn = input?.parentElement.querySelector('.use-location-btn');

        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Getting Location...';
        }

        try {
            const position = await getCurrentPosition();
            const { latitude, longitude } = position.coords;

            // Store user location
            LocationFeatures.userLocation = {
                lat: latitude,
                lng: longitude
            };

            // Reverse geocode to get address
            const address = await reverseGeocodeLocation(latitude, longitude);

            // Update input field
            if (input) {
                input.value = address || `${latitude.toFixed(6)}, ${longitude.toFixed(6)}`;
            }

            // Update map if available
            if (LocationFeatures.map) {
                updateUserLocationOnMap(latitude, longitude);
            }

            // Show success message
            showLocationMessage('Location detected successfully!', 'success');

            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-check"></i> Location Set';
                setTimeout(() => {
                    btn.innerHTML = '<i class="fas fa-location-arrow"></i> Use My Location';
                }, 2000);
            }

            return { latitude, longitude, address };

        } catch (error) {
            console.error('Error getting location:', error);
            showLocationMessage(getLocationErrorMessage(error), 'error');

            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-location-arrow"></i> Use My Location';
            }

            throw error;
        }
    }

    /**
     * Get current position with promise
     */
    function getCurrentPosition(options = {}) {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation is not supported by your browser'));
                return;
            }

            const defaultOptions = {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 30000
            };

            navigator.geolocation.getCurrentPosition(
                resolve,
                reject,
                { ...defaultOptions, ...options }
            );
        });
    }

    /**
     * Reverse geocode coordinates to address
     */
    async function reverseGeocodeLocation(lat, lng) {
        try {
            const response = await fetch(`/api/reverse-geocode?lat=${lat}&lon=${lng}`);
            if (!response.ok) {
                throw new Error('Failed to reverse geocode');
            }
            const data = await response.json();
            return data.label || data.display_name || null;
        } catch (error) {
            console.error('Reverse geocoding error:', error);
            return null;
        }
    }

    /**
     * Update user location on map with glowing marker
     */
    function updateUserLocationOnMap(lat, lng) {
        if (!LocationFeatures.map || typeof L === 'undefined') {
            console.warn('Map not available');
            return;
        }

        // Remove existing user marker
        if (LocationFeatures.userMarker) {
            LocationFeatures.map.removeLayer(LocationFeatures.userMarker);
        }

        // Create custom glowing icon
        const glowingIcon = L.divIcon({
            html: `
                <div style="position: relative;">
                    <div style="
                        width: 20px;
                        height: 20px;
                        background: #4facfe;
                        border: 3px solid white;
                        border-radius: 50%;
                        box-shadow: 0 0 20px rgba(79, 172, 254, 0.8);
                        animation: pulse-glow 2s infinite;
                    "></div>
                    <div style="
                        position: absolute;
                        top: 50%;
                        left: 50%;
                        transform: translate(-50%, -50%);
                        width: 40px;
                        height: 40px;
                        background: rgba(79, 172, 254, 0.2);
                        border-radius: 50%;
                        animation: pulse-expand 2s infinite;
                    "></div>
                </div>
                <style>
                    @keyframes pulse-glow {
                        0%, 100% { opacity: 1; transform: scale(1); }
                        50% { opacity: 0.7; transform: scale(1.1); }
                    }
                    @keyframes pulse-expand {
                        0% { transform: translate(-50%, -50%) scale(1); opacity: 0.5; }
                        100% { transform: translate(-50%, -50%) scale(2); opacity: 0; }
                    }
                </style>
            `,
            className: '',
            iconSize: [40, 40],
            iconAnchor: [20, 20]
        });

        // Add new user marker
        LocationFeatures.userMarker = L.marker([lat, lng], { icon: glowingIcon })
            .addTo(LocationFeatures.map)
            .bindPopup('<div style="text-align: center;"><strong>📍 Your Location</strong></div>');

        // Center map on user location
        LocationFeatures.map.setView([lat, lng], 13);
    }

    /**
     * Calculate distance between two points (Haversine formula)
     */
    window.calculateDistance = function(lat1, lon1, lat2, lon2) {
        const R = 6371; // Earth's radius in km
        const dLat = toRad(lat2 - lat1);
        const dLon = toRad(lon2 - lon1);
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                  Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
                  Math.sin(dLon / 2) * Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    };

    function toRad(degrees) {
        return degrees * (Math.PI / 180);
    }

    /**
     * Format distance for display
     */
    window.formatDistance = function(km) {
        if (km < 1) {
            return `${Math.round(km * 1000)}m`;
        } else if (km < 10) {
            return `${km.toFixed(1)}km`;
        } else {
            return `${Math.round(km)}km`;
        }
    };

    /**
     * Get route between two points
     */
    window.getRoute = async function(startLat, startLng, endLat, endLng, profile = 'driving-car') {
        try {
            const response = await fetch('/api/directions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    start_lat: startLat,
                    start_lon: startLng,
                    end_lat: endLat,
                    end_lon: endLng,
                    profile: profile
                })
            });

            if (!response.ok) {
                throw new Error('Failed to get route');
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error getting route:', error);
            throw error;
        }
    };

    /**
     * Display route on map
     */
    window.displayRouteOnMap = function(route) {
        if (!LocationFeatures.map || !route || !route.coordinates) {
            return;
        }

        // Clear existing route
        if (window.currentRoute) {
            LocationFeatures.map.removeLayer(window.currentRoute);
        }

        // Create polyline
        const latlngs = route.coordinates.map(coord => [coord[1], coord[0]]);
        window.currentRoute = L.polyline(latlngs, {
            color: '#667eea',
            weight: 5,
            opacity: 0.8
        }).addTo(LocationFeatures.map);

        // Fit map to route
        LocationFeatures.map.fitBounds(window.currentRoute.getBounds(), {
            padding: [50, 50]
        });

        // Show route info
        displayRouteInfo(route);
    };

    /**
     * Display route information card
     */
    function displayRouteInfo(route) {
        // Remove existing route info
        const existing = document.querySelector('.route-info-overlay');
        if (existing) {
            existing.remove();
        }

        // Create route info card
        const infoCard = document.createElement('div');
        infoCard.className = 'route-info-overlay';
        infoCard.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            z-index: 1000;
            max-width: 400px;
            width: 90%;
            animation: slideUp 0.3s ease-out;
        `;

        const travelModes = {
            'driving-car': { icon: '🚗', name: 'Driving' },
            'cycling-regular': { icon: '🚴', name: 'Cycling' },
            'foot-walking': { icon: '🚶', name: 'Walking' }
        };

        const mode = travelModes[route.profile] || { icon: '🚗', name: 'Travel' };

        infoCard.innerHTML = `
            <style>
                @keyframes slideUp {
                    from { transform: translateX(-50%) translateY(100px); opacity: 0; }
                    to { transform: translateX(-50%) translateY(0); opacity: 1; }
                }
            </style>
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px;">
                <div>
                    <div style="font-size: 1.25rem; font-weight: 700; color: #1f2937; margin-bottom: 5px;">
                        Route Preview
                    </div>
                    <div style="font-size: 0.875rem; color: #6b7280;">
                        ${mode.icon} ${mode.name}
                    </div>
                </div>
                <button onclick="this.parentElement.parentElement.remove()" style="
                    background: none;
                    border: none;
                    font-size: 1.5rem;
                    color: #9ca3af;
                    cursor: pointer;
                    padding: 0;
                    line-height: 1;
                ">&times;</button>
            </div>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">
                <div>
                    <div style="font-size: 0.75rem; color: #6b7280; text-transform: uppercase; font-weight: 600; margin-bottom: 5px;">
                        Distance
                    </div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: #667eea;">
                        ${route.distance_km.toFixed(1)} km
                    </div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: #6b7280; text-transform: uppercase; font-weight: 600; margin-bottom: 5px;">
                        Duration
                    </div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: #667eea;">
                        ${formatDuration(route.duration_minutes)}
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(infoCard);

        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (infoCard.parentElement) {
                infoCard.remove();
            }
        }, 10000);
    }

    /**
     * Format duration in minutes to human-readable format
     */
    function formatDuration(minutes) {
        if (minutes < 60) {
            return `${Math.round(minutes)}m`;
        }
        const hours = Math.floor(minutes / 60);
        const mins = Math.round(minutes % 60);
        return `${hours}h ${mins}m`;
    }

    /**
     * Add distance badge to element
     */
    window.addDistanceBadge = function(element, distanceKm) {
        const badge = document.createElement('div');
        badge.className = 'restaurant-distance-badge';
        badge.innerHTML = `
            <i class="fas fa-map-marker-alt"></i>
            ${formatDistance(distanceKm)}
        `;
        element.appendChild(badge);
    };

    /**
     * Show location-related message
     */
    function showLocationMessage(message, type = 'info') {
        // Remove existing message
        const existing = document.querySelector('.location-message');
        if (existing) {
            existing.remove();
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = 'location-message';
        
        const colors = {
            success: { bg: '#d1fae5', text: '#065f46', border: '#10b981' },
            error: { bg: '#fee2e2', text: '#991b1b', border: '#ef4444' },
            info: { bg: '#dbeafe', text: '#1e40af', border: '#3b82f6' }
        };

        const color = colors[type] || colors.info;
        
        messageDiv.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            background: ${color.bg};
            color: ${color.text};
            border-left: 4px solid ${color.border};
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 10000;
            max-width: 400px;
            animation: slideInRight 0.3s ease-out;
            font-weight: 600;
        `;

        messageDiv.innerHTML = `
            <style>
                @keyframes slideInRight {
                    from { transform: translateX(400px); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOutRight {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(400px); opacity: 0; }
                }
            </style>
            <div style="display: flex; align-items: center; gap: 10px;">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
                <span>${message}</span>
            </div>
        `;

        document.body.appendChild(messageDiv);

        // Auto-remove after 4 seconds
        setTimeout(() => {
            messageDiv.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => {
                if (messageDiv.parentElement) {
                    messageDiv.remove();
                }
            }, 300);
        }, 4000);
    }

    /**
     * Get user-friendly error message
     */
    function getLocationErrorMessage(error) {
        switch (error.code) {
            case error.PERMISSION_DENIED:
                return 'Location access denied. Please enable location permissions in your browser.';
            case error.POSITION_UNAVAILABLE:
                return 'Location information unavailable. Please try again.';
            case error.TIMEOUT:
                return 'Location request timed out. Please try again.';
            default:
                return 'Unable to get your location. Please enter it manually.';
        }
    }

    /**
     * Start tracking user location in real-time
     */
    window.startLocationTracking = function() {
        if (LocationFeatures.isTracking) {
            return;
        }

        if (!navigator.geolocation) {
            showLocationMessage('Geolocation not supported', 'error');
            return;
        }

        LocationFeatures.watchId = navigator.geolocation.watchPosition(
            (position) => {
                const { latitude, longitude } = position.coords;
                LocationFeatures.userLocation = { lat: latitude, lng: longitude };
                
                if (LocationFeatures.map) {
                    updateUserLocationOnMap(latitude, longitude);
                }
            },
            (error) => {
                console.error('Location tracking error:', error);
            },
            {
                enableHighAccuracy: true,
                timeout: 5000,
                maximumAge: 0
            }
        );

        LocationFeatures.isTracking = true;
        showLocationMessage('Location tracking enabled', 'success');
    };

    /**
     * Stop tracking user location
     */
    window.stopLocationTracking = function() {
        if (LocationFeatures.watchId) {
            navigator.geolocation.clearWatch(LocationFeatures.watchId);
            LocationFeatures.watchId = null;
        }
        LocationFeatures.isTracking = false;
    };

    /**
     * Get user location for route calculation
     */
    window.getUserLocationForRoute = async function() {
        if (LocationFeatures.userLocation) {
            return LocationFeatures.userLocation;
        }

        try {
            const position = await getCurrentPosition();
            LocationFeatures.userLocation = {
                lat: position.coords.latitude,
                lng: position.coords.longitude
            };
            return LocationFeatures.userLocation;
        } catch (error) {
            throw new Error('Unable to get user location');
        }
    };

    /**
     * Calculate and display route to destination
     */
    window.showRouteToDestination = async function(destLat, destLng, profile = 'driving-car') {
        try {
            showLocationMessage('Calculating route...', 'info');

            const userLoc = await getUserLocationForRoute();
            const route = await getRoute(userLoc.lat, userLoc.lng, destLat, destLng, profile);
            
            displayRouteOnMap(route);
            showLocationMessage('Route calculated successfully!', 'success');

            return route;
        } catch (error) {
            showLocationMessage('Unable to calculate route', 'error');
            throw error;
        }
    };

    // Expose module for debugging
    window.LocationFeatures = LocationFeatures;

    console.log('Location Features Module loaded');
})();
