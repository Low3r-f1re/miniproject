/**
 * location.js - Real-Time User Location Tracking for Leaflet
 * Provides real-time GPS location tracking and "Locate Me" functionality
 */

let userMarker = null;
let accuracyCircle = null;
let watchId = null;
let currentUserLocation = null;

/**
 * Initialize real-time location tracking
 * @param {L.Map} map - Leaflet map instance
 */
function initRealTimeLocation(map) {
    if (!navigator.geolocation) {
        console.error("Geolocation not supported by this browser");
        showLocationError("Geolocation not supported by your browser");
        return;
    }

    console.log("Initializing real-time location tracking...");

    function updatePosition(position) {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        const accuracy = position.coords.accuracy;

        console.log(`Location update: ${lat}, ${lng} (accuracy: ${accuracy}m)`);

        // Store current location for use in other features
        currentUserLocation = { lat, lng, accuracy };

        // Create or update user marker
        if (!userMarker) {
            // Create custom icon for user location
            const userIcon = L.icon({
                iconUrl: "https://cdn-icons-png.flaticon.com/512/684/684908.png",
                iconSize: [40, 40],
                iconAnchor: [20, 40],
                popupAnchor: [0, -40]
            });

            userMarker = L.marker([lat, lng], {
                icon: userIcon,
                zIndexOffset: 1000 // Ensure user marker appears on top
            }).addTo(map);

            userMarker.bindPopup("<b>Your Location</b><br>Accuracy: " + Math.round(accuracy) + "m");

            // Create accuracy circle
            accuracyCircle = L.circle([lat, lng], {
                radius: accuracy,
                color: "#4285F4",
                fillColor: "#4285F4",
                fillOpacity: 0.1,
                weight: 2
            }).addTo(map);

            // Center map on user location (first time only)
            map.setView([lat, lng], 15);

            showLocationSuccess("Location tracking active");
        } else {
            // Update existing marker and circle
            userMarker.setLatLng([lat, lng]);
            userMarker.getPopup().setContent("<b>Your Location</b><br>Accuracy: " + Math.round(accuracy) + "m");
            
            accuracyCircle.setLatLng([lat, lng]);
            accuracyCircle.setRadius(accuracy);
        }

        // Update search box with current location (reverse geocode)
        updateSearchWithUserLocation(lat, lng);

        // Dispatch custom event for other components to use
        window.dispatchEvent(new CustomEvent('userLocationUpdate', {
            detail: { lat, lng, accuracy }
        }));
    }

    function handleError(err) {
        console.error("Location error:", err.message);
        
        let errorMessage = "Unable to get your location";
        
        switch(err.code) {
            case err.PERMISSION_DENIED:
                errorMessage = "Location permission denied. Please enable location access.";
                break;
            case err.POSITION_UNAVAILABLE:
                errorMessage = "Location information unavailable.";
                break;
            case err.TIMEOUT:
                errorMessage = "Location request timed out.";
                break;
        }
        
        showLocationError(errorMessage);
    }

    // Start watching position
    watchId = navigator.geolocation.watchPosition(updatePosition, handleError, {
        enableHighAccuracy: true,
        maximumAge: 0,
        timeout: 10000
    });

    console.log("Location tracking started with watch ID:", watchId);
}

/**
 * Stop real-time location tracking
 */
function stopRealTimeLocation() {
    if (watchId !== null) {
        navigator.geolocation.clearWatch(watchId);
        watchId = null;
        console.log("Location tracking stopped");
    }
}

/**
 * Get current user location (one-time)
 * @returns {Promise<{lat: number, lng: number, accuracy: number}>}
 */
function getCurrentUserLocation() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error("Geolocation not supported"));
            return;
        }

        if (currentUserLocation) {
            resolve(currentUserLocation);
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (position) => {
                const location = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude,
                    accuracy: position.coords.accuracy
                };
                currentUserLocation = location;
                resolve(location);
            },
            (error) => {
                reject(error);
            },
            {
                enableHighAccuracy: true,
                maximumAge: 5000,
                timeout: 10000
            }
        );
    });
}

/**
 * Add "Locate Me" button to map
 * @param {L.Map} map - Leaflet map instance
 */
function addLocateMeButton(map) {
    const button = L.control({ position: "topright" });

    button.onAdd = function () {
        const div = L.DomUtil.create("div", "locate-me-btn");
        div.innerHTML = '<i class="fas fa-location-arrow"></i> Locate Me';
        
        // Style the button
        div.style.padding = "10px 15px";
        div.style.background = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)";
        div.style.color = "white";
        div.style.borderRadius = "8px";
        div.style.cursor = "pointer";
        div.style.fontWeight = "600";
        div.style.fontSize = "14px";
        div.style.boxShadow = "0 2px 8px rgba(102, 126, 234, 0.4)";
        div.style.transition = "all 0.3s";
        div.style.border = "none";
        div.style.display = "flex";
        div.style.alignItems = "center";
        div.style.gap = "8px";

        // Hover effects
        div.addEventListener('mouseenter', function() {
            this.style.transform = "scale(1.05)";
            this.style.boxShadow = "0 4px 12px rgba(102, 126, 234, 0.6)";
        });

        div.addEventListener('mouseleave', function() {
            this.style.transform = "scale(1)";
            this.style.boxShadow = "0 2px 8px rgba(102, 126, 234, 0.4)";
        });

        // Click handler
        div.onclick = function(e) {
            L.DomEvent.stopPropagation(e);
            locateUser(map);
        };

        return div;
    };

    button.addTo(map);
    console.log("Locate Me button added to map");
}

