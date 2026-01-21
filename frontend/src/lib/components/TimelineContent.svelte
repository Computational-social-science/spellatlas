<script>
    import { timelineData } from '../stores.js';
    import { onMount } from 'svelte';

    /** @type {HTMLCanvasElement} */
    let canvas;
    /** @type {CanvasRenderingContext2D} */
    let ctx;

    $: if ($timelineData && canvas) {
        drawTimeline();
    }

    onMount(() => {
        if (canvas) {
            ctx = /** @type {CanvasRenderingContext2D} */ (canvas.getContext('2d'));
            drawTimeline();
        }
    });

    function drawTimeline() {
        if (!ctx || !canvas) return;
        const width = canvas.width;
        const height = canvas.height;
        const data = $timelineData;

        ctx.clearRect(0, 0, width, height);

        if (data.length === 0) {
            ctx.fillStyle = 'rgba(255,255,255,0.2)';
            ctx.font = '12px monospace';
            ctx.fillText('AWAITING DATA...', 10, 20);
            return;
        }

        const maxEvents = Math.max(...data.map(d => d.totalEvents), 1);
        const barWidth = (width - 40) / 30; // Show last 30 snapshots

        data.slice(-30).forEach((day, i) => {
            const x = i * barWidth + 10;
            const h = (day.totalEvents / maxEvents) * (height - 20);
            const y = height - h - 10;
            
            // Total
            ctx.fillStyle = '#00f3ff';
            ctx.fillRect(x, y, barWidth - 2, h);

            // Errors
            const errH = (day.errorEvents / maxEvents) * (height - 20);
            ctx.fillStyle = '#ff4500';
            ctx.fillRect(x, height - errH - 10, barWidth - 2, errH);
        });
    }
</script>

<div class="p-4 w-[500px] h-[300px]">
    <div class="flex justify-between mb-2 text-xs font-mono text-gray-400">
        <span>HISTORY</span>
        <span>LAST 30 SNAPSHOTS</span>
    </div>
    <canvas bind:this={canvas} width="460" height="250" class="w-full h-full bg-black/20 rounded border border-white/5"></canvas>
</div>