const AppMap = {
    map: null,
    markers: [],
    
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

        // Popup Content
        let popupContent = `
            <div class="popup-content">
                <span class="popup-country">${item.country_name}</span>
                <div class="popup-headline">"${item.headline}"</div>
                ${item.has_error ? `
                    <div class="popup-error">
                        ⚠ ${item.error_detail.error_word} &rarr; ${item.error_detail.corrected_word}
                    </div>
                ` : ''}
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
            timestamp: Date.now()
        });

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
    }
};
