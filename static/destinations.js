/**
 * Destinations.js - Leaflet + ORS Implementation
 * Manages destinations list and map display without Google APIs
 */

let map;
let destMarkers = [];
let destMarkerMap = {};

/**
 * Initialize the destinations page
 */
document.addEventListener('DOMContentLoaded', () => {
    // Initialize map if element exists
    if (document.getElementById('map')) {
        initDestinationsMap();
    }

    // Initialize destinations CRUD
    initDestinationsCRUD();
    
    // Initial load of destinations
    fetchDestinations();
});

/**
 * Initialize Leaflet map for destinations page
 */
function initDestinationsMap() {
    try {
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

        map = L.map('map').setView([20, 0], 2);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }).addTo(map);

        // Initialize location search
        const searchInput = document.getElementById('locationSearch');
        if (searchInput) {
            initLocationSearch(searchInput);
        }

        console.log('Destinations map initialized');
    } catch (error) {
        console.error('Error initializing map:', error);
        const mapEl = document.getElementById('map');
        if (mapEl) {
            mapEl.innerHTML = '<div style="padding:20px;text-align:center;color:#666;">Map could not be loaded</div>';
        }
    }
}

/**
 * Initialize location search with modern autocomplete dropdown
 */
function initLocationSearch(input) {
    let searchTimeout = null;
    
    // Create search container wrapper
    const parent = input.parentElement;
    const container = document.createElement('div');
    container.className = 'map-search-container';
    container.style.position = 'relative';
    container.style.display = 'block';
    container.style.width = '100%';
    
    parent.insertBefore(container, input);
    container.appendChild(input);
    
    // Style input to make room for buttons
    input.style.paddingRight = '120px';
    input.style.boxSizing = 'border-box';
    input.style.width = '100%';
    
    // Create search button
    const searchButton = document.createElement('button');
    searchButton.type = 'button';
    searchButton.innerHTML = '<i class="fas fa-search"></i> Search';
    searchButton.style.position = 'absolute';
    searchButton.style.right = '40px';
    searchButton.style.top = '8px';
    searchButton.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
    searchButton.style.color = 'white';
    searchButton.style.border = 'none';
    searchButton.style.borderRadius = '6px';
    searchButton.style.padding = '8px 14px';
    searchButton.style.cursor = 'pointer';
    searchButton.style.fontSize = '13px';
    searchButton.style.fontWeight = '600';
    searchButton.style.zIndex = '1000';
    searchButton.style.height = '32px';
    searchButton.style.boxShadow = '0 2px 8px rgba(102, 126, 234, 0.3)';
    container.appendChild(searchButton);
    
    // Create dropdown arrow
    const toggleArrow = document.createElement('button');
    toggleArrow.type = 'button';
    toggleArrow.innerHTML = '<i class="fas fa-chevron-down"></i>';
    toggleArrow.style.position = 'absolute';
    toggleArrow.style.right = '8px';
    toggleArrow.style.top = '50%';
    toggleArrow.style.transform = 'translateY(-50%)';
    toggleArrow.style.background = 'transparent';
    toggleArrow.style.color = '#667eea';
    toggleArrow.style.border = 'none';
    toggleArrow.style.cursor = 'pointer';
    toggleArrow.style.padding = '8px';
    toggleArrow.style.fontSize = '14px';
    toggleArrow.style.zIndex = '1000';
    container.appendChild(toggleArrow);
    
    // Create dropdown for suggestions
    const dropdown = document.createElement('div');
    dropdown.style.position = 'absolute';
    dropdown.style.top = 'calc(100% + 5px)';
    dropdown.style.left = '0';
    dropdown.style.right = '0';
    dropdown.style.background = 'white';
    dropdown.style.border = '1px solid #e0e0e0';
    dropdown.style.borderRadius = '8px';
    dropdown.style.boxShadow = '0 8px 24px rgba(0, 0, 0, 0.15)';
    dropdown.style.maxHeight = '400px';
    dropdown.style.overflowY = 'auto';
    dropdown.style.display = 'none';
    dropdown.style.zIndex = '2000';
    container.appendChild(dropdown);
    
    let currentSuggestions = [];

    // Input event for autocomplete
    input.addEventListener('input', async function(e) {
        const query = e.target.value.trim();
        
        if (searchTimeout) clearTimeout(searchTimeout);

        if (query.length < 2) {
            dropdown.style.display = 'none';
            return;
        }

        // Show loading
        dropdown.innerHTML = '<div style="padding:20px;text-align:center;color:#666;"><i class="fas fa-spinner fa-spin"></i><div style="margin-top:8px;font-size:13px;">Searching...</div></div>';
        dropdown.style.display = 'block';

        searchTimeout = setTimeout(async () => {
            try {
                const response = await fetch(`/api/location/autocomplete?query=${encodeURIComponent(query)}`);
                if (!response.ok) {
                    dropdown.style.display = 'none';
                    return;
                }
                const data = await response.json();
                const suggestions = data.suggestions || [];
                currentSuggestions = suggestions;
                
                if (suggestions.length === 0) {
                    dropdown.innerHTML = '<div style="padding:20px;text-align:center;color:#999;"><i class="fas fa-search" style="font-size:24px;opacity:0.3;"></i><div style="font-size:13px;margin-top:8px;">No locations found</div></div>';
                } else {
                    displaySuggestions(suggestions, dropdown, input);
                }
            } catch (error) {
                console.error('Error fetching suggestions:', error);
                dropdown.style.display = 'none';
            }
        }, 300);
    });

    // Enter key or search button to geocode
    const performSearch = () => {
        const query = input.value.trim();
        if (query) {
            dropdown.style.display = 'none';
            searchLocation(query);
        }
    };
    
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            performSearch();
        } else if (e.key === 'Escape') {
            dropdown.style.display = 'none';
        }
    });
    
    searchButton.addEventListener('click', performSearch);
    
    toggleArrow.addEventListener('click', () => {
        dropdown.style.display = dropdown.style.display === 'block' ? 'none' : (currentSuggestions.length > 0 ? 'block' : 'none');
    });
    
    // Click outside to close
    document.addEventListener('click', (e) => {
        if (!container.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    });
    
    function displaySuggestions(suggestions, dropdown, input) {
        dropdown.innerHTML = '';
        suggestions.forEach((suggestion) => {
            const item = document.createElement('div');
            item.style.padding = '12px 15px';
            item.style.cursor = 'pointer';
            item.style.borderBottom = '1px solid #f0f0f0';
            
            const locationParts = [];
            if (suggestion.name) locationParts.push(suggestion.name);
            if (suggestion.locality && suggestion.locality !== suggestion.name) locationParts.push(suggestion.locality);
            if (suggestion.region) locationParts.push(suggestion.region);
            if (suggestion.country) locationParts.push(suggestion.country);
            const locationText = locationParts.join(', ');
            
            item.innerHTML = `
                <div style="display:flex;align-items:start;gap:10px;">
                    <i class="fas fa-map-marker-alt" style="color:#667eea;margin-top:3px;"></i>
                    <div style="flex:1;">
                        <div style="font-weight:600;color:#333;margin-bottom:2px;">${escapeHtml(suggestion.name || suggestion.label)}</div>
                        <div style="font-size:12px;color:#666;">${escapeHtml(locationText)}</div>
                    </div>
                </div>
            `;
            
            item.addEventListener('mouseenter', function() {
                this.style.background = '#f8f9fd';
                this.style.borderLeft = '3px solid #667eea';
            });
            
            item.addEventListener('mouseleave', function() {
                this.style.background = 'white';
                this.style.borderLeft = 'none';
            });
            
            item.addEventListener('click', function() {
                input.value = suggestion.label;
                dropdown.style.display = 'none';
                if (suggestion.latitude && suggestion.longitude && map) {
                    map.setView([suggestion.latitude, suggestion.longitude], 13);
                }
            });
            
            dropdown.appendChild(item);
        });
        dropdown.style.display = 'block';
    }
    
    console.log('Modern search initialized');
}

