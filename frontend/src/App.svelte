<script>
    import { onMount } from 'svelte';
    import { gameStats } from './lib/stores.js';
    import MapContainer from './lib/components/MapContainer.svelte';
    import Header from './lib/components/Header.svelte';
    import CommandBar from './lib/components/CommandBar.svelte';
    import NewsFeed from './lib/components/NewsFeed.svelte';
    import DraggableWindow from './lib/components/DraggableWindow.svelte';
    import TimelineContent from './lib/components/TimelineContent.svelte';
    import CountriesContent from './lib/components/CountriesContent.svelte';
    import ThreatsContent from './lib/components/ThreatsContent.svelte';
    import StatsContent from './lib/components/StatsContent.svelte';
    import AnalysisWindow from './lib/components/AnalysisWindow.svelte';
    import GameController from './lib/components/GameController.svelte';

    // Parallax Logic
    let mouseX = 0;
    let mouseY = 0;
    let hudX = 0;
    let hudY = 0;
    let frameX = 0;
    let frameY = 0;

    /** @param {MouseEvent} e */
    function handleMouseMove(e) {
        const { clientX, clientY, currentTarget } = e;
        const { innerWidth, innerHeight } = window;
        
        // Normalize -1 to 1
        const x = (clientX / innerWidth) * 2 - 1;
        const y = (clientY / innerHeight) * 2 - 1;
        
        mouseX = x;
        mouseY = y;
    }

    // Smooth lerp loop
    onMount(() => {
        /** @type {number} */
        let frame;
        function loop() {
            // HUD moves slightly opposite to mouse (foreground layer)
            hudX += (mouseX * -15 - hudX) * 0.1;
            hudY += (mouseY * -15 - hudY) * 0.1;

            // Frame moves less (mid layer)
            frameX += (mouseX * -5 - frameX) * 0.1;
            frameY += (mouseY * -5 - frameY) * 0.1;
            
            frame = requestAnimationFrame(loop);
        }
        loop();
        return () => cancelAnimationFrame(frame);
    });
</script>

<svelte:window on:mousemove={handleMouseMove} />

<GameController />

<main class="relative w-full h-screen overflow-hidden bg-tech-dark text-white font-tech selection:bg-neon-blue/30 perspective-1000">
    <!-- CRT Effects -->
    <div class="scanline"></div>
    <div class="absolute inset-0 pointer-events-none z-[9999] shadow-[inset_0_0_100px_rgba(0,0,0,0.9)]"></div> <!-- Vignette -->
    
    <!-- Map Layer (Background - Static or slight movement) -->
    <div class="absolute inset-0 z-0 scale-105" style="transform: translate({frameX * 0.5}px, {frameY * 0.5}px)">
        <MapContainer />
    </div>

    <!-- HUD Layer -->
    <div class="absolute inset-0 z-10 pointer-events-none flex flex-col justify-between p-4 transition-transform will-change-transform"
         style="transform: translate({hudX}px, {hudY}px) rotateX({-hudY * 0.05}deg) rotateY({hudX * 0.05}deg)">
        
        <!-- Perimeter HUD Frame -->
        <div class="absolute inset-4 border border-white/5 pointer-events-none rounded-lg"
             style="transform: translate({frameX - hudX}px, {frameY - hudY}px)">
            <!-- Top Left Corner -->
            <div class="absolute -top-[1px] -left-[1px] w-8 h-8 border-t-2 border-l-2 border-neon-blue/50 rounded-tl-lg"></div>
            <!-- Top Right Corner -->
            <div class="absolute -top-[1px] -right-[1px] w-8 h-8 border-t-2 border-r-2 border-neon-blue/50 rounded-tr-lg"></div>
            
            <!-- Top Right Info (Symmetrical to Title) -->
            <div class="absolute top-4 right-6 flex flex-col items-end">
                <div class="text-[0.6rem] text-neon-blue/60 tracking-[0.2em] font-mono mb-1">DATA STREAM</div>
                <div class="flex items-center gap-2">
                    <div class="w-1.5 h-1.5 rounded-full bg-neon-green animate-pulse"></div>
                    <span class="text-2xl font-bold text-white tracking-widest font-mono">
                        {$gameStats.totalItems.toString().padStart(6, '0')}
                    </span>
                </div>
            </div>

            <!-- Bottom Left Corner -->
            <div class="absolute -bottom-[1px] -left-[1px] w-8 h-8 border-b-2 border-l-2 border-neon-blue/50 rounded-bl-lg"></div>
            <!-- Bottom Right Corner -->
            <div class="absolute -bottom-[1px] -right-[1px] w-8 h-8 border-b-2 border-r-2 border-neon-blue/50 rounded-br-lg"></div>
            
            <!-- Side Rulers (Decorative) -->
            <div class="absolute top-1/2 left-0 -translate-y-1/2 flex flex-col gap-2 opacity-30">
                {#each Array(10) as _, i}
                    <div class="w-2 h-[1px] bg-white"></div>
                {/each}
            </div>
            <div class="absolute top-1/2 right-0 -translate-y-1/2 flex flex-col gap-2 items-end opacity-30">
                {#each Array(10) as _, i}
                    <div class="w-2 h-[1px] bg-white"></div>
                {/each}
            </div>

            <!-- Center Crosshair -->
            <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-8 h-8 border border-white/10 opacity-20 flex items-center justify-center">
                <div class="w-[1px] h-full bg-white/30"></div>
                <div class="h-[1px] w-full bg-white/30 absolute"></div>
            </div>
        </div>

        <!-- Top: Header -->
        <div class="flex flex-col items-center w-full z-20">
            <Header />
        </div>

        <!-- Middle: Floating Windows Space -->
        <div class="flex-1 relative w-full h-full pointer-events-none">
            <!-- Windows container, allowing dragging everywhere -->
            <DraggableWindow id="feed" title="SATELLITE UPLINK" icon="📡">
                <NewsFeed />
            </DraggableWindow>

            <DraggableWindow id="timeline" title="TEMPORAL ANALYSIS" icon="⏱">
                <TimelineContent />
            </DraggableWindow>
            
            <DraggableWindow id="countries" title="REGIONAL STATUS" icon="🌍">
                <CountriesContent />
            </DraggableWindow>
            
            <DraggableWindow id="threats" title="THREAT VECTORS" icon="⚠️">
                <ThreatsContent />
            </DraggableWindow>

            <DraggableWindow id="stats" title="GLOBAL INTEL" icon="📊" initialX={window.innerWidth - 420} initialY={450}>
                <StatsContent />
            </DraggableWindow>

            <DraggableWindow id="analytics" title="QUANTITATIVE ANALYTICS" icon="📉" initialX={60} initialY={160}>
                <AnalysisWindow />
            </DraggableWindow>
        </div>

        <!-- Bottom: Command Bar -->
        <div class="w-full flex justify-center pb-4 pointer-events-auto">
            <CommandBar />
        </div>
    </div>
</main>
