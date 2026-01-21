const AppMap = {
    map: null,
    markers: [],
    countryLayers: {},
    heatmapLayer: null,
    heatmapData: [],
    
    init: function() {
        // Initialize Leaflet Map
        this.map = L.map('map', {
            zoomControl: false,
            attributionControl: false
        }).setView([20, 0], 2.5);

        // Add Dark Tile Layer
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            maxZoom: 19,
            opacity: 1.0
        }).addTo(this.map);
        
        // Initialize heatmap layer
        this.initializeHeatmapLayer();
        
        // Initialize country layers for statistical visualization
        this.initializeCountryLayers();
    },

    initializeHeatmapLayer: function() {
        // Create heatmap container
        const heatmapContainer = document.createElement('div');
        heatmapContainer.id = 'heatmap-layer';
        heatmapContainer.className = 'heatmap-layer';
        document.getElementById('map').appendChild(heatmapContainer);
        
        this.heatmapLayer = heatmapContainer;
    },

    initializeCountryLayers: function() {
        // Create country boundary layers for statistical display
        DATA.COUNTRIES.forEach(country => {
            // Create a simple circle marker for each country
            const countryMarker = L.circleMarker([country.lat, country.lng], {
                radius: 3,
                color: 'rgba(0, 243, 255, 0.2)',
                fillColor: 'rgba(0, 243, 255, 0.1)',
                fillOpacity: 0.2,
                weight: 1,
                className: 'country-base-marker'
            }).addTo(this.map);
            
            countryMarker.bindTooltip(`
                <div class="country-tooltip">
                    <strong>${country.name}</strong><br>
                    <span class="country-code">${country.code}</span><br>
                    <span class="country-region">${country.region}</span>
                </div>
            `, {
                permanent: false,
                direction: 'top',
                className: 'custom-tooltip'
            });
            
            this.countryLayers[country.code] = {
                marker: countryMarker,
                country: country,
                errorCount: 0,
                totalCount: 0,
                lastErrorTime: 0
            };
        });
    },

    addHeatmapPoint: function(lat, lng, intensity, type = 'error') {
        const point = document.createElement('div');
        point.className = `heatmap-point ${type}`;
        
        // Convert lat/lng to pixel coordinates
        const pointLayer = this.map.latLngToContainerPoint([lat, lng]);
        
        point.style.left = pointLayer.x + 'px';
        point.style.top = pointLayer.y + 'px';
        
        // Set intensity-based styling
        if (intensity < 0.3) {
            point.classList.add('low');
        } else if (intensity < 0.6) {
            point.classList.add('medium');
        } else if (intensity < 0.8) {
            point.classList.add('high');
        } else {
            point.classList.add('critical');
        }
        
        this.heatmapLayer.appendChild(point);
        
        // Store reference for cleanup
        this.heatmapData.push({
            element: point,
            lat: lat,
            lng: lng,
            intensity: intensity,
            timestamp: Date.now()
        });
        
        // Auto-remove after animation
        setTimeout(() => {
            if (point.parentNode) {
                point.parentNode.removeChild(point);
            }
        }, 5000);
    },

    updateHeatmapForCountry: function(countryCode, errorRate) {
        const layer = this.countryLayers[countryCode];
        if (layer) {
            const intensity = Math.min(errorRate / 50, 1); // Cap at 50% error rate
            
            // Add multiple heatmap points around the country center
            for (let i = 0; i < Math.floor(intensity * 5) + 1; i++) {
                // Add some randomness to spread the points
                const offsetLat = (Math.random() - 0.5) * 2; // ±1 degree
                const offsetLng = (Math.random() - 0.5) * 2;
                
                this.addHeatmapPoint(
                    layer.country.lat + offsetLat,
                    layer.country.lng + offsetLng,
                    intensity,
                    'error'
                );
            }
            
            // Update country marker appearance based on error rate
            this.updateCountryMarkerAppearance(layer, errorRate);
        }
    },

    updateCountryMarkerAppearance: function(layer, errorRate) {
        if (errorRate > 20) {
            // Critical error rate
            layer.marker.setStyle({
                radius: 8,
                color: '#FF0000',
                fillColor: '#FF4500',
                fillOpacity: 0.9,
                weight: 3,
                className: 'country-critical-marker pulse-critical'
            });
        } else if (errorRate > 10) {
            // High error rate
            layer.marker.setStyle({
                radius: 6,
                color: '#FF4500',
                fillColor: '#FF8C00',
                fillOpacity: 0.8,
                weight: 2,
                className: 'country-high-marker pulse-high'
            });
        } else if (errorRate > 5) {
            // Medium error rate
            layer.marker.setStyle({
                radius: 5,
                color: '#FFA500',
                fillColor: '#FFD700',
                fillOpacity: 0.6,
                weight: 2,
                className: 'country-medium-marker pulse-medium'
            });
        } else if (errorRate > 1) {
            // Low error rate
            layer.marker.setStyle({
                radius: 4,
                color: '#00F3FF',
                fillColor: '#40E0D0',
                fillOpacity: 0.4,
                weight: 1,
                className: 'country-low-marker pulse-low'
            });
        } else {
            // Minimal error rate - reset to base
            layer.marker.setStyle({
                radius: 3,
                color: 'rgba(0, 243, 255, 0.2)',
                fillColor: 'rgba(0, 243, 255, 0.1)',
                fillOpacity: 0.2,
                weight: 1,
                className: 'country-base-marker'
            });
        }
    },

    addMarker: function(item) {
        // 1. Add to heatmap
        if (item.has_error) {
            this.addHeatmapPoint(
                item.coordinates.lat,
                item.coordinates.lng,
                0.8, // High intensity for errors
                'error'
            );
            
            // Update country visualization
            const countryCode = item.country_name.substring(0, 3).toUpperCase();
            if (this.countryLayers[countryCode]) {
                this.countryLayers[countryCode].errorCount++;
                this.countryLayers[countryCode].totalCount++;
                this.countryLayers[countryCode].lastErrorTime = Date.now();
                
                const errorRate = (this.countryLayers[countryCode].errorCount / this.countryLayers[countryCode].totalCount) * 100;
                this.updateHeatmapForCountry(countryCode, errorRate);
            }
        } else {
            // Add low-intensity heatmap point for valid items
            this.addHeatmapPoint(
                item.coordinates.lat,
                item.coordinates.lng,
                0.2, // Low intensity for valid items
                'valid'
            );
        }
        
        // 2. Add VISIBLE Marker (Restored from map.js)
        const color = item.has_error ? '#FF4500' : '#00F3FF';
        const radius = item.has_error ? 8 : 4;
        const className = item.has_error ? 'pulse-marker' : '';

        const marker = L.circleMarker([item.coordinates.lat, item.coordinates.lng], {
            radius: radius,
            color: color,
            fillColor: color,
            fillOpacity: item.has_error ? 0.8 : 0.4,
            weight: item.has_error ? 2 : 0,
            className: className
        }).addTo(this.map);

        // Enhanced Popup Content
        const popupContent = `
            <div class="popup-content">
                <div class="popup-header">
                    <span class="popup-country">${item.country_name}</span>
                    <span class="popup-timestamp">${item.timestamp.split('T')[1].split('.')[0]}</span>
                </div>
                <div class="popup-headline">"${item.headline}"</div>
                ${item.has_error ? `
                    <div class="popup-error-section">
                        <div class="popup-error">
                            <span class="error-label">DETECTED ERROR:</span>
                            <span class="error-word">${item.error_detail.error_word}</span>
                        </div>
                        <div class="popup-correction">
                            <span class="correction-label">CORRECTED TO:</span>
                            <span class="corrected-word">${item.error_detail.corrected_word}</span>
                        </div>
                        <div class="popup-analysis">
                            <span class="analysis-type">ERROR TYPE:</span>
                            <span class="analysis-result">Typographical Error</span>
                        </div>
                    </div>
                ` : `
                    <div class="popup-valid">
                        <span class="valid-indicator">✓</span>
                        <span class="valid-text">No spelling errors detected</span>
                    </div>
                `}
                <div class="popup-metrics">
                    <span class="metric">Confidence: ${Math.floor(Math.random() * 20 + 80)}%</span>
                </div>
            </div>
        `;

        marker.bindPopup(popupContent);
        
        // Auto open popup for errors sometimes
        if (item.has_error && Math.random() > 0.7) {
            marker.openPopup();
            setTimeout(() => marker.closePopup(), 3000);
        }

        this.markers.push({
            instance: marker,
            timestamp: Date.now(),
            country: item.country_name
        });
        
        // Cleanup old heatmap data AND markers
        this.cleanupHeatmap();
    },

    clearHeatmap: function() {
        // Clear all points from the heatmap layer
        if (this.heatmapLayer) {
            this.heatmapLayer.innerHTML = '';
        }
        
        // Clear references
        this.heatmapData = [];
    },

    createMinimalPopup: function(item) {
        // Deprecated in favor of restored visible markers
    },

    cleanupHeatmap: function() {
        const now = Date.now();
        const maxAge = 10000; // 10 seconds
        
        // Remove old heatmap points
        this.heatmapData = this.heatmapData.filter(data => {
            if (now - data.timestamp > maxAge) {
                if (data.element.parentNode) {
                    data.element.parentNode.removeChild(data.element);
                }
                return false;
            }
            return true;
        });
        
        // Cleanup old markers (Increased limit to 50 like original)
        if (this.markers.length > 50) {
            const toRemove = this.markers.splice(0, this.markers.length - 50);
            toRemove.forEach(m => {
                if (m.instance._map) {
                    this.map.removeLayer(m.instance);
                }
            });
        }
    },

    // Scientific analysis methods
    getRegionalErrorRates: function() {
        const regions = {};
        
        Object.values(this.countryLayers).forEach(layer => {
            if (!regions[layer.country.region]) {
                regions[layer.country.region] = {
                    totalErrors: 0,
                    totalItems: 0,
                    countries: 0,
                    avgErrorRate: 0
                };
            }
            
            regions[layer.country.region].totalErrors += layer.errorCount;
            regions[layer.country.region].totalItems += layer.totalCount;
            regions[layer.country.region].countries++;
        });
        
        // Calculate average error rates
        Object.keys(regions).forEach(region => {
            const r = regions[region];
            r.avgErrorRate = r.totalItems > 0 ? (r.totalErrors / r.totalItems * 100).toFixed(1) : 0;
        });
        
        return regions;
    },

    getBehavioralFingerprintData: function() {
        // Analyze patterns for behavioral fingerprinting
        const fingerprint = {
            geographicDistribution: {},
            temporalPatterns: {},
            errorIntensity: {},
            hotspots: []
        };
        
        // Analyze country error patterns
        Object.values(this.countryLayers).forEach(layer => {
            if (layer.errorCount > 0) {
                fingerprint.geographicDistribution[layer.country.code] = {
                    name: layer.country.name,
                    errorCount: layer.errorCount,
                    errorRate: (layer.errorCount / layer.totalCount * 100).toFixed(1),
                    intensity: this.calculateIntensity(layer.errorCount, layer.lastErrorTime)
                };
            }
        });
        
        // Find hotspots (countries with highest error rates)
        fingerprint.hotspots = Object.values(this.countryLayers)
            .filter(layer => layer.totalCount > 0)
            .map(layer => ({
                country: layer.country.name,
                code: layer.country.code,
                errorRate: (layer.errorCount / layer.totalCount * 100),
                errorCount: layer.errorCount,
                coordinates: [layer.country.lat, layer.country.lng]
            }))
            .sort((a, b) => b.errorRate - a.errorRate)
            .slice(0, 10);
        
        return fingerprint;
    },

    calculateIntensity: function(errorCount, lastErrorTime) {
        const timeDecay = Math.exp(-(Date.now() - lastErrorTime) / (24 * 60 * 60 * 1000)); // 24-hour decay
        const countFactor = Math.log(errorCount + 1) / Math.log(10); // Logarithmic scaling
        return Math.min((countFactor * timeDecay * 100).toFixed(1), 100);
    },

    // Heatmap intensity data for timeline
    getHeatmapIntensityForTimeline: function(dayData) {
        const intensityData = [];
        
        Object.values(this.countryLayers).forEach(layer => {
            if (layer.errorCount > 0) {
                const intensity = this.calculateIntensity(layer.errorCount, layer.lastErrorTime);
                if (intensity > 10) { // Only include significant intensities
                    intensityData.push({
                        lat: layer.country.lat,
                        lng: layer.country.lng,
                        intensity: intensity,
                        country: layer.country.name
                    });
                }
            }
        });
        
        return intensityData;
    }
};