/**
 * Locate user and center map on their position
 * @param {L.Map} map - Leaflet map instance
 */
function locateUser(map) {
    if (!navigator.geolocation) {
        showLocationError("Geolocation not supported");
        return;
    }

    showLocationInfo("Getting your location...");

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            
            // Center map on user location
            map.setView([lat, lng], 15);
            
            // Update/create marker if needed
            if (userMarker) {
                userMarker.openPopup();
            }
            
            showLocationSuccess("Location found!");
        },
        (error) => {
            console.error("Error getting location:", error);
            showLocationError("Unable to get your location");
        },
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        }
    );
}

/**
 * Update search box with user location (reverse geocode)
 */
async function updateSearchWithUserLocation(lat, lng) {
    try {
        const response = await fetch(`/api/reverse-geocode?lat=${lat}&lon=${lng}`);
        
        if (response.ok) {
            const result = await response.json();
            
            // Store location name for later use
            if (result.label) {
                localStorage.setItem('userLocationName', result.label);
                
                // Optionally update search input if user hasn't typed anything
                const searchInput = document.getElementById('locationSearch');
                if (searchInput && !searchInput.value) {
                    searchInput.placeholder = `Near ${result.label}`;
                }
            }
        }
    } catch (error) {
        console.error('Error reverse geocoding user location:', error);
    }
}

/**
 * Calculate distance from user location to a point
 * @param {number} lat - Target latitude
 * @param {number} lng - Target longitude
 * @returns {number|null} Distance in kilometers, or null if user location unavailable
 */
function calculateDistanceFromUser(lat, lng) {
    if (!currentUserLocation) {
        return null;
    }

    return calculateDistance(
        currentUserLocation.lat,
        currentUserLocation.lng,
        lat,
        lng
    );
}

/**
 * Calculate distance between two points (Haversine formula)
 * @param {number} lat1 - First point latitude
 * @param {number} lng1 - First point longitude
 * @param {number} lat2 - Second point latitude
 * @param {number} lng2 - Second point longitude
 * @returns {number} Distance in kilometers
 */
function calculateDistance(lat1, lng1, lat2, lng2) {
    const R = 6371; // Earth's radius in km
    const dLat = toRad(lat2 - lat1);
    const dLng = toRad(lng2 - lng1);
    
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
              Math.sin(dLng / 2) * Math.sin(dLng / 2);
    
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const distance = R * c;
    
    return distance;
}

function toRad(degrees) {
    return degrees * (Math.PI / 180);
}

/**
 * Get user location for route planning
 * @returns {Promise<{lat: number, lng: number}>}
 */
async function getUserLocationForRoute() {
    if (currentUserLocation) {
        return {
            lat: currentUserLocation.lat,
            lng: currentUserLocation.lng
        };
    }
    
    return await getCurrentUserLocation();
}

/**
 * Show location success message
 */
function showLocationSuccess(message) {
    showLocationMessage(message, 'success');
}

/**
 * Show location error message
 */
function showLocationError(message) {
    showLocationMessage(message, 'error');
}

/**
 * Show location info message
 */
function showLocationInfo(message) {
    showLocationMessage(message, 'info');
}

/**
 * Show location-related message
 */
function showLocationMessage(message, type) {
    // Try to use existing map status function
    if (typeof window.showMapStatus === 'function') {
        window.showMapStatus(message, type);
        return;
    }

    // Fallback: create simple toast notification
    const toast = document.createElement('div');
    toast.className = 'location-toast';
    toast.textContent = message;
    
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
    
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${colors[type] || colors.info};
        color: ${textColors[type] || textColors.info};
        padding: 12px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 10000;
        font-weight: 500;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Expose functions globally for use in other scripts
window.initRealTimeLocation = initRealTimeLocation;
window.stopRealTimeLocation = stopRealTimeLocation;
window.getCurrentUserLocation = getCurrentUserLocation;
window.addLocateMeButton = addLocateMeButton;
window.calculateDistanceFromUser = calculateDistanceFromUser;
window.getUserLocationForRoute = getUserLocationForRoute;

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
    
    .locate-me-btn:active {
        transform: scale(0.95) !important;
    }
`;
document.head.appendChild(style);

console.log("Location.js module loaded successfully");
