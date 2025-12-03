/**
 * Map.js - OpenRouteService + Leaflet Implementation
 * Replaces Google Maps with open-source alternatives
 */

const MAP_CONFIG = {
    defaultLocation: { lat: 20, lng: 0 },
    defaultZoom: 2,
    tileLayer: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
};

let map, marker, routePolyline, directionsPanel;
let isochroneLayers = [];
let searchTimeout = null;

/**
 * Initialize Leaflet map
 */
window.initMap = function() {
    const mapElement = document.getElementById('map');
    if (!mapElement) {
        console.warn('Map element not found');
        return;
    }

    // Ensure Leaflet is loaded
    if (typeof L === 'undefined') {
        console.error('Leaflet library not loaded');
        return;
    }

    // Configure Leaflet's default icon paths for local hosting
    L.Icon.Default.prototype.options = {
        iconUrl: '/static/images/leaflet/marker-icon.png',
        iconRetinaUrl: '/static/images/leaflet/marker-icon-2x.png',
        shadowUrl: '/static/images/leaflet/marker-shadow.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        tooltipAnchor: [16, -28],
        shadowSize: [41, 41]
    };

    // Initialize Leaflet map
    map = L.map('map').setView([MAP_CONFIG.defaultLocation.lat, MAP_CONFIG.defaultLocation.lng], MAP_CONFIG.defaultZoom);

    // Add OpenStreetMap tile layer
    L.tileLayer(MAP_CONFIG.tileLayer, {
        attribution: MAP_CONFIG.attribution,
        maxZoom: 19
    }).addTo(map);

    // Initialize location search
    const searchInput = document.getElementById('locationSearch');
    if (searchInput) {
        initLocationSearch(searchInput);
    }

    // Add click handler to map
    map.on('click', function(e) {
        const latlng = e.latlng;
        placeMarker(latlng.lat, latlng.lng);
        reverseGeocode(latlng.lat, latlng.lng);
    });

    console.log('Leaflet map initialized successfully');
    
    // Initialize real-time location tracking if location.js is loaded
    if (typeof window.initRealTimeLocation === 'function') {
        window.initRealTimeLocation(map);
    }
    
    // Add Locate Me button if location.js is loaded
    if (typeof window.addLocateMeButton === 'function') {
        window.addLocateMeButton(map);
    }
};

/**
 * Initialize location search with autocomplete dropdown
 */
function initLocationSearch(input) {
    // Create search container wrapper
    const searchContainer = createSearchContainer(input);
    
    // Create and add search button
    const searchButton = createSearchButton();
    searchContainer.appendChild(searchButton);
    
    // Create dropdown for suggestions
    const dropdown = createSuggestionsDropdown();
    searchContainer.appendChild(dropdown);
    
    // Create toggle arrow
    const toggleArrow = createToggleArrow();
    searchContainer.appendChild(toggleArrow);
    
    let currentSuggestions = [];
    let selectedIndex = -1;

    // Input event for autocomplete
    input.addEventListener('input', function(e) {
        const query = e.target.value.trim();
        
        // Clear previous timeout
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }

        // Clear dropdown if query is too short
        if (query.length < 2) {
            hideDropdown(dropdown);
            currentSuggestions = [];
            return;
        }

        // Show loading state
        showLoadingInDropdown(dropdown);

        // Debounce autocomplete search
        searchTimeout = setTimeout(async () => {
            await fetchSuggestions(query, dropdown, input);
        }, 300);
    });

    // Enter key to search
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            const query = e.target.value.trim();
            if (query) {
                hideDropdown(dropdown);
                searchAndGeocode(query);
            }
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            navigateSuggestions(dropdown, 'down');
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            navigateSuggestions(dropdown, 'up');
        } else if (e.key === 'Escape') {
            hideDropdown(dropdown);
        }
    });

    // Search button click
    searchButton.addEventListener('click', function() {
        const query = input.value.trim();
        if (query) {
            hideDropdown(dropdown);
            searchAndGeocode(query);
        }
    });

    // Toggle arrow click
    toggleArrow.addEventListener('click', function() {
        if (dropdown.style.display === 'block') {
            hideDropdown(dropdown);
        } else if (currentSuggestions.length > 0) {
            showDropdown(dropdown);
        }
    });

    // Click outside to close
    document.addEventListener('click', function(e) {
        if (!searchContainer.contains(e.target)) {
            hideDropdown(dropdown);
        }
    });

    // Store references for later use
    input._searchDropdown = dropdown;
    input._currentSuggestions = currentSuggestions;
}

