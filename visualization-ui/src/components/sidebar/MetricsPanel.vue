<template>
  <div class="metrics-panel p-4">
    <h3 class="text-lg font-medium mb-4">System Metrics</h3>
    
    <div class="space-y-4">
      <!-- Active Workers -->
      <div class="metric-card p-4 bg-dark-surface rounded-lg">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm text-gray-400">Active Workers</span>
          <svg class="w-5 h-5 text-worker-primary" fill="currentColor" viewBox="0 0 20 20">
            <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z"/>
          </svg>
        </div>
        <div class="text-3xl font-bold text-worker-primary">{{ activeWorkerCount }}</div>
        <div class="text-xs text-gray-500 mt-1">{{ workerNodes.length }} total registered</div>
      </div>
      
      <!-- Tasks Progress -->
      <div class="metric-card p-4 bg-dark-surface rounded-lg">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm text-gray-400">Task Progress</span>
          <svg class="w-5 h-5 text-kanban-primary" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M3 3a1 1 0 011-1h12a1 1 0 011 1v3a1 1 0 01-.293.707L12 11.414V15a1 1 0 01-.293.707l-2 2A1 1 0 018 17v-5.586L3.293 6.707A1 1 0 013 6V3z" clip-rule="evenodd"/>
          </svg>
        </div>
        <div class="flex items-baseline gap-2">
          <div class="text-3xl font-bold text-kanban-primary">{{ tasksInProgress }}</div>
          <span class="text-sm text-gray-500">in progress</span>
        </div>
        <div class="mt-2 h-2 bg-gray-700 rounded-full overflow-hidden">
          <div 
            class="h-full bg-kanban-primary transition-all duration-500"
            :style="{ width: `${completionRate}%` }"
          />
        </div>
        <div class="text-xs text-gray-500 mt-1">{{ completionRate }}% completion rate</div>
      </div>
      
      <!-- Decision Confidence -->
      <div class="metric-card p-4 bg-dark-surface rounded-lg">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm text-gray-400">Decision Confidence</span>
          <svg class="w-5 h-5 text-decision-primary" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z"/>
            <path fill-rule="evenodd" d="M4 5a2 2 0 012-2 1 1 0 000 2H6a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2 1 1 0 100-2 2 2 0 012 2v8a2 2 0 002 2h2a1 1 0 110 2h-2a2 2 0 01-2-2v-2a2 2 0 01-2-2H6a2 2 0 00-2 2v2a2 2 0 01-2 2H2a1 1 0 110-2h2a2 2 0 002-2V5z" clip-rule="evenodd"/>
          </svg>
        </div>
        <div class="text-3xl font-bold text-decision-primary">{{ avgConfidence }}%</div>
        <div class="text-xs text-gray-500 mt-1">{{ totalDecisions }} decisions today</div>
      </div>
      
      <!-- Event Rate -->
      <div class="metric-card p-4 bg-dark-surface rounded-lg">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm text-gray-400">Event Rate</span>
          <svg class="w-5 h-5 text-pm-primary" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clip-rule="evenodd"/>
          </svg>
        </div>
        <div class="text-3xl font-bold text-pm-primary">{{ eventStats.lastMinute }}</div>
        <div class="text-xs text-gray-500 mt-1">events per minute</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useWorkflowStore } from '@/stores/workflow'
import { useEventStore } from '@/stores/events'

const workflowStore = useWorkflowStore()
const eventStore = useEventStore()
const { activeNodes, workerNodes, nodes } = storeToRefs(workflowStore)
const { eventStats } = storeToRefs(eventStore)

const activeWorkerCount = computed(() => 
  workerNodes.value.filter(n => n.data.status === 'working' || n.data.status === 'active').length
)

const pmAgent = computed(() => 
  nodes.value.find(n => n.id === 'pm-agent')
)

const kanbanBoard = computed(() => 
  nodes.value.find(n => n.id === 'kanban-board')
)

const tasksInProgress = computed(() => 
  kanbanBoard.value?.data?.metrics?.inProgress || 0
)

const completionRate = computed(() => {
  const total = kanbanBoard.value?.data?.metrics?.totalTasks || 0
  const completed = kanbanBoard.value?.data?.metrics?.completed || 0
  return total > 0 ? Math.round((completed / total) * 100) : 0
})

const avgConfidence = computed(() => 
  Math.round((pmAgent.value?.data?.metrics?.avgConfidence || 0) * 100)
)

const totalDecisions = computed(() => 
  pmAgent.value?.data?.metrics?.decisionsToday || 0
)
</script>