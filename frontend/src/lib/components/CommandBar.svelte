<script>
    import { isPaused, playbackSpeed, windowState, mapMode, gameStats } from '../stores.js';
    
    // Windows configuration
    const windows = [
        { id: 'feed', icon: '📡', label: 'UPLINK' },
        { id: 'timeline', icon: '⏱', label: 'TEMPORAL' },
        { id: 'countries', icon: '🌍', label: 'REGIONAL' },
        { id: 'threats', icon: '⚠️', label: 'THREATS' }
    ];

    /** @param {string} id */
    function toggleWindow(id) {
        windowState.update(s => {
            /** @type {any} */
            const state = s;
            const win = state[id];
            if (win.visible && !win.minimized) {
                // If focused, minimize
                win.minimized = true;
            } else {
                // Open or restore
                win.visible = true;
                win.minimized = false;
            }
            return { ...state, [id]: win };
        });
    }

    function togglePause() {
        $isPaused = !$isPaused;
    }

    function toggleMapMode() {
        $mapMode = $mapMode === 'satellite' ? 'wireframe' : 'satellite';
    }
</script>

<div class="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 pointer-events-auto select-none">
    <!-- Main Console Container -->
    <div class="h-20 min-w-[700px] bg-[#050510]/50 backdrop-blur-md rounded-full border border-white/10 shadow-[0_0_50px_rgba(0,0,0,0.6)] flex items-center justify-between px-8 relative overflow-hidden group">
        
        <!-- Ambient Glow -->
        <div class="absolute inset-0 bg-gradient-to-r from-neon-blue/5 via-transparent to-neon-pink/5 pointer-events-none"></div>
        <div class="absolute bottom-0 left-1/2 -translate-x-1/2 w-1/2 h-[1px] bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>

        <!-- LEFT SECTION: WINDOW CONTROLS -->
        <div class="flex items-center gap-4">
            
            <div class="flex gap-2 bg-black/40 p-1.5 rounded-full border border-white/5 shadow-inner">
                {#each windows as win}
                    <button 
                        class="w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300 relative group/btn overflow-hidden {$windowState[win.id]?.visible && !$windowState[win.id]?.minimized ? 'bg-white/10 text-neon-blue shadow-[0_0_15px_rgba(0,243,255,0.2)]' : 'text-white/30 hover:text-white hover:bg-white/5'}"
                        on:click={() => toggleWindow(win.id)}
                        title={win.label}
                    >
                        <span class="material-icons-round text-lg relative z-10">{win.icon}</span>
                        {#if $windowState[win.id]?.visible && !$windowState[win.id]?.minimized}
                            <div class="absolute inset-0 bg-neon-blue/10 blur-sm"></div>
                        {/if}
                    </button>
                {/each}
            </div>
        </div>

        <!-- CENTER SECTION: FLIGHT DECK -->
        <div class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex items-center gap-6">
            
            <!-- Speed Down -->
            <button 
                class="w-8 h-8 rounded-full border border-white/10 flex items-center justify-center text-white/50 hover:text-white hover:border-white/30 hover:bg-white/5 transition-all active:scale-95 font-mono font-bold text-lg"
                on:click={() => $playbackSpeed = Math.max(0.5, $playbackSpeed - 0.5)}
            >
                -
            </button>

            <!-- Main Control Knob -->
            <div class="relative w-24 h-24 -my-4 flex items-center justify-center group/knob">
                <!-- Outer Ring -->
                <div class="absolute inset-0 rounded-full border border-white/10 bg-[#0a0a15] shadow-2xl"></div>
                
                <!-- Progress Ring (SVG) -->
                <svg class="absolute inset-0 w-full h-full -rotate-90 pointer-events-none p-1">
                    <circle cx="50%" cy="50%" r="44%" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="2" />
                    <circle cx="50%" cy="50%" r="44%" fill="none" stroke="#00f3ff" stroke-width="2" 
                        stroke-dasharray="276" 
                        stroke-dashoffset={276 - (($playbackSpeed / 5) * 276)} 
                        class="transition-all duration-500 ease-out shadow-[0_0_10px_#00f3ff]"
                    />
                </svg>

                <!-- Inner Button -->
                <button 
                    class="w-16 h-16 rounded-full bg-gradient-to-br from-[#1a1a2e] to-[#0a0a15] shadow-[inset_0_2px_10px_rgba(255,255,255,0.05)] flex items-center justify-center border border-white/10 hover:border-neon-blue/50 transition-all active:scale-95 group/play z-10"
                    on:click={togglePause}
                >
                    {#if $isPaused}
                        <!-- Solid Triangle Play Icon -->
                        <svg viewBox="0 0 24 24" class="w-8 h-8 fill-white/30 ml-1 transition-all duration-300">
                            <path d="M8 5v14l11-7z" />
                        </svg>
                    {:else}
                        <!-- Pause Icon -->
                        <svg viewBox="0 0 24 24" class="w-8 h-8 fill-neon-blue drop-shadow-[0_0_5px_rgba(0,243,255,0.8)] transition-all duration-300">
                            <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
                        </svg>
                    {/if}
                </button>

                <!-- Speed Label -->
                <div class="absolute -bottom-6 text-[0.6rem] font-mono font-bold tracking-widest text-neon-blue/80 bg-black/80 px-2 py-0.5 rounded-full border border-white/10 backdrop-blur">
                    {$playbackSpeed.toFixed(1)}
                </div>
            </div>

            <!-- Speed Up -->
            <button 
                class="w-8 h-8 rounded-full border border-white/10 flex items-center justify-center text-white/50 hover:text-white hover:border-white/30 hover:bg-white/5 transition-all active:scale-95 font-mono font-bold text-lg"
                on:click={() => $playbackSpeed = Math.min(5, $playbackSpeed + 0.5)}
            >
                +
            </button>

        </div>

        <!-- RIGHT SECTION: TELEMETRY -->
        <div class="flex items-center gap-6">
            
            <!-- Stats Group -->
            <div class="flex gap-4 pr-6 mr-2 border-r border-white/10">
                <div class="flex flex-col items-end">
                    <span class="text-[0.5rem] font-mono text-white/30 tracking-widest">DETECTED</span>
                    <span class="text-sm font-mono font-bold text-neon-blue">{$gameStats.totalItems}</span>
                </div>
                <div class="flex flex-col items-end">
                    <span class="text-[0.5rem] font-mono text-white/30 tracking-widest">ANOMALIES</span>
                    <span class="text-sm font-mono font-bold text-neon-pink">{$gameStats.totalErrors}</span>
                </div>
            </div>

        </div>

    </div>
</div>

<style>
    /* No custom input styles needed as we use a custom visual thumb */
</style>