/**
 * Create search container wrapper
 */
function createSearchContainer(input) {
    const parent = input.parentElement;
    const container = document.createElement('div');
    container.className = 'map-search-container';
    
    // Set container styles individually
    container.style.position = 'relative';
    container.style.display = 'block';
    container.style.width = '100%';
    
    parent.insertBefore(container, input);
    container.appendChild(input);
    
    // Add styling to input
    input.style.paddingRight = '120px';
    input.style.boxSizing = 'border-box';
    input.style.width = '100%';
    
    console.log('Search container created');
    return container;
}

/**
 * Create search button
 */
function createSearchButton() {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'map-search-button';
    button.innerHTML = '<i class="fas fa-search"></i> Search';
    
    // Set each style individually for maximum compatibility
    button.style.position = 'absolute';
    button.style.right = '40px';
    button.style.top = '8px';
    button.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
    button.style.color = 'white';
    button.style.border = 'none';
    button.style.borderRadius = '6px';
    button.style.padding = '8px 14px';
    button.style.cursor = 'pointer';
    button.style.fontSize = '13px';
    button.style.fontWeight = '600';
    button.style.transition = 'all 0.3s';
    button.style.zIndex = '1000';
    button.style.boxShadow = '0 2px 8px rgba(102, 126, 234, 0.3)';
    button.style.height = '32px';
    button.style.lineHeight = '16px';
    button.style.display = 'block';
    
    button.addEventListener('mouseenter', function() {
        this.style.transform = 'scale(1.05)';
        this.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.5)';
    });
    
    button.addEventListener('mouseleave', function() {
        this.style.transform = 'scale(1)';
        this.style.boxShadow = '0 2px 8px rgba(102, 126, 234, 0.3)';
    });
    
    console.log('Search button created');
    return button;
}

/**
 * Create toggle arrow for dropdown
 */
function createToggleArrow() {
    const arrow = document.createElement('button');
    arrow.type = 'button';
    arrow.className = 'map-search-toggle';
    arrow.innerHTML = '<i class="fas fa-chevron-down"></i>';
    arrow.style.cssText = `
        position: absolute !important;
        right: 8px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        background: transparent !important;
        color: #667eea !important;
        border: none !important;
        cursor: pointer !important;
        padding: 8px 10px !important;
        font-size: 14px !important;
        transition: all 0.3s !important;
        z-index: 100 !important;
        display: block !important;
        height: auto !important;
        width: auto !important;
        line-height: normal !important;
    `;
    
    arrow.addEventListener('mouseenter', function() {
        this.style.color = '#764ba2';
    });
    
    arrow.addEventListener('mouseleave', function() {
        this.style.color = '#667eea';
    });
    
    return arrow;
}

/**
 * Create suggestions dropdown
 */
function createSuggestionsDropdown() {
    const dropdown = document.createElement('div');
    dropdown.className = 'map-search-dropdown';
    dropdown.style.cssText = `
        position: absolute;
        top: calc(100% + 5px);
        left: 0;
        right: 0;
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
        max-height: 400px;
        overflow-y: auto;
        display: none;
        z-index: 1000;
    `;
    
    return dropdown;
}

/**
 * Fetch autocomplete suggestions
 */
