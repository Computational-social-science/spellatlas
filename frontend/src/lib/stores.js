import { writable } from 'svelte/store';

/** @type {import('svelte/store').Writable<any[]>} */
export const newsFeed = writable([]);
export const isPaused = writable(false);
export const playbackSpeed = writable(1.0);

// UI State
export const mapMode = writable('satellite'); // 'satellite' | 'wireframe'
export const soundEnabled = writable(true);

export const mapState = writable({
    selectedCountry: null,
    zoom: 2.5,
    center: [20, 0]
});
export const gameStats = writable({
    totalItems: 0,
    totalErrors: 0,
    accuracy: 100
});

// New Stores for Restored Functionality
export const countryStats = writable({}); // Key: country code, Value: { errors, total, ... }
/** @type {import('svelte/store').Writable<any[]>} */
export const timelineData = writable([]); // Array of daily snapshots
/** @type {import('svelte/store').Writable<Record<string, any>>} */
export const windowState = writable({
    feed: { visible: true, minimized: false, maximized: false, position: { x: 20, y: 100 } },
    timeline: { visible: false, minimized: false, maximized: false, position: { x: 100, y: 100 } },
    countries: { visible: false, minimized: false, maximized: false, position: { x: 150, y: 150 } },
    threats: { visible: false, minimized: false, maximized: false, position: { x: 200, y: 200 } }
});
export const latestNewsItem = writable(null); // To trigger map updates efficiently
