<script>
    import { onMount, onDestroy } from 'svelte';
    import { newsFeed, isPaused, latestNewsItem, gameStats, countryStats, timelineData } from '../stores.js';
    
    /** @type {WebSocket} */
    let socket;
    /** @type {any} */
    let snapshotId;

    function connectWebSocket() {
        const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
        socket = new WebSocket(`${wsUrl}/ws`);

        socket.onopen = () => {
            console.log('Connected to backend simulator');
        };

        socket.onmessage = (event) => {
            if ($isPaused) return; // Skip updates if paused

            try {
                const payload = JSON.parse(event.data);
                
                // Handle different message types
                if (payload.type === 'heartbeat' || payload.type === 'info') return;

                if (payload.type === 'news_item') {
                    const newItem = {
                        id: Date.now() + Math.random(),
                        timestamp: Date.now(),
                        country_name: payload.country_name,
                        country_code: payload.country_code,
                        coordinates: payload.coordinates,
                        has_error: payload.has_error,
                        headline: payload.title,
                        error_details: payload.error_details
                    };

                    // 1. Update Feed (Cap at 50 items)
                    newsFeed.update(current => [newItem, ...current].slice(0, 50));
                    
                    // 2. Trigger Map Update
                    // @ts-ignore
                    latestNewsItem.set(newItem);

                    // 3. Update Game Stats
                    gameStats.update(s => ({
                        ...s,
                        totalItems: s.totalItems + 1,
                        totalErrors: s.totalErrors + (newItem.has_error ? 1 : 0),
                        accuracy: s.totalItems === 0 ? 100 : Math.round(((s.totalItems + 1 - (s.totalErrors + (newItem.has_error ? 1 : 0))) / (s.totalItems + 1)) * 100)
                    }));

                    // 4. Update Country Stats
                    countryStats.update(s => {
                        /** @type {Record<string, any>} */
                        const stats = s;
                        const code = newItem.country_code || 'UNK';
                        if (!stats[code]) {
                            stats[code] = { name: newItem.country_name || 'Unknown', total: 0, errors: 0 };
                        }
                        stats[code].total += 1;
                        if (newItem.has_error) stats[code].errors += 1;
                        return stats;
                    });
                }
            } catch (e) {
                console.error('Error processing message:', e);
            }
        };

        socket.onclose = () => {
            console.log('Disconnected from backend. Reconnecting in 3s...');
            setTimeout(connectWebSocket, 3000);
        };
        
        socket.onerror = (/** @type {Event} */ err) => {
            console.error('WebSocket error:', err);
            socket.close();
        };
    }

    onMount(() => {
        connectWebSocket();

        // Snapshot Loop (Keep client-side for now)
        snapshotId = setInterval(() => {
            if (!$isPaused) {
                /** @type {any} */
                let currentStats;
                const unsub = gameStats.subscribe(v => currentStats = v);
                unsub();
                
                timelineData.update(data => {
                    /** @type {any} */
                    const newData = [
                        ...data,
                        {
                            day: data.length + 1,
                            totalEvents: currentStats.totalItems,
                            errorEvents: currentStats.totalErrors
                        }
                    ].slice(-30);
                    return newData;
                });
            }
        }, 10000); // Fixed 10s for snapshot
    });

    onDestroy(() => {
        if (socket) socket.close();
        if (snapshotId) clearInterval(snapshotId);
    });
</script>

<!-- Headless Controller -->
<slot></slot>