async function fetchSuggestions(query, dropdown, input) {
    try {
        const response = await fetch(`/api/location/autocomplete?query=${encodeURIComponent(query)}`);
        
        if (!response.ok) {
            hideDropdown(dropdown);
            return;
        }

        const data = await response.json();
        const suggestions = data.suggestions || [];
        
        if (suggestions.length === 0) {
            showNoResults(dropdown);
            return;
        }

        displaySuggestions(suggestions, dropdown, input);
    } catch (error) {
        console.error('Error fetching suggestions:', error);
        hideDropdown(dropdown);
    }
}

/**
 * Display suggestions in dropdown
 */
function displaySuggestions(suggestions, dropdown, input) {
    dropdown.innerHTML = '';
    
    suggestions.forEach((suggestion, index) => {
        const item = document.createElement('div');
        item.className = 'suggestion-item';
        item.dataset.index = index;
        item.dataset.lat = suggestion.latitude;
        item.dataset.lon = suggestion.longitude;
        item.dataset.label = suggestion.label;
        
        item.style.cssText = `
            padding: 12px 15px;
            cursor: pointer;
            transition: all 0.2s;
            border-bottom: 1px solid #f0f0f0;
        `;
        
        // Build location display
        const locationParts = [];
        if (suggestion.name) locationParts.push(suggestion.name);
        if (suggestion.locality && suggestion.locality !== suggestion.name) locationParts.push(suggestion.locality);
        if (suggestion.region) locationParts.push(suggestion.region);
        if (suggestion.country) locationParts.push(suggestion.country);
        
        const locationText = locationParts.join(', ');
        const confidence = suggestion.confidence || 0;
        
        item.innerHTML = `
            <div style="display: flex; align-items: start; gap: 10px;">
                <i class="fas fa-map-marker-alt" style="color: #667eea; margin-top: 3px;"></i>
                <div style="flex: 1;">
                    <div style="font-weight: 600; color: #333; margin-bottom: 2px;">${escapeHtml(suggestion.name || suggestion.label)}</div>
                    <div style="font-size: 12px; color: #666;">${escapeHtml(locationText)}</div>
                </div>
                ${confidence > 0.8 ? '<span style="color: #27ae60; font-size: 11px;"><i class="fas fa-check-circle"></i></span>' : ''}
            </div>
        `;
        
        // Hover effect
        item.addEventListener('mouseenter', function() {
            this.style.background = '#f8f9fd';
            this.style.borderLeftColor = '#667eea';
            this.style.borderLeftWidth = '3px';
            this.style.borderLeftStyle = 'solid';
        });
        
        item.addEventListener('mouseleave', function() {
            this.style.background = 'white';
            this.style.borderLeft = 'none';
        });
        
        // Click to select
        item.addEventListener('click', function() {
            selectSuggestion(this, input, dropdown);
        });
        
        dropdown.appendChild(item);
    });
    
    showDropdown(dropdown);
}

/**
 * Select a suggestion
 */
function selectSuggestion(item, input, dropdown) {
    const lat = parseFloat(item.dataset.lat);
    const lon = parseFloat(item.dataset.lon);
    const label = item.dataset.label;
    
    // Update input
    input.value = label;
    
    // Hide dropdown
    hideDropdown(dropdown);
    
    // Geocode and center map
    if (lat && lon) {
        map.setView([lat, lon], 13);
        placeMarker(lat, lon);
        
        // Show status
        showMapStatus(`Found: ${label}`, 'success');
    }
}

/**
 * Search and geocode location (for button/enter key)
 */
async function searchAndGeocode(query) {
    try {
        showMapStatus('Searching...', 'info');
        
        const response = await fetch(`/api/geocode?location=${encodeURIComponent(query)}`);
        
        if (!response.ok) {
            showMapStatus('Location not found', 'error');
            return;
        }

        const result = await response.json();
        
        if (result && result.latitude && result.longitude) {
            const lat = result.latitude;
            const lng = result.longitude;
            
            // Center map on location
            map.setView([lat, lng], 13);
            
            // Place marker
            placeMarker(lat, lng);
            
            // Update search input with formatted address
            const searchInput = document.getElementById('locationSearch');
            if (searchInput && result.label) {
                searchInput.value = result.label;
            }
            
            showMapStatus(`Found: ${result.label || query}`, 'success');
        } else {
            showMapStatus('Could not find location', 'error');
        }
    } catch (error) {
        console.error('Error searching location:', error);
        showMapStatus('Search failed', 'error');
    }
}