/**
 * Search for a location using ORS Geocoding
 */
async function searchLocation(query) {
    try {
        const response = await fetch(`/api/geocode?location=${encodeURIComponent(query)}`);
        
        if (!response.ok) {
            console.error('Geocoding failed');
            return;
        }

        const result = await response.json();
        
        if (result && result.latitude && result.longitude && map) {
            map.setView([result.latitude, result.longitude], 12);
        }
    } catch (error) {
        console.error('Error searching location:', error);
    }
}

/**
 * Initialize destinations CRUD functionality
 */
function initDestinationsCRUD() {
    const addBtn = document.getElementById('addDestinationBtn');
    const titleInput = document.getElementById('destTitle');
    const catInput = document.getElementById('destCategory');
    const budgetInput = document.getElementById('destBudget');
    const descInput = document.getElementById('destDescription');
    const websiteInput = document.getElementById('destWebsite');
    const msg = document.getElementById('destMessage');

    if (addBtn) {
        addBtn.addEventListener('click', async () => {
            if (!msg) return;
            msg.textContent = '';
            const title = (titleInput?.value || '').trim();
            if (!title) {
                msg.textContent = 'Please enter a destination name';
                msg.style.color = '#e74c3c';
                return;
            }

            const body = {
                title,
                description: (descInput?.value || '').trim(),
                category: (catInput?.value || '').trim(),
                budget_tier: (budgetInput?.value || '').trim(),
                website: (websiteInput?.value || '').trim()
            };

            try {
                const resp = await fetch('/api/destinations', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                });

                if (!resp.ok) {
                    const err = await resp.json().catch(() => ({error: 'Failed to save'}));
                    msg.textContent = err.error || 'Could not save destination';
                    msg.style.color = '#e74c3c';
                    return;
                }

                msg.textContent = 'Destination saved!';
                msg.style.color = '#27ae60';

                // Clear form
                titleInput.value = '';
                descInput.value = '';
                catInput.value = 'cities';
                budgetInput.value = 'budget';
                websiteInput.value = '';

                fetchDestinations();
            } catch (e) {
                msg.textContent = 'Error saving destination';
                msg.style.color = '#e74c3c';
            }
        });
    }
}

