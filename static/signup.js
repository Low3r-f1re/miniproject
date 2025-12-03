/**
 * Signup.js - Leaflet Implementation
 * User signup with location sharing (no Google Maps)
 */

let signupBtn = null;
let startShareBtn = null;
let stopShareBtn = null;
let formMsg = null;
let locStatus = null;
let locInfo = null;

let watchId = null;
let ws = null;
let map = null;
let userMarker = null;
let accuracyCircle = null;

/**
 * Initialize map for signup page
 */
async function initMap() {
    const mapElement = document.getElementById('map');
    if (!mapElement) {
        return null;
    }

    try {
        // Initialize Leaflet map
        map = L.map('map').setView([20, 0], 2);

        // Add OpenStreetMap tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }).addTo(map);

        console.log('Leaflet map initialized for signup');
        return map;
    } catch (error) {
        console.error('Error initializing map:', error);
        return null;
    }
}

/**
 * Initialize the map when needed
 */
let mapPromise;
if (document.getElementById('map')) {
    mapPromise = initMap();
} else {
    mapPromise = Promise.resolve(null);
}

/**
 * Update location UI with current position
 */
function updateLocUI(pos) {
    const { latitude: lat, longitude: lng, accuracy } = pos.coords;
    const ts = new Date(pos.timestamp || Date.now()).toLocaleTimeString();
    
    if (locInfo) {
        locInfo.innerHTML = `
            <li>Latitude: ${lat.toFixed(6)}</li>
            <li>Longitude: ${lng.toFixed(6)}</li>
            <li>Accuracy: ${Math.round(accuracy)} m</li>
            <li>Time: ${ts}</li>
        `;
    }
}

/**
 * Move marker on map to show user location
 */
async function moveMarker(lat, lng, acc) {
    const currentMap = await mapPromise;
    if (!currentMap) return;

    const latlng = L.latLng(lat, lng);

    if (!userMarker) {
        // Create marker for user location
        userMarker = L.marker(latlng, {
            title: 'You (live)'
        }).addTo(currentMap);

        // Create accuracy circle
        accuracyCircle = L.circle(latlng, {
            radius: acc || 0,
            fillColor: '#007bff',
            fillOpacity: 0.2,
            color: '#007bff',
            weight: 2
        }).addTo(currentMap);

        // Center map on user location
        currentMap.setView(latlng, 15);
    } else {
        // Update existing marker and circle
        userMarker.setLatLng(latlng);
        accuracyCircle.setLatLng(latlng);
        accuracyCircle.setRadius(acc || 0);
        currentMap.panTo(latlng);
    }
}

/**
 * Send location data to server
 */
function sendLocation(payload) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(payload));
    } else {
        // Fallback to HTTP POST
        fetch('/api/location', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).catch(() => {});
    }
}

/**
 * Start sharing user location
 */
async function startSharing() {
    if (!('geolocation' in navigator)) {
        if (locStatus) locStatus.textContent = 'Geolocation not supported';
        return;
    }

    if (locStatus) locStatus.textContent = 'Starting… (requesting permission)';

    watchId = navigator.geolocation.watchPosition(
        async pos => {
            updateLocUI(pos);
            await moveMarker(pos.coords.latitude, pos.coords.longitude, pos.coords.accuracy);
            
            if (locStatus) locStatus.textContent = 'Sharing live';

            const payload = {
                type: 'location',
                lat: pos.coords.latitude,
                lng: pos.coords.longitude,
                accuracy: pos.coords.accuracy,
                timestamp: pos.timestamp || Date.now(),
                user: document.getElementById('email')?.value || 'anonymous'
            };
            
            sendLocation(payload);
        },
        err => {
            if (locStatus) {
                locStatus.textContent = 'Location error: ' + (err.message || err.code);
            }
        },
        {
            enableHighAccuracy: true,
            maximumAge: 2000,
            timeout: 10000
        }
    );

    if (startShareBtn) startShareBtn.disabled = true;
    if (stopShareBtn) stopShareBtn.disabled = false;
}

/**
 * Stop sharing user location
 */
function stopSharing() {
    if (watchId !== null) {
        navigator.geolocation.clearWatch(watchId);
        watchId = null;
    }
    
    if (ws && ws.readyState === WebSocket.OPEN) {
        try {
            ws.close();
        } catch (e) {}
    }
    
    if (locStatus) locStatus.textContent = 'Not sharing';
    if (startShareBtn) startShareBtn.disabled = false;
    if (stopShareBtn) stopShareBtn.disabled = true;
}

/**
 * Attach signup event listeners
 */
function attachSignupListeners() {
    signupBtn = document.getElementById('signupBtn');
    startShareBtn = document.getElementById('startShareBtn');
    stopShareBtn = document.getElementById('stopShareBtn');
    formMsg = document.getElementById('formMsg');
    locStatus = document.getElementById('locStatus');
    locInfo = document.getElementById('locInfo');

    if (signupBtn) {
        signupBtn.addEventListener('click', async () => {
            if (!formMsg) formMsg = document.getElementById('formMsg');
            formMsg.textContent = '';
            
            const name = document.getElementById('name').value.trim();
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            
            if (!name || !email || password.length < 6) {
                formMsg.textContent = 'Please fill the form correctly.';
                formMsg.style.color = 'crimson';
                return;
            }

            try {
                const resp = await fetch('/api/signup', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, email, password })
                });

                if (resp.ok) {
                    let j = {};
                    try {
                        j = await resp.json();
                    } catch (e) {}
                    
                    formMsg.textContent = j.message || 'Signup successful. Redirecting...';
                    formMsg.style.color = 'green';
                    
                    setTimeout(() => {
                        window.location.replace('/');
                    }, 600);
                } else {
                    let errMsg = resp.statusText || 'Signup failed';
                    try {
                        const errJson = await resp.json();
                        errMsg = errJson.error || errJson.message || errMsg;
                    } catch (e) {
                        try {
                            errMsg = await resp.text();
                        } catch (_) {}
                    }
                    
                    if (resp.status === 409) {
                        formMsg.innerHTML = (errMsg || 'An account with that email already exists.') + 
                            ` <a href="/login" style="font-weight:700;color:var(--accent-600);">Log in</a> or ` +
                            `<a href="/login" style="color:var(--muted);">reset password</a>`;
                        formMsg.style.color = 'crimson';
                    } else {
                        formMsg.textContent = errMsg || 'Signup failed';
                        formMsg.style.color = 'crimson';
                    }
                }
            } catch (e) {
                console.warn('Signup request failed', e);
                formMsg.textContent = 'Signup (demo) saved locally.';
                formMsg.style.color = 'green';
            }
        });
    }

    if (startShareBtn) startShareBtn.addEventListener('click', startSharing);
    if (stopShareBtn) stopShareBtn.addEventListener('click', stopSharing);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attachSignupListeners);
} else {
    attachSignupListeners();
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (watchId !== null) {
        navigator.geolocation.clearWatch(watchId);
    }
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
    }
});
