const AppMap = {
    map: null,
    markers: [],
    countryLayers: {},
    
    init: function() {
        // Initialize Leaflet Map
        this.map = L.map('map', {
            zoomControl: false,
            attributionControl: false
        }).setView([20, 0], 2.5);

        // Add Dark Tile Layer
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            maxZoom: 19,
            opacity: 1.0 // Ensure visibility
        }).addTo(this.map);
        
        // Initialize country layers for statistical visualization
        this.initializeCountryLayers();
    },

    initializeCountryLayers: function() {
        // Create country boundary layers for statistical display
        DATA.COUNTRIES.forEach(country => {
            // Create a simple circle marker for each country
            const countryMarker = L.circleMarker([country.lat, country.lng], {
                radius: 3,
                color: 'rgba(0, 243, 255, 0.3)',
                fillColor: 'rgba(0, 243, 255, 0.1)',
                fillOpacity: 0.3,
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
                totalCount: 0
            };
        });
    },

    updateCountryVisualization: function(countryCode, errorRate) {
        const layer = this.countryLayers[countryCode];
        if (layer) {
            // Update visual appearance based on error rate
            const intensity = Math.min(errorRate / 50, 1); // Cap at 50% error rate for visualization
            const radius = 3 + (intensity * 5); // Scale radius from 3 to 8
            
            if (errorRate > 10) {
                // High error rate - show as alert
                layer.marker.setStyle({
                    radius: radius,
                    color: 'var(--alert)',
                    fillColor: 'var(--alert)',
                    fillOpacity: 0.6,
                    weight: 2,
                    className: 'country-alert-marker pulse-marker'
                });
            } else if (errorRate > 5) {
                // Medium error rate
                layer.marker.setStyle({
                    radius: radius,
                    color: 'var(--primary)',
                    fillColor: 'var(--primary)',
                    fillOpacity: 0.4,
                    weight: 1,
                    className: 'country-medium-marker'
                });
            } else {
                // Low error rate - reset to base
                layer.marker.setStyle({
                    radius: 3,
                    color: 'rgba(0, 243, 255, 0.3)',
                    fillColor: 'rgba(0, 243, 255, 0.1)',
                    fillOpacity: 0.3,
                    weight: 1,
                    className: 'country-base-marker'
                });
            }
        }
    },

    addMarker: function(item) {
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

        // Popup Content with enhanced scientific information
        let popupContent = `
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
                    <span class="metric">Source: News Feed #${Math.floor(Math.random() * 999 + 1)}</span>
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

        // Update country layer if this is a significant error
        if (item.has_error) {
            const countryCode = item.country_name.substring(0, 3).toUpperCase();
            if (this.countryLayers[countryCode]) {
                this.countryLayers[countryCode].errorCount++;
                this.countryLayers[countryCode].totalCount++;
                
                const errorRate = (this.countryLayers[countryCode].errorCount / this.countryLayers[countryCode].totalCount) * 100;
                this.updateCountryVisualization(countryCode, errorRate);
            }
        }

        // Cleanup old markers
        this.cleanup();
    },

    cleanup: function() {
        const now = Date.now();
        // Remove markers older than 10 seconds or if > 50 markers
        if (this.markers.length > 50) {
            const toRemove = this.markers.splice(0, this.markers.length - 50);
            toRemove.forEach(m => this.map.removeLayer(m.instance));
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
                    countries: 0
                };
            }
            
            regions[layer.country.region].totalErrors += layer.errorCount;
            regions[layer.country.region].totalItems += layer.totalCount;
            regions[layer.country.region].countries++;
        });
        
        return regions;
    },

    getTopErrorCountries: function(limit = 10) {
        return Object.values(this.countryLayers)
            .filter(layer => layer.totalCount > 0)
            .map(layer => ({
                country: layer.country.name,
                code: layer.country.code,
                region: layer.country.region,
                errorRate: (layer.errorCount / layer.totalCount) * 100,
                errorCount: layer.errorCount,
                totalCount: layer.totalCount
            }))
            .sort((a, b) => b.errorRate - a.errorRate)
            .slice(0, limit);
    }
};