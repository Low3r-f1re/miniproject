/**
 * Location Permission System - Google Maps/Airbnb-style
 * Handles geolocation, manual entry, autocomplete, and backend integration
 */

class LocationPermissionSystem {
    constructor() {
        this.currentStep = 'permission';
        this.selectedLocation = null;
        this.autocompleteTimeout = null;
        this.apiBaseUrl = window.location.origin;
        
        this.init();
    }

    init() {
        // Get DOM elements
        this.elements = {
            overlay: document.getElementById('locationOverlay'),
            modal: document.getElementById('locationModal'),
            
            // Steps
            permissionStep: document.getElementById('permissionStep'),
            manualStep: document.getElementById('manualStep'),
            whyStep: document.getElementById('whyStep'),
            loadingStep: document.getElementById('loadingStep'),
            successStep: document.getElementById('successStep'),
            errorStep: document.getElementById('errorStep'),
            
            // Buttons
            allowLocationBtn: document.getElementById('allowLocationBtn'),
            enterManuallyBtn: document.getElementById('enterManuallyBtn'),
            whyNeedBtn: document.getElementById('whyNeedBtn'),
            backToPermissionBtn: document.getElementById('backToPermissionBtn'),
            backFromWhyBtn: document.getElementById('backFromWhyBtn'),
            saveLocationBtn: document.getElementById('saveLocationBtn'),
            continueBtn: document.getElementById('continueBtn'),
            retryBtn: document.getElementById('retryBtn'),
            
            // Form elements
            manualLocationForm: document.getElementById('manualLocationForm'),
            cityInput: document.getElementById('cityInput'),
            cityInputSpinner: document.getElementById('cityInputSpinner'),
            autocompleteDropdown: document.getElementById('autocompleteDropdown'),
            manualError: document.getElementById('manualError'),
            
            // Messages
            loadingMessage: document.getElementById('loadingMessage'),
            successMessage: document.getElementById('successMessage'),
            errorMessage: document.getElementById('errorMessage')
        };

        this.attachEventListeners();
        this.checkExistingLocation();
    }

