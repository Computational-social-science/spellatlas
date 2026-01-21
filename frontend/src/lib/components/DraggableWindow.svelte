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
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div 
    bind:this={element}
    class="pointer-events-auto absolute flex flex-col bg-black/90 border border-[#00f3ff]/30 shadow-[0_0_15px_rgba(0,243,255,0.2)] backdrop-blur-md overflow-hidden transition-all duration-300 ease-out"
    style="left: {state.position.x}px; top: {state.position.y}px; z-index: {state.maximized ? 50 : 40}; width: {state.maximized ? '100vw' : 'auto'}; height: {state.maximized ? '100vh' : 'auto'}; {state.maximized ? 'left: 0; top: 0;' : ''} {state.minimized ? 'height: 40px;' : ''}"
    transition:scale={{duration: 200, easing: quintOut, start: 0.95}}
    on:mousedown={() => {
      // Bring to front logic could go here
    }}
  >
    <!-- Header -->
    <div 
      class="h-10 flex items-center justify-between px-3 bg-[#00f3ff]/10 border-b border-[#00f3ff]/20 cursor-grab active:cursor-grabbing select-none"
      on:mousedown={startDrag}
    >
      <div class="flex items-center gap-2">
        <span class="text-sm">{icon}</span>
        <span class="text-[#00f3ff] font-mono text-sm tracking-wider font-bold">{title}</span>
      </div>
      <div class="flex items-center gap-1">
        <button 
          class="w-6 h-6 flex items-center justify-center rounded hover:bg-[#00f3ff]/20 text-[#00f3ff]/70 hover:text-[#00f3ff] transition-colors"
          on:click|stopPropagation={toggleMinimize}
        >
          {state.minimized ? '□' : '_'}
        </button>
        <button 
          class="w-6 h-6 flex items-center justify-center rounded hover:bg-[#00f3ff]/20 text-[#00f3ff]/70 hover:text-[#00f3ff] transition-colors"
          on:click|stopPropagation={() => {
            windowState.update(s => {
              const state = s;
              return { ...state, [id]: { ...state[id], maximized: !state[id].maximized } };
            });
          }}
        >
          {state.maximized ? '❐' : '□'}
        </button>
        <button 
          class="w-6 h-6 flex items-center justify-center rounded hover:bg-red-500/20 text-red-400 hover:text-red-500 transition-colors"
          on:click|stopPropagation={closeWindow}
        >
          ×
        </button>
      </div>
    </div>

    <!-- Content -->
    {#if !state.minimized}
      <div class="flex-1 overflow-auto custom-scrollbar relative">
        <slot></slot>
      </div>
    {/if}
  </div>
{/if}

<style>
  .custom-scrollbar::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }
  .custom-scrollbar::-webkit-scrollbar-track {
    background: rgba(0, 243, 255, 0.05);
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: rgba(0, 243, 255, 0.2);
    border-radius: 3px;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: rgba(0, 243, 255, 0.4);
  }
</style>