/**
 * Fetch all destinations from the API
 */
async function fetchDestinations() {
    const list = document.getElementById('destinationsList');
    if (!list) return;

    try {
        const resp = await fetch('/api/destinations');
        if (!resp.ok) throw new Error('Could not load destinations');
        const data = await resp.json();
        renderDestinations(data || []);
        addDestinationMarkers(data || []);
    } catch (e) {
        list.innerHTML = '<div style="text-align: center; color: #e74c3c; padding: 20px;">Could not load destinations</div>';
    }
}

/**
 * Render destinations list
 */
function renderDestinations(items) {
    const list = document.getElementById('destinationsList');
    const count = document.getElementById('destCount');
    const totalCount = document.getElementById('totalDestinations');

    if (!list) return;

    if (count) count.textContent = items.length;
    if (totalCount) totalCount.textContent = items.length;

    if (!items.length) {
        list.innerHTML = `
            <div style="text-align: center; color: #999; padding: 40px 20px;">
                <i class="fas fa-map-marked-alt" style="font-size: 48px; margin-bottom: 15px; opacity: 0.5;"></i>
                <p>No destinations saved yet</p>
                <p style="font-size: 14px;">Add your first destination using the form!</p>
            </div>
        `;
        return;
    }

    list.innerHTML = '';
    items.forEach(d => {
        const div = document.createElement('div');
        div.className = 'destination-item';
        div.innerHTML = `
            <div class="destination-content">
                <div class="destination-header">
                    <strong>${escapeHtml(d.title)}</strong>
                    <div class="destination-actions">
                        ${d.latitude && d.longitude ? `
                            <button class="btn-small btn-outline" onclick="viewOnMap(${d.id})">
                                <i class="fas fa-map-marker-alt"></i> View
                            </button>
                        ` : ''}
                        <button class="btn-small btn-outline" onclick="editDestination(${d.id}, '${escapeHtml(d.title)}', '${escapeHtml(d.description || '')}', '${d.category || ''}', '${d.budget_tier || ''}', '${escapeHtml(d.website || '')}')">
                            <i class="fas fa-edit"></i> Edit
                        </button>
                        <button class="btn-small btn-danger" onclick="deleteDestination(${d.id})">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                    </div>
                </div>
                <div class="destination-meta">
                    <span class="tag">${d.category || 'City'}</span>
                    <span class="budget">${d.budget_tier || 'Budget'}</span>
                </div>
                ${d.description ? `<div class="destination-notes">${escapeHtml(d.description)}</div>` : ''}
                ${d.website ? `<div class="destination-website"><a href="${escapeHtml(d.website)}" target="_blank">Visit Website <i class="fas fa-external-link-alt"></i></a></div>` : ''}
            </div>
        `;
        list.appendChild(div);
    });
}

/**
 * View destination on map
 */
window.viewOnMap = function(destId) {
    if (!map) return;
    
    const marker = destMarkerMap[destId];
    if (marker) {
        map.setView(marker.getLatLng(), 12);
        marker.openPopup();
        
        // Bounce effect simulation
        const originalIcon = marker.getIcon();
        marker.setIcon(L.icon({
            iconUrl: '/static/images/leaflet/marker-icon-2x.png',
            shadowUrl: '/static/images/leaflet/marker-shadow.png',
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
            shadowSize: [41, 41]
        }));
        
        setTimeout(() => {
            marker.setIcon(originalIcon);
        }, 1500);
    }
};

/**
 * Edit destination
 */
