/**
 * Transport Display Module
 * Modern UI component for displaying transportation options with costs,
 * distance, and travel times for trip planning
 */

(function() {
    'use strict';

    // Store destination info for route viewing
    let currentDestination = null;

    /**
     * Display transportation options in a modern card format
     * @param {Object} transportDetails - Transportation details from API
     * @param {string} containerId - ID of container element
     * @param {Object} destination - Destination info {lat, lon, name}
     */
    window.displayTransportOptions = function(transportDetails, containerId = 'transportOptions', destination = null) {
        const container = document.getElementById(containerId);
        if (!container) {
            console.warn(`Container ${containerId} not found`);
            return;
        }

        if (!transportDetails || !transportDetails.all_options) {
            container.innerHTML = '<p class="text-muted">Transportation details not available</p>';
            return;
        }

        // Store destination for route viewing
        currentDestination = destination;

        const { distance_km, recommended_mode, all_options } = transportDetails;

        // Create modern transport card
        const html = `
            <div class="transport-options-card">
                <!-- Header -->
                <div class="transport-header">
                    <h4 class="transport-title">
                        <i class="fas fa-route"></i>
                        Transportation Options
                    </h4>
                    <div class="transport-distance-badge">
                        <i class="fas fa-map-marker-alt"></i>
                        ${distance_km} km
                    </div>
                </div>

                <!-- Recommended Option (Highlighted) -->
                ${recommended_mode && all_options[recommended_mode] ? `
                    <div class="transport-recommended">
                        <div class="recommended-label">
                            <i class="fas fa-star"></i>
                            Recommended
                        </div>
                        ${createTransportModeCard(recommended_mode, all_options[recommended_mode], true)}
                    </div>
                ` : ''}

                <!-- All Transport Options -->
                <div class="transport-options-grid">
                    ${Object.entries(all_options)
                        .filter(([mode]) => mode !== recommended_mode)
                        .map(([mode, details]) => createTransportModeCard(mode, details, false))
                        .join('')}
                </div>

                <!-- Travel Tips -->
                <div class="transport-tips">
                    <div class="tip-icon"><i class="fas fa-lightbulb"></i></div>
                    <div class="tip-content">
                        <strong>Travel Tip:</strong> Prices are estimates for round trip per person. 
                        Book in advance for better deals, especially for flights and trains.
                    </div>
                </div>
            </div>
        `;

        container.innerHTML = html;

        // Add event listeners for interactive elements
        addTransportInteractivity(containerId);
    };

    /**
     * Create individual transport mode card
     */
    function createTransportModeCard(mode, details, isRecommended) {
        if (!details.available) {
            return '';
        }

        const { icon, name, one_way_cost, round_trip_cost, duration } = details;
        
        return `
            <div class="transport-mode-card ${isRecommended ? 'recommended-card' : ''}" data-mode="${mode}">
                <div class="transport-icon-wrapper">
                    <span class="transport-icon">${icon}</span>
                </div>
                <div class="transport-details">
                    <h5 class="transport-name">${name}</h5>
                    <div class="transport-time">
                        <i class="fas fa-clock"></i>
                        <span>${duration}</span>
                    </div>
                </div>
                <div class="transport-cost">
                    <div class="cost-label">Round Trip</div>
                    <div class="cost-value">₹${formatCost(round_trip_cost)}</div>
                    <div class="cost-sublabel">₹${formatCost(one_way_cost)} one way</div>
                </div>
                ${isRecommended ? '<div class="best-value-badge">Best Value</div>' : ''}
                <button class="btn-route-view" data-mode="${mode}" style="width: 100%; margin-top: 12px;">
                    <i class="fas fa-map-marked-alt"></i>
                    View Route
                </button>
            </div>
        `;
    }

    /**
     * Format cost with thousand separators
     */
    function formatCost(amount) {
        return new Intl.NumberFormat('en-IN').format(Math.round(amount));
    }

    /**
     * Add interactive features to transport cards
     */
    function addTransportInteractivity(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        // Add click handlers to "View Route" buttons
        const routeButtons = container.querySelectorAll('.btn-route-view');
        routeButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.stopPropagation(); // Prevent card click event
                
                const mode = this.dataset.mode;
                console.log(`View route clicked for mode: ${mode}`);
                
                // Use Google Maps for all route directions
                if (currentDestination && typeof openGoogleMapsDirections === 'function') {
                    const { lat, lon, name } = currentDestination;
                    
                    // Format destination as coordinates for precise location
                    const destination = `${lat},${lon}`;
                    
                    // Open Google Maps with directions
                    openGoogleMapsDirections(destination, name);
                } else {
                    console.warn('Destination info or openGoogleMapsDirections function not available');
                    
                    // Fallback: try to open Google Maps with destination name
                    if (currentDestination && currentDestination.name) {
                        const fallbackUrl = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(currentDestination.name)}`;
                        window.open(fallbackUrl, '_blank');
                    } else {
                        alert('Destination information is not available. Please try again.');
                    }
                }
            });
        });

        // Add click handlers to transport cards
        const cards = container.querySelectorAll('.transport-mode-card');
        cards.forEach(card => {
            card.addEventListener('click', function() {
                // Remove active class from all cards
                cards.forEach(c => c.classList.remove('active'));
                
                // Add active class to clicked card
                this.classList.add('active');
                
                // Get mode details
                const mode = this.dataset.mode;
                console.log(`Selected transport mode: ${mode}`);
                
                // Emit custom event for other parts of the app
                const event = new CustomEvent('transportModeSelected', {
                    detail: { mode }
                });
                window.dispatchEvent(event);
            });

            // Add hover effect
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-4px)';
            });

            card.addEventListener('mouseleave', function() {
                if (!this.classList.contains('active')) {
                    this.style.transform = 'translateY(0)';
                }
            });
        });
    }

    /**
     * Display compact transport summary (for smaller spaces)
     */
    window.displayTransportSummary = function(transportDetails, containerId = 'transportSummary') {
        const container = document.getElementById(containerId);
        if (!container || !transportDetails) return;

        const { distance_km, recommended_mode, recommended_cost_round_trip, all_options } = transportDetails;
        const recommended = all_options[recommended_mode];

        if (!recommended) {
            container.innerHTML = '<p class="text-muted">Transportation info not available</p>';
            return;
        }

        const html = `
            <div class="transport-summary-compact">
                <div class="summary-icon">${recommended.icon}</div>
                <div class="summary-details">
                    <div class="summary-title">
                        ${recommended.name}
                        <span class="summary-badge">Recommended</span>
                    </div>
                    <div class="summary-info">
                        <span><i class="fas fa-map-marker-alt"></i> ${distance_km} km</span>
                        <span><i class="fas fa-clock"></i> ${recommended.duration}</span>
                        <span><i class="fas fa-rupee-sign"></i> ₹${formatCost(recommended_cost_round_trip)}</span>
                    </div>
                </div>
                <button class="summary-expand-btn" onclick="expandTransportOptions()">
                    <i class="fas fa-chevron-down"></i>
                    View All
                </button>
            </div>
        `;

        container.innerHTML = html;
    };

    /**
     * Expand transport options from summary
     */
    window.expandTransportOptions = function() {
        const fullContainer = document.getElementById('transportOptions');
        if (fullContainer) {
            fullContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            
            // Add highlight animation
            fullContainer.classList.add('highlight-pulse');
            setTimeout(() => {
                fullContainer.classList.remove('highlight-pulse');
            }, 2000);
        }
    };

    /**
     * Add comparison view for transport options
     */
    window.displayTransportComparison = function(transportDetails, containerId = 'transportComparison') {
        const container = document.getElementById(containerId);
        if (!container || !transportDetails || !transportDetails.all_options) return;

        const modes = Object.entries(transportDetails.all_options)
            .filter(([, details]) => details.available)
            .sort((a, b) => a[1].round_trip_cost - b[1].round_trip_cost);

        const html = `
            <div class="transport-comparison-table">
                <table class="comparison-table">
                    <thead>
                        <tr>
                            <th>Mode</th>
                            <th>Duration</th>
                            <th>Cost (Round Trip)</th>
                            <th>Per Person</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${modes.map(([mode, details]) => `
                            <tr class="${mode === transportDetails.recommended_mode ? 'recommended-row' : ''}">
                                <td>
                                    <span class="mode-icon">${details.icon}</span>
                                    ${details.name}
                                    ${mode === transportDetails.recommended_mode ? '<span class="badge-sm">Recommended</span>' : ''}
                                </td>
                                <td>${details.duration}</td>
                                <td class="cost-cell">₹${formatCost(details.round_trip_cost)}</td>
                                <td class="cost-cell">₹${formatCost(details.one_way_cost)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;

        container.innerHTML = html;
    };

    /**
     * Create CSS styles for transport display
     */
    function injectStyles() {
        if (document.getElementById('transport-display-styles')) return;

        const style = document.createElement('style');
        style.id = 'transport-display-styles';
        style.textContent = `
            /* Transport Options Card */
            .transport-options-card {
                background: white;
                border-radius: 16px;
                padding: 24px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
                margin: 20px 0;
            }

            .transport-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                padding-bottom: 16px;
                border-bottom: 2px solid #f0f0f0;
            }

            .transport-title {
                margin: 0;
                font-size: 1.5rem;
                font-weight: 700;
                color: #1f2937;
                display: flex;
                align-items: center;
                gap: 10px;
            }

            .transport-title i {
                color: #667eea;
            }

            .transport-distance-badge {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: 700;
                display: flex;
                align-items: center;
                gap: 6px;
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
            }

            /* Recommended Section */
            .transport-recommended {
                background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 20px;
            }

            .recommended-label {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                background: rgba(255, 255, 255, 0.9);
                color: #d97706;
                padding: 6px 12px;
                border-radius: 20px;
                font-weight: 700;
                font-size: 0.875rem;
                margin-bottom: 12px;
            }

            .recommended-label i {
                color: #f59e0b;
            }

            /* Transport Options Grid */
            .transport-options-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 16px;
                margin-bottom: 20px;
            }

            /* Transport Mode Card */
            .transport-mode-card {
                background: white;
                border: 2px solid #e5e7eb;
                border-radius: 12px;
                padding: 16px;
                cursor: pointer;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
                overflow: hidden;
            }

            .transport-mode-card:hover {
                border-color: #667eea;
                box-shadow: 0 8px 24px rgba(102, 126, 234, 0.15);
                transform: translateY(-2px);
            }

            .transport-mode-card.active {
                border-color: #667eea;
                background: linear-gradient(135deg, #f0f4ff 0%, #e8f0fe 100%);
                transform: translateY(-2px);
            }

            .transport-mode-card.recommended-card {
                border-color: #d97706;
                background: rgba(255, 236, 210, 0.3);
            }

            .transport-icon-wrapper {
                display: flex;
                align-items: center;
                justify-content: center;
                width: 56px;
                height: 56px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 12px;
                margin-bottom: 12px;
            }

            .transport-icon {
                font-size: 2rem;
            }

            .transport-details {
                margin-bottom: 12px;
            }

            .transport-name {
                margin: 0 0 6px 0;
                font-size: 1.1rem;
                font-weight: 700;
                color: #1f2937;
            }

            .transport-time {
                display: flex;
                align-items: center;
                gap: 6px;
                color: #6b7280;
                font-size: 0.875rem;
            }

            .transport-time i {
                color: #667eea;
            }

            .transport-cost {
                padding-top: 12px;
                border-top: 1px solid #e5e7eb;
            }

            .cost-label {
                font-size: 0.75rem;
                color: #6b7280;
                text-transform: uppercase;
                font-weight: 600;
                letter-spacing: 0.05em;
                margin-bottom: 4px;
            }

            .cost-value {
                font-size: 1.5rem;
                font-weight: 800;
                color: #667eea;
                margin-bottom: 4px;
            }

            .cost-sublabel {
                font-size: 0.875rem;
                color: #9ca3af;
            }

            .best-value-badge {
                position: absolute;
                top: 12px;
                right: 12px;
                background: #10b981;
                color: white;
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 0.75rem;
                font-weight: 700;
            }

            /* Transport Tips */
            .transport-tips {
                background: #f0f9ff;
                border-left: 4px solid #3b82f6;
                border-radius: 8px;
                padding: 16px;
                display: flex;
                gap: 12px;
                align-items: start;
            }

            .tip-icon {
                font-size: 1.5rem;
                color: #3b82f6;
                flex-shrink: 0;
            }

            .tip-content {
                font-size: 0.875rem;
                color: #1e40af;
                line-height: 1.6;
            }

            /* Compact Summary */
            .transport-summary-compact {
                background: white;
                border-radius: 12px;
                padding: 16px;
                display: flex;
                align-items: center;
                gap: 16px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
                margin: 16px 0;
            }

            .summary-icon {
                font-size: 2.5rem;
                flex-shrink: 0;
            }

            .summary-details {
                flex: 1;
            }

            .summary-title {
                font-weight: 700;
                color: #1f2937;
                margin-bottom: 6px;
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .summary-badge {
                background: #fef3c7;
                color: #92400e;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 0.75rem;
                font-weight: 600;
            }

            .summary-info {
                display: flex;
                flex-wrap: wrap;
                gap: 16px;
                font-size: 0.875rem;
                color: #6b7280;
            }

            .summary-info span {
                display: flex;
                align-items: center;
                gap: 4px;
            }

            .summary-info i {
                color: #667eea;
            }

            .summary-expand-btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: 600;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 6px;
                transition: all 0.3s;
                white-space: nowrap;
            }

            .summary-expand-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
            }

            /* Highlight animation */
            @keyframes highlightPulse {
                0%, 100% { box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); }
                50% { box-shadow: 0 8px 24px rgba(102, 126, 234, 0.3); }
            }

            .highlight-pulse {
                animation: highlightPulse 1s ease-in-out 2;
            }

            /* Comparison Table */
            .transport-comparison-table {
                background: white;
                border-radius: 12px;
                padding: 20px;
                overflow-x: auto;
            }

            .comparison-table {
                width: 100%;
                border-collapse: collapse;
            }

            .comparison-table th {
                background: #f9fafb;
                padding: 12px;
                text-align: left;
                font-weight: 700;
                color: #374151;
                border-bottom: 2px solid #e5e7eb;
            }

            .comparison-table td {
                padding: 12px;
                border-bottom: 1px solid #f3f4f6;
            }

            .comparison-table tr:hover {
                background: #f9fafb;
            }

            .recommended-row {
                background: #fef3c7;
            }

            .recommended-row:hover {
                background: #fde68a;
            }

            .mode-icon {
                font-size: 1.25rem;
                margin-right: 8px;
            }

            .cost-cell {
                font-weight: 700;
                color: #667eea;
            }

            .badge-sm {
                background: #f59e0b;
                color: white;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 0.75rem;
                margin-left: 8px;
            }

            /* Route View Button */
            .btn-route-view {
                background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: 600;
                font-size: 0.9rem;
                cursor: pointer;
                transition: all 0.3s;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                box-shadow: 0 4px 12px rgba(79, 172, 254, 0.3);
            }

            .btn-route-view:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(79, 172, 254, 0.4);
            }

            .btn-route-view i {
                font-size: 1rem;
            }

            /* Responsive Design */
            @media (max-width: 768px) {
                .transport-options-grid {
                    grid-template-columns: 1fr;
                }

                .transport-header {
                    flex-direction: column;
                    gap: 12px;
                    align-items: flex-start;
                }

                .transport-summary-compact {
                    flex-direction: column;
                    text-align: center;
                }

                .summary-info {
                    justify-content: center;
                }

                .summary-expand-btn {
                    width: 100%;
                    justify-content: center;
                }
            }
        `;

        document.head.appendChild(style);
    }

    // Inject styles when module loads
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', injectStyles);
    } else {
        injectStyles();
    }

    console.log('Transport Display Module loaded');
})();
