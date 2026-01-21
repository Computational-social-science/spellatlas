<script>
    import { onMount } from 'svelte';
    
    /** @type {any[]} */
    let topErrors = [];
    /** @type {any[]} */
    let trendCurve = [];
    let loading = true;
    let activeTab = 'top'; // 'top' | 'trends'

    /** @returns {Promise<void>} */
    async function fetchData() {
        loading = true;
        try {
            // Robust fallback: If env var is missing, guess based on environment
            const apiBase = import.meta.env.VITE_API_URL || 
                            (window.location.hostname === 'localhost' ? 'http://localhost:8000' : 'https://spellatlas-backend-production.fly.dev');
            
            const [topRes, curveRes] = await Promise.all([
                fetch(`${apiBase}/api/stats/top-errors?limit=10`),
                fetch(`${apiBase}/api/stats/curve?hours=24`)
            ]);
            
            if (topRes.ok) topErrors = await topRes.json();
            if (curveRes.ok) trendCurve = await curveRes.json();
        } catch (e) {
            console.error(e);
        } finally {
            loading = false;
        }
    }

    onMount(() => {
        fetchData();
        const interval = setInterval(fetchData, 30000);
        return () => clearInterval(interval);
    });

    // Chart Helpers
    $: maxValTop = Math.max(...topErrors.map(d => d.count), 1);
    $: maxValCurve = Math.max(...trendCurve.map(d => d.count), 1);

    // SVG Chart Dimensions
    const chartHeight = 150;
    const chartWidth = 300;
    
    /** @param {number} i */
    function getX(i) {
        return (i / (trendCurve.length - 1 || 1)) * chartWidth;
    }
    
    /** @param {number} val */
    function getY(val) {
        return chartHeight - ((val / maxValCurve) * chartHeight);
    }
    
    $: points = trendCurve.map((d, i) => `${getX(i)},${getY(d.count)}`).join(' ');
    $: areaPoints = `${points} ${chartWidth},${chartHeight} 0,${chartHeight}`;
</script>

<div class="flex flex-col h-full w-[350px] h-[300px] p-4 font-mono text-sm">
    <!-- Tabs -->
    <div class="flex border-b border-white/10 mb-4">
        <button 
            class="px-4 py-2 hover:bg-white/5 transition-colors {activeTab === 'top' ? 'text-neon-blue border-b-2 border-neon-blue' : 'text-gray-500'}"
            on:click={() => activeTab = 'top'}>
            ALL TIME
        </button>
        <button 
            class="px-4 py-2 hover:bg-white/5 transition-colors {activeTab === 'trends' ? 'text-neon-green border-b-2 border-neon-green' : 'text-gray-500'}"
            on:click={() => activeTab = 'trends'}>
            24H TRENDS
        </button>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto custom-scrollbar relative">
        {#if loading && topErrors.length === 0 && trendCurve.length === 0}
            <div class="absolute inset-0 flex items-center justify-center text-neon-blue animate-pulse">
                ANALYZING DATA...
            </div>
        {:else if activeTab === 'top'}
            {#if topErrors.length === 0}
                 <div class="text-center text-gray-500 mt-10">NO DATA AVAILABLE</div>
            {:else}
                <div class="space-y-3">
                    {#each topErrors as item, i}
                        <div class="relative group">
                            <div class="flex justify-between items-end mb-1 text-xs relative z-10">
                                <span class="font-bold text-red-400">{item.word}</span>
                                <span class="text-white/60">{item.count}</span>
                            </div>
                            <div class="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                                <div 
                                    class="h-full rounded-full transition-all duration-1000 ease-out bg-gradient-to-r from-red-500 to-red-400"
                                    style="width: {(item.count / maxValTop) * 100}%"
                                ></div>
                            </div>
                        </div>
                    {/each}
                </div>
            {/if}
        {:else}
            <!-- Trend Chart -->
            {#if trendCurve.length === 0}
                <div class="text-center text-gray-500 mt-10">NO TREND DATA</div>
            {:else}
                <div class="relative h-[200px] w-full mt-4">
                    <svg viewBox="0 0 {chartWidth} {chartHeight}" class="w-full h-full overflow-visible">
                        <!-- Grid Lines -->
                        {#each [0, 0.25, 0.5, 0.75, 1] as tick}
                             <line x1="0" y1={chartHeight * tick} x2={chartWidth} y2={chartHeight * tick} stroke="white" stroke-opacity="0.1" stroke-dasharray="2 2" />
                        {/each}
                        
                        <!-- Area -->
                        <path d="M0,{chartHeight} {areaPoints}" fill="rgba(0, 255, 128, 0.1)" />
                        
                        <!-- Line -->
                        <polyline points={points} fill="none" stroke="#00ff80" stroke-width="2" />
                        
                        <!-- Points -->
                        {#each trendCurve as point, i}
                            <circle cx={getX(i)} cy={getY(point.count)} r="3" fill="#00ff80" class="hover:r-4 transition-all" />
                        {/each}
                    </svg>
                    
                    <!-- X-Axis Labels (First and Last) -->
                    <div class="flex justify-between text-[10px] text-gray-500 mt-2">
                        <span>{new Date(trendCurve[0].time).getHours()}:00</span>
                        <span>{new Date(trendCurve[trendCurve.length-1].time).getHours()}:00</span>
                    </div>
                </div>
            {/if}
        {/if}
    </div>
</div>

<style>
    /* Custom Scrollbar for Webkit */
    .custom-scrollbar::-webkit-scrollbar {
        width: 4px;
    }
    .custom-scrollbar::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.05);
    }
    .custom-scrollbar::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 2px;
    }
</style>