/**
 * Show/hide dropdown
 */
function showDropdown(dropdown) {
    dropdown.style.display = 'block';
}

function hideDropdown(dropdown) {
    dropdown.style.display = 'none';
}

/**
 * Show loading state in dropdown
 */
function showLoadingInDropdown(dropdown) {
    dropdown.innerHTML = `
        <div style="padding: 20px; text-align: center; color: #666;">
            <i class="fas fa-spinner fa-spin"></i>
            <div style="margin-top: 8px; font-size: 13px;">Searching...</div>
        </div>
    `;
    showDropdown(dropdown);
}

/**
 * Show no results message
 */
function showNoResults(dropdown) {
    dropdown.innerHTML = `
        <div style="padding: 20px; text-align: center; color: #999;">
            <i class="fas fa-search" style="font-size: 24px; margin-bottom: 8px; opacity: 0.3;"></i>
            <div style="font-size: 13px;">No locations found</div>
        </div>
    `;
    showDropdown(dropdown);
}

/**
 * Navigate suggestions with arrow keys
 */
function navigateSuggestions(dropdown, direction) {
    const items = dropdown.querySelectorAll('.suggestion-item');
    if (items.length === 0) return;
    
    const currentActive = dropdown.querySelector('.suggestion-item.active');
    let currentIndex = currentActive ? parseInt(currentActive.dataset.index) : -1;
    
    // Remove current active
    if (currentActive) {
        currentActive.classList.remove('active');
        currentActive.style.background = 'white';
        currentActive.style.borderLeft = 'none';
    }
    
    // Calculate new index
    if (direction === 'down') {
        currentIndex = (currentIndex + 1) % items.length;
    } else {
        currentIndex = currentIndex <= 0 ? items.length - 1 : currentIndex - 1;
    }
    
    // Set new active
    const newActive = items[currentIndex];
    newActive.classList.add('active');
    newActive.style.background = '#f8f9fd';
    newActive.style.borderLeftColor = '#667eea';
    newActive.style.borderLeftWidth = '3px';
    newActive.style.borderLeftStyle = 'solid';
    
    // Scroll into view
    newActive.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}

/**
 * Show map status message
 */