    attachEventListeners() {
        // Primary action buttons
        this.elements.allowLocationBtn.addEventListener('click', () => this.requestGeolocation());
        this.elements.enterManuallyBtn.addEventListener('click', () => this.showStep('manual'));
        this.elements.whyNeedBtn.addEventListener('click', () => this.showStep('why'));
        
        // Navigation buttons
        this.elements.backToPermissionBtn.addEventListener('click', () => this.showStep('permission'));
        this.elements.backFromWhyBtn.addEventListener('click', () => this.showStep('permission'));
        this.elements.continueBtn.addEventListener('click', () => this.closeModal());
        this.elements.retryBtn.addEventListener('click', () => this.showStep('manual'));
        
        // Form submission
        this.elements.manualLocationForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleManualSubmit();
        });
        
        // Autocomplete
        this.elements.cityInput.addEventListener('input', (e) => {
            this.handleAutocompleteInput(e.target.value);
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.elements.cityInput.contains(e.target) && 
                !this.elements.autocompleteDropdown.contains(e.target)) {
                this.hideAutocomplete();
            }
        });
    }

    async checkExistingLocation() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/me`, {
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                
                // If user has saved location, don't show modal
                if (data.authenticated && data.home_latitude && data.home_longitude) {
                    console.log('User has saved location:', {
                        city: data.home_city,
                        country: data.home_country,
                        lat: data.home_latitude,
                        lon: data.home_longitude
                    });
                    this.closeModal();
                    return;
                }
            }
            
            // Show modal if no saved location
            this.showStep('permission');
        } catch (error) {
            console.error('Error checking existing location:', error);
            this.showStep('permission');
        }
    }

    showStep(stepName) {
        // Hide all steps
        Object.keys(this.elements).forEach(key => {
            if (key.endsWith('Step')) {
                this.elements[key].classList.add('hidden');
            }
        });
        
        // Show target step
        const targetStep = this.elements[`${stepName}Step`];
        if (targetStep) {
            targetStep.classList.remove('hidden');
            this.currentStep = stepName;
        }
    }

    requestGeolocation() {
        this.showStep('loading');
        this.elements.loadingMessage.textContent = 'Getting your location...';
        
        if (!navigator.geolocation) {
            this.showError('Geolocation is not supported by your browser');
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (position) => this.handleGeolocationSuccess(position),
            (error) => this.handleGeolocationError(error),
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            }
        );
    }

    async handleGeolocationSuccess(position) {
        const latitude = position.coords.latitude;
        const longitude = position.coords.longitude;
        
        console.log('GPS location obtained:', { latitude, longitude });
        
        this.elements.loadingMessage.textContent = 'Looking up your location...';
        
        try {
            // Reverse geocode to get city/country
            const response = await fetch(
                `${this.apiBaseUrl}/api/reverse-geocode?lat=${latitude}&lon=${longitude}`,
                { credentials: 'include' }
            );
            
            if (!response.ok) {
                throw new Error('Failed to reverse geocode location');
            }
            
            const locationData = await response.json();
            
            // Save location to backend
            await this.saveLocation({
                latitude,
                longitude,
                city: locationData.locality || locationData.name || 'Unknown',
                country: locationData.country || 'Unknown',
                source: 'gps'
            });
            
        } catch (error) {
            console.error('Error processing GPS location:', error);
            
            // Still save GPS coordinates even if reverse geocoding fails
            await this.saveLocation({
                latitude,
                longitude,
                city: 'Unknown',
                country: 'Unknown',
                source: 'gps'
            });
        }
    }

    handleGeolocationError(error) {
        console.error('Geolocation error:', error);
        
        let errorMsg = '';
        switch (error.code) {
            case error.PERMISSION_DENIED:
                errorMsg = 'Location access was denied. Please enter your location manually.';
                break;
            case error.POSITION_UNAVAILABLE:
                errorMsg = 'Location information is unavailable. Please enter your location manually.';
                break;
            case error.TIMEOUT:
                errorMsg = 'Location request timed out. Please try again or enter manually.';
                break;
            default:
                errorMsg = 'An unknown error occurred. Please enter your location manually.';
        }
        
        this.showError(errorMsg);
    }

    handleAutocompleteInput(query) {
        // Clear previous timeout
        if (this.autocompleteTimeout) {
            clearTimeout(this.autocompleteTimeout);
        }
        
        // Hide dropdown if query is too short
        if (query.trim().length < 2) {
            this.hideAutocomplete();
            return;
        }
        
        // Show loading spinner
        this.elements.cityInputSpinner.classList.remove('hidden');
        
        // Debounce the autocomplete request
        this.autocompleteTimeout = setTimeout(() => {
            this.fetchAutocomplete(query);
        }, 300);
    }

    async fetchAutocomplete(query) {
        try {
            const response = await fetch(
                `${this.apiBaseUrl}/api/location/autocomplete?query=${encodeURIComponent(query)}`,
                { credentials: 'include' }
            );
            
            if (!response.ok) {
                throw new Error('Failed to fetch autocomplete results');
            }
            
            const data = await response.json();
            this.displayAutocomplete(data.suggestions || []);
            
        } catch (error) {
            console.error('Autocomplete error:', error);
            this.hideAutocomplete();
        } finally {
            this.elements.cityInputSpinner.classList.add('hidden');
        }
    }

    displayAutocomplete(suggestions) {
        const dropdown = this.elements.autocompleteDropdown;
        dropdown.innerHTML = '';
        
        if (!suggestions || suggestions.length === 0) {
            dropdown.innerHTML = '<div class="autocomplete-empty">No locations found</div>';
            dropdown.classList.remove('hidden');
            return;
        }
        
        suggestions.forEach(suggestion => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';
            item.innerHTML = `
                <div class="autocomplete-item-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                        <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z" 
                              stroke="currentColor" stroke-width="2" fill="none"/>
                        <circle cx="12" cy="9" r="2.5" fill="currentColor"/>
                    </svg>
                </div>
                <div class="autocomplete-item-content">
                    <div class="autocomplete-item-name">${this.escapeHtml(suggestion.name)}</div>
                    <div class="autocomplete-item-details">${this.escapeHtml(suggestion.label)}</div>
                </div>
            `;
            
            item.addEventListener('click', () => {
                this.selectLocation(suggestion);
            });
            
            dropdown.appendChild(item);
        });
        
        dropdown.classList.remove('hidden');
    }

    selectLocation(location) {
        this.selectedLocation = location;
        this.elements.cityInput.value = location.label;
        this.hideAutocomplete();
    }

    hideAutocomplete() {
        this.elements.autocompleteDropdown.classList.add('hidden');
        this.elements.autocompleteDropdown.innerHTML = '';
    }

    async handleManualSubmit() {
        const cityValue = this.elements.cityInput.value.trim();
        
        if (!cityValue) {
            this.showManualError('Please enter a city or location');
            return;
        }
        
        this.showStep('loading');
        this.elements.loadingMessage.textContent = 'Locating your city...';
        
        try {
            let location;
            
            // If user selected from autocomplete, use that
            if (this.selectedLocation && this.selectedLocation.label === cityValue) {
                location = this.selectedLocation;
            } else {
                // Otherwise, geocode the entered text
                const response = await fetch(
                    `${this.apiBaseUrl}/api/geocode?location=${encodeURIComponent(cityValue)}`,
                    { credentials: 'include' }
                );
                
                if (!response.ok) {
                    throw new Error('Failed to geocode location');
                }
                
                location = await response.json();
            }
            
            // Save location to backend
            await this.saveLocation({
                latitude: location.latitude,
                longitude: location.longitude,
                city: location.locality || location.name || cityValue,
                country: location.country || 'Unknown',
                source: 'manual'
            });
            
        } catch (error) {
            console.error('Error processing manual location:', error);
            this.showManualError('Could not find that location. Please try a different city name.');
            this.showStep('manual');
        }
    }

    async saveLocation(locationData) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/user/location`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    home_city: locationData.city,
                    home_country: locationData.country,
                    home_latitude: locationData.latitude,
                    home_longitude: locationData.longitude
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to save location');
            }
            
            const result = await response.json();
            console.log('Location saved successfully:', result);
            
            this.showSuccess(locationData);
            
        } catch (error) {
            console.error('Error saving location:', error);
            this.showError('Failed to save your location. Please try again.');
        }
    }

    showSuccess(locationData) {
        this.showStep('success');
        
        const cityCountry = locationData.country && locationData.country !== 'Unknown'
            ? `${locationData.city}, ${locationData.country}`
            : locationData.city;
        
        this.elements.successMessage.textContent = 
            `Your location has been saved as ${cityCountry}. You'll now get personalized recommendations!`;
    }

    showError(message) {
        this.showStep('error');
        this.elements.errorMessage.textContent = message;
    }

    showManualError(message) {
        this.elements.manualError.textContent = message;
        this.elements.manualError.classList.remove('hidden');
    }

    closeModal() {
        this.elements.overlay.style.display = 'none';
        
        // Redirect to dashboard or reload
        const redirectUrl = new URLSearchParams(window.location.search).get('redirect');
        if (redirectUrl) {
            window.location.href = redirectUrl;
        } else {
            // Reload to update the page with location data
            window.location.reload();
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.locationSystem = new LocationPermissionSystem();
    });
} else {
    window.locationSystem = new LocationPermissionSystem();
}