window.editDestination = async function(id, currentTitle, currentDesc, currentCat, currentBudget, currentWebsite) {
    const newTitle = prompt('Edit destination name:', currentTitle);
    if (!newTitle || newTitle.trim() === currentTitle) return;

    const payload = {
        title: newTitle.trim(),
        description: currentDesc,
        category: currentCat,
        budget_tier: currentBudget,
        website: currentWebsite
    };

    try {
        const resp = await fetch('/api/destinations/' + id, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!resp.ok) {
            alert('Could not update destination');
            return;
        }

        fetchDestinations();
    } catch (err) {
        alert('Update failed');
    }
};

/**
 * Delete destination
 */
window.deleteDestination = async function(id) {
    if (!confirm('Are you sure you want to delete this destination?')) return;

    try {
        const resp = await fetch('/api/destinations/' + id, { method: 'DELETE' });
        if (!resp.ok) throw new Error('Delete failed');
        fetchDestinations();
    } catch (err) {
        alert('Could not delete destination');
    }
};

/**
 * Add markers for all destinations on the map
 */
function addDestinationMarkers(items) {
    if (!map) return;

    // Clear existing markers
    clearDestinationMarkers();

    const bounds = L.latLngBounds();
    let markerCount = 0;

    items.forEach(d => {
        if (!d.latitude || !d.longitude) return;

        try {
            const latLng = L.latLng(parseFloat(d.latitude), parseFloat(d.longitude));
            
            const marker = L.marker(latLng).addTo(map);
            
            // Create popup content
            const thumb = `<img src="${escapeHtml(formatThumbnail(d))}" style="width:100%;height:120px;object-fit:cover;border-radius:6px;margin-bottom:6px;"/>`;
            const websiteHtml = d.website ? `<div style="margin-top:6px"><a href="${escapeHtml(formatWebsite(d.website))}" target="_blank" rel="noopener" class="small-link">Open site</a></div>` : '';
            
            const popupContent = `
                <div style="min-width:220px">
                    ${thumb}
                    <strong>${escapeHtml(d.title)}</strong>
                    <div class="muted">${escapeHtml(d.description || '')}</div>
                    <div style="margin-top:6px;">
                        <small class="muted">${d.category || ''} ${d.budget_tier ? '· ' + d.budget_tier : ''}</small>
                    </div>
                    ${websiteHtml}
                </div>
            `;
            
            marker.bindPopup(popupContent);
            
            // Store marker reference
            destMarkers.push(marker);
            destMarkerMap[String(d.id)] = marker;
            
            bounds.extend(latLng);
            markerCount += 1;
        } catch (e) {
            console.warn('Marker add failed', e);
        }
    });

    // Adjust map viewport to show all markers
    if (markerCount === 1) {
        map.setView(bounds.getCenter(), 10);
    } else if (markerCount > 1) {
        map.fitBounds(bounds, { padding: [40, 40] });
    }
}

/**
 * Clear all destination markers
 */
function clearDestinationMarkers() {
    destMarkers.forEach(marker => {
        map.removeLayer(marker);
    });
    destMarkers = [];
    destMarkerMap = {};
}

/**
 * Format website URL
 */
function formatWebsite(url) {
    if (!url) return '';
    const trimmed = String(url).trim();
    if (/^https?:\/\//i.test(trimmed)) return trimmed;
    return 'https://' + trimmed;
}

/**
 * Format thumbnail image URL
 */
function formatThumbnail(d) {
    const cat = (d.category || '').toLowerCase().trim();
    const mapping = {
        'cities': '/static/images/cities.svg',
        'city': '/static/images/cities.svg',
        'beaches': '/static/images/beaches.svg',
        'beach': '/static/images/beaches.svg',
        'mountains': '/static/images/mountains.svg',
        'mountain': '/static/images/mountains.svg',
        'cultural': '/static/images/cultural.svg',
        'museum': '/static/images/cultural.svg'
    };
    if (cat && mapping[cat]) return mapping[cat];
    return '/static/images/default.svg';
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(s) {
    return String(s || '').replace(/[&<>"']/g, c => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }[c]));
}

/**
 * Calculate distance between two points (Haversine formula)
 */
function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371; // Earth radius in km
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
              Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c * 1000; // Return in meters
}

/**
 * Convert degrees to radians
 */
function toRad(value) {
    return value * Math.PI / 180;
}

/**
 * Format distance for display
 */
function formatDistance(meters) {
    return meters < 1000 ? `${Math.round(meters)}m` : `${(meters / 1000).toFixed(1)}km`;
}

// Export for use in other scripts
window.destMarkers = destMarkers;
window.destMarkerMap = destMarkerMap;
