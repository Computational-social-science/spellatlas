<script>
    import { onMount, createEventDispatcher } from 'svelte';
    import { scale } from 'svelte/transition';
    import { quintOut } from 'svelte/easing';
    import { windowState } from '../stores.js';
    
    /** @type {string} */
    export let id;
    export let title = 'WINDOW';
    export let icon = '⬜';
    export let initialX = 100;
    export let initialY = 100;
    
    /** @type {HTMLElement} */
    let element;
    let isDragging = false;
    let dragOffset = { x: 0, y: 0 };
    
    const dispatch = createEventDispatcher();
    
    // Initialize store if not present
    onMount(() => {
        windowState.update(s => {
            /** @type {any} */
            const state = s;
            if (!state[id]) {
                return {
                    ...s,
                    [id]: { visible: true, minimized: false, maximized: false, position: { x: initialX, y: initialY } }
                };
            }
            return s;
        });
    });
    
    // @ts-ignore
    $: state = $windowState[id] || { visible: false, minimized: false, maximized: false, position: { x: initialX, y: initialY } };

    /** @param {MouseEvent} e */
    function startDrag(e) {
        // @ts-ignore
        if (state.maximized) return;
        isDragging = true;
        // @ts-ignore
        dragOffset.x = e.clientX - state.position.x;
        // @ts-ignore
        dragOffset.y = e.clientY - state.position.y;
        
        window.addEventListener('mousemove', handleDrag);
        window.addEventListener('mouseup', stopDrag);
    }
    
    /** @param {MouseEvent} e */
    function handleDrag(e) {
        if (!isDragging) return;
        
        const newX = e.clientX - dragOffset.x;
        const newY = e.clientY - dragOffset.y;
        
        windowState.update(s => {
            /** @type {any} */
            const state = s;
            return {
                ...state,
                [id]: { ...state[id], position: { x: newX, y: newY } }
            };
        });
    }
    
    function stopDrag() {
        isDragging = false;
        window.removeEventListener('mousemove', handleDrag);
        window.removeEventListener('mouseup', stopDrag);
    }
    
    function toggleMinimize() {
        windowState.update(s => {
            /** @type {any} */
            const state = s;
            return {
                ...state,
                [id]: { ...state[id], minimized: !state[id].minimized }
            };
        });
    }
    
    function closeWindow() {
        windowState.update(s => {
            /** @type {any} */
            const state = s;
            return {
                ...state,
                [id]: { ...state[id], visible: false }
            };
        });
    }
</script>

{#if state.visible}
    <div 
        bind:this={element}
        transition:scale={{duration: 300, easing: quintOut, start: 0.95, opacity: 0}}
        class="absolute z-50 flex flex-col backdrop-blur-md bg-[#0a0a1f]/60 border border-white/10 shadow-[0_0_30px_rgba(0,0,0,0.5)] overflow-hidden transition-all duration-200 pointer-events-auto group ring-1 ring-white/5"
        style="left: {state.position.x}px; top: {state.position.y}px; width: {state.maximized ? '100%' : 'auto'}; height: {state.maximized ? '100%' : 'auto'}; min-width: 300px; min-height: 200px;"
        class:opacity-0={state.minimized}
        class:pointer-events-none={state.minimized}
    >
        <!-- Holographic Projection Lines -->
        <div class="absolute -top-4 left-1/2 -translate-x-1/2 w-[1px] h-4 bg-gradient-to-b from-transparent to-neon-blue/50 opacity-0 group-hover:opacity-100 transition-opacity"></div>
        
        <!-- Decorative Corners (Tech Style) -->
        <div class="absolute top-0 left-0 w-2 h-2 border-t border-l border-neon-blue/80"></div>
        <div class="absolute top-0 right-0 w-2 h-2 border-t border-r border-neon-blue/80"></div>
        <div class="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-neon-blue/80"></div>
        <div class="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-neon-blue/80"></div>

        <!-- Header -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
        <div 
            class="h-8 bg-gradient-to-r from-white/5 via-white/10 to-transparent border-b border-white/10 flex justify-between items-center px-2 cursor-grab active:cursor-grabbing select-none relative"
            on:mousedown={startDrag}
            role="group"
            aria-label="Window Header"
        >
            <!-- Header Scanline -->
            <div class="absolute bottom-0 left-0 w-full h-[1px] bg-gradient-to-r from-neon-blue/0 via-neon-blue/50 to-neon-blue/0 opacity-50"></div>

            <div class="flex items-center gap-2 text-neon-blue font-mono text-[0.65rem] tracking-wider uppercase">
                <span class="opacity-70">{icon}</span>
                <span class="font-bold drop-shadow-[0_0_2px_rgba(0,243,255,0.5)]">{title}</span>
            </div>
            
            <div class="flex items-center gap-1 win-controls">
                <button 
                    class="p-1 hover:text-white text-white/50 transition-colors"
                    on:click={toggleMinimize}
                    aria-label="Minimize"
                >
                    <span class="material-icons-round text-[10px]">remove</span>
                </button>
                <button 
                    class="p-1 hover:text-neon-pink text-white/50 transition-colors"
                    on:click={closeWindow}
                    aria-label="Close"
                >
                    <span class="material-icons-round text-[10px]">close</span>
                </button>
            </div>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-auto bg-black/20 relative tech-scrollbar">
            <!-- Inner Grid Overlay -->
            <div class="absolute inset-0 bg-grid-pattern opacity-10 pointer-events-none" style="background-size: 20px 20px;"></div>
            <!-- Diagonal Lines Overlay -->
            <div class="absolute inset-0 opacity-5 pointer-events-none" style="background-image: repeating-linear-gradient(45deg, transparent, transparent 10px, #00f3ff 10px, #00f3ff 11px);"></div>
            
            <slot></slot>
        </div>
    </div>
{/if}

<style>
    .tech-scrollbar::-webkit-scrollbar {
        width: 4px;
        height: 4px;
    }
    
    .tech-scrollbar::-webkit-scrollbar-track {
        background: rgba(0, 0, 0, 0.2);
    }
    
    .tech-scrollbar::-webkit-scrollbar-thumb {
        background: rgba(0, 243, 255, 0.3);
        border-radius: 2px;
    }
    
    .tech-scrollbar::-webkit-scrollbar-thumb:hover {
        background: rgba(0, 243, 255, 0.6);
    }
</style>
