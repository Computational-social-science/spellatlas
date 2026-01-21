<script>
    import { onMount } from 'svelte';
    
    let time = new Date().toLocaleTimeString();
    let date = new Date().toLocaleDateString();

    onMount(() => {
        const interval = setInterval(() => {
            const now = new Date();
            time = now.toLocaleTimeString();
            date = now.toLocaleDateString();
        }, 1000);
        return () => clearInterval(interval);
    });
</script>

<header class="w-full h-12 flex items-center justify-between px-6 z-50 pointer-events-auto bg-gradient-to-b from-black/50 to-transparent border-b border-white/5 backdrop-blur-sm select-none">
    <!-- Left: Brand -->
    <div class="flex items-center gap-4">
        <div class="relative w-6 h-6">
            <div class="absolute inset-0 bg-neon-blue rounded-full animate-ping opacity-20"></div>
            <div class="absolute inset-1 bg-neon-blue rounded-full shadow-[0_0_10px_#00f3ff]"></div>
        </div>
        <div class="flex flex-col">
            <h1 class="text-xl font-bold tracking-[0.2em] text-white leading-none">SPELL ATLAS</h1>
            <span class="text-[0.6rem] text-neon-blue font-mono tracking-widest opacity-70">Uncharted fingerprints of human misspelling behavior</span>
        </div>
    </div>

    <!-- Center: Decoration -->
    <div class="hidden md:flex items-center gap-2 opacity-30">
        <div class="w-16 h-[1px] bg-white"></div>
        <div class="w-2 h-2 border border-white rotate-45"></div>
        <div class="w-16 h-[1px] bg-white"></div>
    </div>

    <!-- Right: Empty for cleaner HUD -->
    <div class="w-20"></div>
</header>
