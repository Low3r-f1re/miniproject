/**
 * Directions Module
 * Handles navigation and route display for TourWithMe
 * - Google Maps links for restaurants
 * - Embedded Leaflet maps with OpenRouteService routing for trip planning
 */

(function() {
    'use strict';

    // Global variables
    let routeMap = null;
    let routeLayer = null;
    let userLocation = null;

    /**
     * Initialize user location from various sources
     */
    async function initializeUserLocation() {
        if (userLocation) return userLocation;

        try {
            // Try to get from user profile first
            const response = await fetch('/api/me');
            if (response.ok) {
                const userData = await response.json();
                if (userData.authenticated && userData.home_latitude && userData.home_longitude) {
                    userLocation = {
                        lat: userData.home_latitude,
                        lon: userData.home_longitude,
                        city: userData.home_city,
                        source: 'profile'
                    };
                    return userLocation;
                }
            }

            // Try to get from browser geolocation
            if (navigator.geolocation) {
                return new Promise((resolve, reject) => {
                    navigator.geolocation.getCurrentPosition(
                        position => {
                            userLocation = {
                                lat: position.coords.latitude,
                                lon: position.coords.longitude,
                                source: 'gps'
                            };
                            resolve(userLocation);
                        },
                        error => {
                            console.warn('Geolocation error:', error);
                            reject(error);
                        }
                    );
                });
            }

            return null;
        } catch (error) {
            console.error('Error initializing user location:', error);
            return null;
        }
    }

    /**
     * Open Google Maps with directions
     * @param {string} destination - Destination address or coordinates
     * @param {string} destinationName - Name of the destination
     */
    window.openGoogleMapsDirections = async function(destination, destinationName) {
        try {
            const userLoc = await initializeUserLocation();
            
            let origin = '';
            if (userLoc) {
                origin = `${userLoc.lat},${userLoc.lon}`;
            }

            // Build Google Maps URL
            const baseUrl = 'https://www.google.com/maps/dir/';
            let url = baseUrl;
            
            if (origin) {
                url += `?api=1&origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(destination)}`;
            } else {
                url += `?api=1&destination=${encodeURIComponent(destination)}`;
            }
            
            // Add travel mode (default to driving)
            url += '&travelmode=driving';
            
            // Open in new tab
            window.open(url, '_blank');
            
        } catch (error) {
            console.error('Error opening Google Maps:', error);
            // Fallback: open Google Maps with just destination
            const fallbackUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(destination)}`;
            window.open(fallbackUrl, '_blank');
        }
    };

    /**
     * Show route on embedded Leaflet map
     * @param {number} destLat - Destination latitude
     * @param {number} destLon - Destination longitude
     * @param {string} destName - Destination name
     * @param {string} transportMode - Transport mode (driving-car, foot-walking, etc.)
     */
    window.showRouteOnMap = async function(destLat, destLon, destName, transportMode = 'driving-car') {
        try {
            // Get user location
            const userLoc = await initializeUserLocation();
            
            if (!userLoc) {
                alert('Please enable location services or set your home location in settings to view routes.');
                return;
            }

            // Show the modal
            const modal = document.getElementById('routeModal');
            if (!modal) {
                console.error('Route modal not found');
                return;
            }
            
            modal.style.display = 'block';
            document.body.style.overflow = 'hidden';

            // Update modal title
            const modalTitle = document.getElementById('routeModalTitle');
            if (modalTitle) {
                modalTitle.textContent = `Route to ${destName}`;
            }

            // Show loading
            showRouteLoading(true);

            // Initialize map if not already done
            if (!routeMap) {
                const mapContainer = document.getElementById('routeMapContainer');
                routeMap = L.map(mapContainer).setView([userLoc.lat, userLoc.lon], 10);
                
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '© OpenStreetMap contributors',
                    maxZoom: 19
                }).addTo(routeMap);
            } else {
                // Clear existing routes
                if (routeLayer) {
                    routeMap.removeLayer(routeLayer);
                }
                routeMap.eachLayer(layer => {
                    if (layer instanceof L.Marker) {
                        routeMap.removeLayer(layer);
                    }
                });
            }

            // Fetch route from backend
            const response = await fetch('/api/directions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    start_lat: userLoc.lat,
                    start_lon: userLoc.lon,
                    end_lat: destLat,
                    end_lon: destLon,
                    profile: transportMode,
                    alternatives: 1
                })
            });

            if (!response.ok) {
                throw new Error('Failed to fetch route');
            }

            const routeData = await response.json();
            
            // Display route on map
            displayRouteOnMap(routeData, userLoc, { lat: destLat, lon: destLon }, destName);
            
            showRouteLoading(false);

        } catch (error) {
            console.error('Error showing route:', error);
            showRouteLoading(false);
            showRouteError('Failed to load route. Please try again.');
        }
    };

    /**
     * Display route on the map
     */
    function displayRouteOnMap(routeData, origin, destination, destName) {
        if (!routeData || !routeData.routes || routeData.routes.length === 0) {
            showRouteError('No route found');
            return;
        }

        const route = routeData.routes[0];
        const coordinates = route.geometry.coordinates;
        
        // Convert coordinates from [lon, lat] to [lat, lon] for Leaflet
        const latLngs = coordinates.map(coord => [coord[1], coord[0]]);

        // Draw route
        routeLayer = L.polyline(latLngs, {
            color: '#667eea',
            weight: 5,
            opacity: 0.7,
            smoothFactor: 1
        }).addTo(routeMap);

        // Add markers
        const startIcon = L.icon({
            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
            shadowUrl: '/static/images/leaflet/marker-shadow.png',
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
            shadowSize: [41, 41]
        });

        const endIcon = L.icon({
            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
            shadowUrl: '/static/images/leaflet/marker-shadow.png',
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
            shadowSize: [41, 41]
        });

        L.marker([origin.lat, origin.lon], { icon: startIcon })
            .bindPopup('<b>Your Location</b>')
            .addTo(routeMap);

        L.marker([destination.lat, destination.lon], { icon: endIcon })
            .bindPopup(`<b>${destName}</b>`)
            .addTo(routeMap);

        // Fit bounds to show entire route
        routeMap.fitBounds(routeLayer.getBounds(), { padding: [50, 50] });

        // Display route info
        displayRouteInfo(route);
    }

    /**
     * Display route information
     */
    function displayRouteInfo(route) {
        const infoContainer = document.getElementById('routeInfo');
        if (!infoContainer) return;

        const distanceKm = (route.summary.distance / 1000).toFixed(1);
        const durationMin = Math.round(route.summary.duration / 60);
        const hours = Math.floor(durationMin / 60);
        const minutes = durationMin % 60;
        const durationStr = hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;

        infoContainer.innerHTML = `
            <div class="route-info-card">
                <div class="route-stat">
                    <i class="fas fa-route"></i>
                    <div>
                        <span class="route-label">Distance</span>
                        <span class="route-value">${distanceKm} km</span>
                    </div>
                </div>
                <div class="route-stat">
                    <i class="fas fa-clock"></i>
                    <div>
                        <span class="route-label">Duration</span>
                        <span class="route-value">${durationStr}</span>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Show/hide route loading state
     */
    function showRouteLoading(show) {
        const loadingEl = document.getElementById('routeLoading');
        const mapEl = document.getElementById('routeMapContainer');
        const infoEl = document.getElementById('routeInfo');
        
        if (loadingEl) loadingEl.style.display = show ? 'flex' : 'none';
        if (mapEl) mapEl.style.display = show ? 'none' : 'block';
        if (infoEl) infoEl.style.display = show ? 'none' : 'block';
    }

    /**
     * Show route error
     */
    function showRouteError(message) {
        const errorEl = document.getElementById('routeError');
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.style.display = 'block';
            
            setTimeout(() => {
                errorEl.style.display = 'none';
            }, 5000);
        }
    }

    /**
     * Close route modal
     */
    window.closeRouteModal = function() {
        const modal = document.getElementById('routeModal');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }

        // Clean up map
        if (routeMap) {
            routeMap.remove();
            routeMap = null;
            routeLayer = null;
        }
    };

    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        const modal = document.getElementById('routeModal');
        if (event.target === modal) {
            closeRouteModal();
        }
    });

    // Close modal on Escape key
    window.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            const modal = document.getElementById('routeModal');
            if (modal && modal.style.display === 'block') {
                closeRouteModal();
            }
        }
    });

    console.log('Directions module loaded');
})();