function showMapStatus(message, type) {
    const statusDiv = document.getElementById('map-status');
    const statusText = document.getElementById('map-status-text');
    
    if (!statusDiv || !statusText) return;
    
    const colors = {
        success: '#d4edda',
        error: '#f8d7da',
        info: '#d1ecf1'
    };
    
    const textColors = {
        success: '#155724',
        error: '#721c24',
        info: '#0c5460'
    };
    
    statusDiv.style.background = colors[type] || colors.info;
    statusText.style.color = textColors[type] || textColors.info;
    statusText.textContent = message;
    statusDiv.style.display = 'block';
    
    // Auto-hide after 3 seconds
    setTimeout(() => {
        statusDiv.style.display = 'none';
    }, 3000);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


/**
 * Reverse geocode coordinates to address
 */
async function reverseGeocode(lat, lng) {
    try {
        const response = await fetch(`/api/reverse-geocode?lat=${lat}&lon=${lng}`);
        
        if (!response.ok) {
            return;
        }

        const result = await response.json();
        
        if (result && result.label) {
            const searchInput = document.getElementById('locationSearch');
            if (searchInput) {
                searchInput.value = result.label;
            }
        }
    } catch (error) {
        console.error('Error reverse geocoding:', error);
    }
}

/**
 * Place or update marker on map
 */
function placeMarker(lat, lng) {
    if (marker) {
        marker.setLatLng([lat, lng]);
    } else {
        marker = L.marker([lat, lng]).addTo(map);
    }
}

/**
 * Search nearby places (restaurants, etc.)
 */
function searchNearbyPlaces(location) {
    // This would need to be implemented with ORS POI or Overpass API
    // For now, show a message
    const placesList = document.getElementById('placesList');
    if (placesList) {
        placesList.innerHTML = '<li class="muted">Nearby places search - Use recommendations API</li>';
    }
}

/**
 * Display route on map from OpenRouteService directions
 */
function displayRoute(directions) {
    // Clear existing route
    if (routePolyline) {
        map.removeLayer(routePolyline);
        routePolyline = null;
    }
    
    if (!directions || !directions.coordinates) {
        console.error('Invalid directions data');
        return;
    }
    
    // Create polyline from coordinates
    const latlngs = directions.coordinates.map(coord => [coord[1], coord[0]]); // [lat, lng]
    
    routePolyline = L.polyline(latlngs, {
        color: '#4285F4',
        weight: 4,
        opacity: 0.8
    }).addTo(map);
    
    // Fit map to route bounds
    map.fitBounds(routePolyline.getBounds());
    
    // Display route summary
    displayRouteSummary(directions);
}

/**
 * Display route summary information
 */
function displayRouteSummary(directions) {
    if (!directionsPanel) {
        directionsPanel = document.createElement('div');
        directionsPanel.id = 'directions-panel';
        directionsPanel.style.cssText = `
            position: absolute;
            top: 10px;
            right: 10px;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.3);
            max-width: 300px;
            max-height: 400px;
            overflow-y: auto;
            z-index: 1000;
        `;
        document.getElementById('map')?.parentElement?.appendChild(directionsPanel);
    }
    
    let html = `
        <div style="margin-bottom: 10px;">
            <strong>Route Summary</strong>
            <button onclick="closeDirections()" style="float:right;border:none;background:none;cursor:pointer;font-size:18px;">×</button>
        </div>
        <div style="margin-bottom: 10px;">
            <div>📍 Distance: <strong>${directions.distance_km.toFixed(1)} km</strong></div>
            <div>🕐 Duration: <strong>${Math.floor(directions.duration_minutes / 60)}h ${Math.round(directions.duration_minutes % 60)}m</strong></div>
            <div>🚗 Mode: <strong>${directions.profile.replace('-', ' ')}</strong></div>
        </div>
    `;
    
    if (directions.steps && directions.steps.length > 0) {
        html += '<div style="border-top: 1px solid #ddd; padding-top: 10px;"><strong>Directions:</strong></div>';
        html += '<ol style="padding-left: 20px; margin-top: 10px;">';
        directions.steps.forEach((step, index) => {
            html += `<li style="margin-bottom: 8px; font-size: 13px;">${step.instruction} <span style="color: #666;">(${step.distance_km.toFixed(1)} km)</span></li>`;
        });
        html += '</ol>';
    }
    
    directionsPanel.innerHTML = html;
}

/**
 * Close directions panel
 */
function closeDirections() {
    if (directionsPanel) {
        directionsPanel.remove();
        directionsPanel = null;
    }
    if (routePolyline) {
        map.removeLayer(routePolyline);
        routePolyline = null;
    }
}

/**
 * Display isochrones (reachability areas) on map
 */
function displayIsochrones(isochroneData) {
    // Clear existing isochrones
    clearIsochrones();
    
    if (!isochroneData || !isochroneData.polygons) {
        console.error('Invalid isochrone data');
        return;
    }
    
    const colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8'];
    
    isochroneData.polygons.forEach((polygon, index) => {
        if (polygon.geometry && polygon.geometry.coordinates) {
            const coordinates = polygon.geometry.coordinates[0].map(coord => [coord[1], coord[0]]); // [lat, lng]
            
            const isochronePolygon = L.polygon(coordinates, {
                color: colors[index % colors.length],
                fillColor: colors[index % colors.length],
                fillOpacity: 0.2,
                weight: 2
            }).addTo(map);
            
            isochroneLayers.push(isochronePolygon);
        }
    });
    
    // Fit map to include all isochrones
    if (isochroneLayers.length > 0) {
        const group = L.featureGroup(isochroneLayers);
        map.fitBounds(group.getBounds());
    }
}

/**
 * Clear all isochrones from map
 */
function clearIsochrones() {
    isochroneLayers.forEach(layer => map.removeLayer(layer));
    isochroneLayers = [];
}

/**
 * Get directions between two points using OpenRouteService
 */
async function getDirections(start, end, profile = 'driving-car') {
    try {
        const response = await fetch('/api/directions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                start_lat: start.lat,
                start_lon: start.lng,
                end_lat: end.lat,
                end_lon: end.lng,
                profile: profile,
                alternatives: 1
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to get directions');
        }
        
        const directions = await response.json();
        displayRoute(directions);
        return directions;
    } catch (error) {
        console.error('Error getting directions:', error);
        alert('Could not get directions. Please try again.');
    }
}

/**
 * Get restaurant directions from user location
 */
async function getRestaurantDirections(restaurantLat, restaurantLon, profile = 'driving-car') {
    try {
        // Try to get user's real-time location first
        let userLocation = null;
        
        if (typeof window.getUserLocationForRoute === 'function') {
            try {
                userLocation = await window.getUserLocationForRoute();
                console.log('Using real-time user location:', userLocation);
            } catch (locationError) {
                console.warn('Could not get real-time location:', locationError);
            }
        }
        
        // If real-time location available, use direct directions API
        if (userLocation) {
            const response = await fetch('/api/directions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    start_lat: userLocation.lat,
                    start_lon: userLocation.lng,
                    end_lat: restaurantLat,
                    end_lon: restaurantLon,
                    profile: profile
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to get directions');
            }
            
            const directions = await response.json();
            displayRoute(directions);
            return directions;
        } else {
            // Fall back to restaurant-directions API which uses saved home location
            const response = await fetch('/api/restaurant-directions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    restaurant_lat: restaurantLat,
                    restaurant_lon: restaurantLon,
                    profile: profile
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to get restaurant directions');
            }

            const directions = await response.json();
            displayRoute(directions);
            return directions;
        }
    } catch (error) {
        console.error('Error getting restaurant directions:', error);
        alert('Could not get directions to restaurant. Please enable location access or set your home location in settings.');
    }
}

/**
 * Generate and display isochrones
 */
async function generateIsochrones(lat, lon, ranges = [300, 600, 900], profile = 'driving-car') {
    try {
        const response = await fetch('/api/isochrones', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lat: lat,
                lon: lon,
                profile: profile,
                range_type: 'time',
                ranges: ranges
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to generate isochrones');
        }
        
        const isochroneData = await response.json();
        displayIsochrones(isochroneData);
        return isochroneData;
    } catch (error) {
        console.error('Error generating isochrones:', error);
        alert('Could not generate reachability areas. Please try again.');
    }
}

/**
 * Create search container wrapper
 */
function createSearchContainer(input) {
    const parent = input.parentElement;
    const container = document.createElement('div');
    container.className = 'map-search-container';
    
    // Set container styles individually
    container.style.position = 'relative';
    container.style.display = 'block';
    container.style.width = '100%';
    
    parent.insertBefore(container, input);
    container.appendChild(input);
    
    // Add styling to input - make sure it doesn't override button visibility
    input.style.paddingRight = '120px';
    input.style.boxSizing = 'border-box';
    input.style.width = '100%';
    
    return container;
}

/**
 * Format distance for display
 */
function formatDistance(meters) {
    return meters < 1000 ? `${Math.round(meters)}m` : `${(meters / 1000).toFixed(1)}km`;
}

// Expose functions globally for use in other scripts
window.displayRoute = displayRoute;
window.closeDirections = closeDirections;
window.displayIsochrones = displayIsochrones;
window.clearIsochrones = clearIsochrones;
window.getDirections = getDirections;
window.getRestaurantDirections = getRestaurantDirections;
window.generateIsochrones = generateIsochrones;
window.calculateDistance = calculateDistance;
window.formatDistance = formatDistance;

// Initialize map when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMap);
} else {
    initMap();
}
