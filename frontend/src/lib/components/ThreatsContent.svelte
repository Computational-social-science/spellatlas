<script>
    import { newsFeed } from '../stores.js';
    
    $: threats = $newsFeed.filter(i => i.has_error);
</script>

<div class="p-4 w-[400px] h-[400px]">
    <div class="space-y-2">
        {#each threats as item}
            <div class="bg-red-900/20 border border-red-500/30 p-2 rounded text-xs font-mono">
                <div class="flex justify-between text-red-400 mb-1">
                    <span>{item.country_name}</span>
                    <span>{new Date(item.timestamp).toLocaleTimeString()}</span>
                </div>
                <div class="text-white opacity-80 mb-1">{item.headline}</div>
                <div class="flex gap-2">
                    <span class="bg-red-500/20 px-1 rounded text-red-300">{item.error_detail.error_word}</span>
                    <span class="text-gray-500">→</span>
                    <span class="bg-green-500/20 px-1 rounded text-green-300">{item.error_detail.corrected_word}</span>
                </div>
            </div>
        {/each}
        {#if threats.length === 0}
            <div class="text-center text-green-500 mt-10">NO ACTIVE THREATS DETECTED</div>
        {/if}
    </div>
</div>