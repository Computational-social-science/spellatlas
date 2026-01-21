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
    class="pointer-events-auto absolute flex flex-col bg-gray-900 border border-cyan-500/30 rounded-lg shadow-[0_0_15px_rgba(6,182,212,0.15)] overflow-hidden transition-all duration-200"
    style="left: {state.position.x}px; top: {state.position.y}px; width: {state.minimized ? '200px' : '400px'}; height: {state.minimized ? '40px' : 'auto'}; z-index: 50;"
    transition:scale={{duration: 300, easing: quintOut, start: 0.95, opacity: 0}}
  >
    <!-- Header -->
    <div 
      class="h-10 bg-gray-800/80 backdrop-blur border-b border-white/10 flex items-center justify-between px-3 cursor-move select-none"
      on:mousedown={startDrag}
    >
      <div class="flex items-center gap-2 text-cyan-400 font-mono text-sm">
        <span>{icon}</span>
        <span class="font-bold tracking-wider">{title}</span>
      </div>
      <div class="flex items-center gap-2">
        <button 
          class="w-6 h-6 flex items-center justify-center rounded hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
          on:click={toggleMinimize}
        >
          {state.minimized ? '□' : '_'}
        </button>
        <button 
          class="w-6 h-6 flex items-center justify-center rounded hover:bg-red-500/20 text-gray-400 hover:text-red-400 transition-colors"
          on:click={closeWindow}
        >
          ✕
        </button>
      </div>
    </div>

    <!-- Content -->
    {#if !state.minimized}
      <div class="flex-1 overflow-auto bg-black/80 p-4 min-h-[200px] max-h-[60vh] text-gray-300 font-mono text-sm">
        <slot></slot>
      </div>
    {/if}
  </div>
{/if}
