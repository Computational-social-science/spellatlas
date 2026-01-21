<script>
  import { onMount, onDestroy } from 'svelte';
    import { mapState, latestNewsItem, countryStats, mapMode } from '../stores.js';
    import L from 'leaflet';
    import { DATA } from '../data.js';

    /** @type {HTMLElement} */
    let mapElement;
    /** @type {HTMLElement} */
    let mapElementContainer; // Renamed to avoid confusion if needed, but keeping simple for now
    /** @type {L.Map} */
    let map;
    /** @type {any[]} */
    let markers = [];
    /** @type {Record<string, any>} */
    let countryLayers = {};
    /** @type {L.TileLayer} */
    let tileLayer;
    
    // Dynamic Heatmap System
    /** @type {any} */
    let heatLayer; // L.heatLayer
    /** @type {any[]} */
    let heatData = []; // Array of [lat, lng, intensity]
    
    // Threat Vectors System
    /** @type {any[]} */
    let recentErrors = []; // Array of { lat, lng, timestamp }
    const THREAT_WINDOW = 5000; // 5 seconds to link errors
    const THREAT_MAX_DIST = 2000000; // Max distance in meters (2000km) for a link
    const THREAT_MIN_DIST = 100000; // Min distance (100km) to avoid clutter

    // Focus Mode (Removed)
    /** @type {any} */
    let decayInterval;

    // Tactical Map Styles
    /** @type {Record<string, {url: string, filter: string}>} */
    const TILES = {
        satellite: {
            url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
            filter: 'none'
        },
        wireframe: {
            url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
            filter: 'invert(100%) grayscale(100%) contrast(150%) brightness(0.7) drop-shadow(0 0 5px #00f3ff)'
        }
    };

    onMount(async () => {
        if (mapElement) {
            // Initialize Map
            map = L.map(mapElement, {
                zoomControl: false,
                attributionControl: false,
                zoomSnap: 0.1,
                worldCopyJump: true
            }).setView(/** @type {L.LatLngExpression} */ (/** @type {any} */ ($mapState.center)), $mapState.zoom);

            // Create Tile Layer
            tileLayer = L.tileLayer(TILES.satellite.url, {
                maxZoom: 19,
                opacity: 1.0,
                className: 'transition-all duration-700'
            }).addTo(map);

            // Load Leaflet Heatmap Plugin dynamically
            await loadScript('https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js');
            
            // Initialize Heatmap Layer
            // @ts-ignore
            if (L.heatLayer) {
                // @ts-ignore
                heatLayer = L.heatLayer([], {
                    radius: 25,
                    blur: 15,
                    maxZoom: 10,
                    max: 5.0, // Cumulative Mode: Need 5 errors to hit max red
                    // Optimized Gradient for Cumulative View:
                    // 1 Error (0.2): Deep Purple
                    // 2 Errors (0.4): Cyan
                    // 3 Errors (0.6): Lime
                    // 4 Errors (0.8): Yellow
                    // 5+ Errors (1.0): Red
                    gradient: {
                        0.15: '#2A004E',
                        0.3: '#00F3FF',
                        0.5: '#00FF00',
                        0.7: '#FFFF00',
                        1.0: '#FF0000'
                    }
                }).addTo(map);
            }

            // Fetch Initial Map Stats
            try {
                const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000';
                const statsRes = await fetch(`${apiBase}/api/map-data`);
                if (statsRes.ok) {
                    const statsData = await statsRes.json();
                    countryStats.set(statsData);
                }
            } catch (e) {
                console.warn("Backend offline or stats unavailable", e);
            }

            // Fetch and Initialize GeoJSON World Map
            try {
                const response = await fetch('https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json');
                const geoData = await response.json();
                initializeGeoJSONLayers(geoData);
            } catch (e) {
                console.error("Failed to load GeoJSON, falling back to points", e);
                initializeCountryLayers(); // Fallback
            }
            
            // Start Heatmap Decay Loop
            decayInterval = setInterval(() => {
                decayHeatmap();
                cleanupThreatVectors();
            }, 1000);
        }
    });

    /** @param {string} src */
    function loadScript(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    // ... (keep React to map mode changes)

    /** @param {any} geoData */
    function initializeGeoJSONLayers(geoData) {
        // @ts-ignore
        L.geoJSON(geoData, {
            style: (/** @type {any} */ feature) => {
                const code = feature.id; // Alpha-3 code
                const isEnglish = DATA.ENGLISH_SPEAKING_COUNTRIES.includes(code);
                
                // Swapped Logic:
                // English = Dark (Background)
                // Non-English = Bright (Highlight)
                return {
                    fillColor: isEnglish ? '#050505' : '#FFFFFF',
                    fillOpacity: isEnglish ? 0.8 : 0.2,
                    color: 'transparent',
                    weight: 0,
                    className: 'country-feature transition-all duration-1000'
                };
            },
            onEachFeature: (/** @type {any} */ feature, /** @type {any} */ layer) => {
                const code = feature.id;
                // @ts-ignore
                countryLayers[code] = layer;

                const isEnglish = DATA.ENGLISH_SPEAKING_COUNTRIES.includes(code);
                const name = feature.properties.name;

                layer.bindTooltip(`
                    <div class="font-tech text-xs flex items-center gap-1">
                        <strong class="text-white">${name}</strong>
                        ${isEnglish ? '<span class="text-[0.6rem] font-bold text-black bg-[#00f3ff] px-1 rounded shadow-[0_0_5px_rgba(0,243,255,0.5)]">EN</span>' : ''}
                    </div>
                `, { direction: 'top', className: 'bg-black/90 border border-[#00f3ff]/50 text-white shadow-[0_0_10px_rgba(0,243,255,0.2)]' });
                
                layer.on('mouseover', () => {
                   layer.setStyle({ 
                       fillOpacity: isEnglish ? 0.9 : 0.4,
                       color: 'transparent',
                       weight: 0
                   });
                });
                layer.on('mouseout', () => {
                   layer.setStyle({ 
                       fillOpacity: isEnglish ? 0.8 : 0.2,
                       color: 'transparent',
                       weight: 0
                   });
                });
            }
        }).addTo(map);
    }

    // Focus Mode functions removed



    function updateCountryVisuals() {
        // Update GeoJSON styles based on stats
        Object.entries($countryStats).forEach(([code, stats]) => {
            // @ts-ignore
            const layer = countryLayers[code];
            if (layer) {
                // Removed red border logic as requested
                // We can use this for other visual updates if needed in future
            }
        });
    }

    /** @param {any} item */
    function addMarker(item) {
        const isError = item.has_error;
        /** @type {any} */
        let marker;

        if (isError) {
            // Update Heatmap
            updateHeatmap(item);
            createThreatVector(item);

            // Spark Marker
            // ... (keep existing spark marker logic)
            const markerHtml = `<div class="heatmap-blob error"></div>`;
            marker = L.marker([item.coordinates.lat, item.coordinates.lng], {
                icon: L.divIcon({
                    html: markerHtml,
                    className: 'heatmap-marker-container',
                    iconSize: [40, 40],
                    iconAnchor: [20, 20]
                })
            });
            setTimeout(() => { if (map && marker) map.removeLayer(marker); }, 3000);

        } else {
             // ... (keep existing transient dot logic)
            marker = L.circleMarker([item.coordinates.lat, item.coordinates.lng], {
                radius: 3,
                color: '#00F3FF',
                fillColor: '#00F3FF',
                fillOpacity: 0.6,
                weight: 1,
                className: 'transition-all duration-500'
            });

            setTimeout(() => {
                if (map && marker) map.removeLayer(marker);
            }, 800);
        }
        
        marker.addTo(map);
        // ... (keep popup logic)
        // ...
        // Rich Popup
        const popupContent = `
            <div class="font-tech p-2 min-w-[200px]">
                <div class="flex justify-between items-center mb-2 border-b border-white/20 pb-1">
                    <span class="text-neon-blue font-bold">${item.country_name}</span>
                    <span class="text-xs text-gray-400">${new Date(item.timestamp).toLocaleTimeString()}</span>
                </div>
                <div class="text-sm mb-2 text-white">"${item.headline}"</div>
                ${isError ? `
                    <div class="bg-red-900/30 border border-red-500/50 p-2 rounded text-xs">
                        <div class="text-red-400 font-bold">DETECTED ERROR</div>
                        <div>Word: <span class="text-white">${item.error_details?.word || 'Unknown'}</span></div>
                        <div>Correct: <span class="text-green-400">${item.error_details?.suggestion || 'Unknown'}</span></div>
                    </div>
                ` : '<div class="text-green-400 text-xs">✓ Verified Authentic</div>'}
            </div>
        `;

        marker.bindPopup(popupContent);
        
        if (isError && Math.random() > 0.5) {
            marker.openPopup();
            setTimeout(() => marker.closePopup(), 3000);
            
            // Only push errors to persistent markers list if needed, or handle separately
            markers.push({ instance: marker, timestamp: Date.now() });
        }
        
        // Cleanup
        if (markers.length > 50) {
            const old = markers.shift();
            map.removeLayer(old.instance);
        }
    }

    /** @param {any} item */
    function updateHeatmap(item) {
        if (!heatLayer) return;
        
        // Add point to heat data
        // [lat, lng, intensity]
        // We accumulate points. For dynamic "alive" feel, we push new points.
        // And we remove old points in decay.
        
        heatData.push([item.coordinates.lat, item.coordinates.lng, 1.0]); // Max intensity start
        heatLayer.setLatLngs(heatData);
    }

    function decayHeatmap() {
        if (!heatLayer) return;

        // Cumulative Mode: No decay.
        // History is preserved forever.
        // New errors simply add to the intensity.
    }

    // React to map mode changes
    $: if (map && $mapMode && tileLayer) {
        // @ts-ignore
        const style = TILES[$mapMode];
        if (style) {
            tileLayer.setUrl(style.url);
            if (mapElement) {
                // @ts-ignore
                mapElement.style.filter = style.filter;
            }
        }
    }

    // React to new news items
    $: if ($latestNewsItem && map) {
        addMarker($latestNewsItem);
    }

    // React to country stats updates
    $: if ($countryStats && map) {
        updateCountryVisuals();
    }

    function initializeCountryLayers() {
        DATA.COUNTRIES.forEach(country => {
            // Generate a simple code if not present (Simulator uses name, let's map it)
            const code = country.code || country.name.substring(0, 3).toUpperCase();
            const isEnglish = DATA.ENGLISH_SPEAKING_COUNTRIES.includes(code);
            
            // Binary gray scale: English = Dark (Background), Non-English = Light (Highlight)
            // Swapped Logic
            const fillColor = isEnglish ? '#050505' : '#FFFFFF'; 
            const fillOpacity = isEnglish ? 0.8 : 0.2;
            const radius = isEnglish ? 2 : 4;

            const marker = L.circleMarker([country.lat, country.lng], {
                radius: radius,
                color: 'transparent',
                fillColor: fillColor,
                fillOpacity: fillOpacity,
                weight: 0,
                className: 'country-base-marker transition-all duration-1000'
            }).addTo(map);

            marker.bindTooltip(`
                <div class="font-tech text-xs flex items-center gap-1">
                    <strong class="text-white">${country.name}</strong>
                    ${isEnglish ? '<span class="text-[0.6rem] font-bold text-black bg-[#00f3ff] px-1 rounded shadow-[0_0_5px_rgba(0,243,255,0.5)]">EN</span>' : ''}
                </div>
            `, { direction: 'top', className: 'bg-black/90 border border-[#00f3ff]/50 text-white shadow-[0_0_10px_rgba(0,243,255,0.2)]' });

            countryLayers[code] = marker;
        });
    }









    /** @param {any} item */
    function createThreatVector(item) {
        const now = Date.now();
        const currentLatLng = L.latLng(item.coordinates.lat, item.coordinates.lng);

        // Filter recent errors
        recentErrors = recentErrors.filter(e => now - e.timestamp < THREAT_WINDOW);

        // Find neighbors
        recentErrors.forEach(prev => {
            const prevLatLng = L.latLng(prev.lat, prev.lng);
            const dist = currentLatLng.distanceTo(prevLatLng);

            if (dist > THREAT_MIN_DIST && dist < THREAT_MAX_DIST) {
                // Draw Line
                const line = L.polyline([prevLatLng, currentLatLng], {
                    color: '#ff4500',
                    weight: 1,
                    opacity: 0.6,
                    className: 'threat-vector-line' // CSS animation for "flow"
                }).addTo(map);

                // Animate removal
                setTimeout(() => {
                    line.setStyle({ opacity: 0 });
                    setTimeout(() => map.removeLayer(line), 1000);
                }, 2000);
            }
        });

        recentErrors.push({ 
            lat: item.coordinates.lat, 
            lng: item.coordinates.lng, 
            timestamp: now 
        });
    }

    function cleanupThreatVectors() {
        // Just prune the array, lines handle their own removal
        const now = Date.now();
        recentErrors = recentErrors.filter(e => now - e.timestamp < THREAT_WINDOW);
    }



    onDestroy(() => {
        if (decayInterval) clearInterval(decayInterval);
        if (map) map.remove();
    });
</script>

<div class="w-full h-full bg-black" bind:this={mapElement}></div>

<style>
    /* Leaflet customization if needed */
    :global(.leaflet-popup-content-wrapper) {
        background: rgba(10, 10, 31, 0.9);
        backdrop-filter: blur(10px);
        border: 1px solid #00f3ff;
        color: white;
        border-radius: 8px;
    }
    :global(.leaflet-popup-tip) {
        background: rgba(10, 10, 31, 0.9);
    }

    :global(.heatmap-marker-container) {
        background: transparent;
        border: none;
    }
    :global(.heatmap-blob) {
        width: 100%;
        height: 100%;
        border-radius: 50%;
        opacity: 0.6;
        transition: all 0.5s ease-out;
    }
    :global(.heatmap-blob.normal) {
        background: radial-gradient(closest-side, rgba(0, 243, 255, 0.6), rgba(0, 243, 255, 0));
        box-shadow: 0 0 10px rgba(0, 243, 255, 0.2);
    }
    :global(.heatmap-blob.error) {
        background: radial-gradient(closest-side, rgba(255, 69, 0, 0.8), rgba(255, 69, 0, 0));
        box-shadow: 0 0 15px rgba(255, 69, 0, 0.4);
        animation: pulse-heat 2s infinite;
    }
    @keyframes pulse-heat {
        0% { transform: scale(1); opacity: 0.6; }
        50% { transform: scale(1.2); opacity: 0.8; }
        100% { transform: scale(1); opacity: 0.6; }
    }

    /* Drilldown Tooltip */
    :global(.drilldown-tooltip) {
        background: rgba(10, 10, 15, 0.95);
        border: 1px solid rgba(255, 69, 0, 0.5);
        border-radius: 4px;
        box-shadow: 0 0 20px rgba(255, 69, 0, 0.2);
        padding: 0;
    }
    :global(.drilldown-tooltip .leaflet-tooltip-content) {
        margin: 0;
    }
    :global(.drilldown-tooltip:before) {
        border-top-color: rgba(255, 69, 0, 0.5);
    }

    /* Threat Vector Line Animation */
    :global(.threat-vector-line) {
        stroke-dasharray: 10, 10;
        animation: dash-flow 1s linear infinite;
    }
    @keyframes dash-flow {
        to { stroke-dashoffset: -20; }
    }
</style>
