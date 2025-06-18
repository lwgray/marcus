<template>
  <div class="connection-status flex items-center gap-2">
    <div class="flex items-center gap-1.5">
      <div 
        class="w-2 h-2 rounded-full"
        :class="statusClass"
      ></div>
      <span class="text-xs text-gray-400">
        {{ isConnected ? 'Connected' : 'Disconnected' }}
      </span>
    </div>
    
    <div v-if="connectionError" class="text-xs text-red-400">
      {{ connectionError }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useWebSocketStore } from '@/stores/websocket'

const wsStore = useWebSocketStore()
const { isConnected, connectionError } = storeToRefs(wsStore)

const statusClass = computed(() => ({
  'bg-green-500': isConnected.value,
  'bg-red-500': !isConnected.value,
  'animate-pulse': isConnected.value
}))
</script>