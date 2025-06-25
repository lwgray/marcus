import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import HealthAnalysisPanel from '@/components/HealthAnalysisPanel.vue'
import { useWebSocketStore } from '@/stores/websocket'

// Mock fetch globally
global.fetch = vi.fn()

describe('HealthAnalysisPanel', () => {
  let wrapper
  let mockSocket
  let pinia

  beforeEach(() => {
    // Reset mocks
    vi.clearAllMocks()
    
    // Create pinia instance
    pinia = createPinia()
    
    // Mock socket
    mockSocket = {
      emit: vi.fn(),
      on: vi.fn(),
      off: vi.fn()
    }
    
    // Default fetch response
    fetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({})
    })
  })

  const createWrapper = (props = {}) => {
    wrapper = mount(HealthAnalysisPanel, {
      props,
      global: {
        plugins: [pinia]
      }
    })
    
    // Set socket in store
    const wsStore = useWebSocketStore()
    wsStore.socket = mockSocket
    
    return wrapper
  }

  it('renders no data state initially', () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 404
    })
    
    const wrapper = createWrapper()
    
    expect(wrapper.find('.no-data').exists()).toBe(true)
    expect(wrapper.text()).toContain('No health analysis available')
  })

  it('displays health data when available', async () => {
    const mockHealthData = {
      overall_health: 'green',
      timestamp: new Date().toISOString(),
      timeline_prediction: {
        on_track: true,
        confidence: 0.85,
        estimated_completion: 'On schedule'
      },
      risk_factors: [],
      recommendations: [],
      resource_optimization: []
    }
    
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockHealthData
    })
    
    const wrapper = createWrapper()
    await wrapper.vm.$nextTick()
    
    // Wait for async operations
    await new Promise(resolve => setTimeout(resolve, 100))
    
    expect(wrapper.find('.health-status').exists()).toBe(true)
    expect(wrapper.find('.health-green').exists()).toBe(true)
    expect(wrapper.text()).toContain('GREEN')
  })

  it('shows error message on fetch failure', async () => {
    fetch.mockRejectedValueOnce(new Error('Network error'))
    
    const wrapper = createWrapper()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))
    
    expect(wrapper.find('.error-message').exists()).toBe(true)
    expect(wrapper.text()).toContain('Network error')
  })

  it('runs initial analysis when button clicked', async () => {
    fetch
      .mockResolvedValueOnce({ ok: false, status: 404 }) // Initial fetch
      .mockResolvedValueOnce({ ok: true, json: async () => ({}) }) // History fetch
      .mockResolvedValueOnce({ // Analysis response
        ok: true,
        json: async () => ({
          overall_health: 'yellow',
          timestamp: new Date().toISOString()
        })
      })
    
    const wrapper = createWrapper()
    await wrapper.vm.$nextTick()
    
    const button = wrapper.find('.primary-btn')
    expect(button.exists()).toBe(true)
    
    await button.trigger('click')
    await wrapper.vm.$nextTick()
    
    // Check fetch was called with correct endpoint
    expect(fetch).toHaveBeenCalledWith(
      '/api/health/analyze',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
    )
  })

  it('displays risk factors correctly', async () => {
    const mockHealthData = {
      overall_health: 'yellow',
      timestamp: new Date().toISOString(),
      timeline_prediction: {
        on_track: false,
        confidence: 0.6,
        estimated_completion: '1 week behind'
      },
      risk_factors: [
        {
          type: 'resource',
          description: '3 tasks are blocked',
          severity: 'high',
          mitigation: 'Review and unblock tasks'
        },
        {
          type: 'timeline',
          description: 'Behind schedule',
          severity: 'medium',
          mitigation: 'Reprioritize tasks'
        }
      ],
      recommendations: [],
      resource_optimization: []
    }
    
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockHealthData
    })
    
    const wrapper = createWrapper()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))
    
    const riskFactors = wrapper.findAll('.risk-item')
    expect(riskFactors).toHaveLength(2)
    
    expect(wrapper.text()).toContain('3 tasks are blocked')
    expect(wrapper.text()).toContain('Review and unblock tasks')
  })

  it('displays recommendations', async () => {
    const mockHealthData = {
      overall_health: 'red',
      timestamp: new Date().toISOString(),
      timeline_prediction: {
        on_track: false,
        confidence: 0.3
      },
      risk_factors: [],
      recommendations: [
        {
          priority: 'high',
          action: 'Conduct emergency planning session',
          expected_impact: 'Restore project trajectory'
        }
      ],
      resource_optimization: []
    }
    
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockHealthData
    })
    
    const wrapper = createWrapper()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))
    
    expect(wrapper.find('.recommendations').exists()).toBe(true)
    expect(wrapper.text()).toContain('Conduct emergency planning session')
    expect(wrapper.find('.priority-high').exists()).toBe(true)
  })

  it('shows trends when available', async () => {
    const mockHealthData = {
      overall_health: 'green',
      timestamp: new Date().toISOString(),
      timeline_prediction: { on_track: true, confidence: 0.8 },
      trends: {
        health_direction: 'improving',
        confidence_change: 0.15,
        risk_change: 'decreasing'
      },
      risk_factors: [],
      recommendations: []
    }
    
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockHealthData
    })
    
    const wrapper = createWrapper()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))
    
    expect(wrapper.find('.trends').exists()).toBe(true)
    expect(wrapper.text()).toContain('improving')
    expect(wrapper.text()).toContain('+15.0%')
    expect(wrapper.text()).toContain('decreasing')
  })

  it('subscribes to WebSocket health updates on mount', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.$nextTick()
    
    expect(mockSocket.emit).toHaveBeenCalledWith('subscribe_health_updates', {})
    expect(mockSocket.on).toHaveBeenCalledWith('health_update', expect.any(Function))
  })

  it('unsubscribes from WebSocket on unmount', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.$nextTick()
    
    wrapper.unmount()
    
    expect(mockSocket.off).toHaveBeenCalledWith('health_update', expect.any(Function))
  })

  it('refreshes analysis when refresh button clicked', async () => {
    const mockHealthData = {
      overall_health: 'green',
      timestamp: new Date().toISOString(),
      timeline_prediction: { on_track: true, confidence: 0.9 },
      risk_factors: [],
      recommendations: []
    }
    
    fetch
      .mockResolvedValueOnce({ ok: true, json: async () => mockHealthData })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ history: [] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => mockHealthData })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ history: [] }) })
    
    const wrapper = createWrapper()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))
    
    const refreshBtn = wrapper.find('.refresh-btn')
    await refreshBtn.trigger('click')
    
    expect(fetch).toHaveBeenCalledWith(
      '/api/health/analyze',
      expect.any(Object)
    )
  })

  it('handles timeline prediction display', async () => {
    const mockHealthData = {
      overall_health: 'yellow',
      timestamp: new Date().toISOString(),
      timeline_prediction: {
        on_track: false,
        confidence: 0.65,
        estimated_completion: '2 weeks behind schedule',
        critical_path_risks: ['Resource constraints', 'Technical debt']
      },
      risk_factors: [],
      recommendations: []
    }
    
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockHealthData
    })
    
    const wrapper = createWrapper()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))
    
    expect(wrapper.text()).toContain('⚠ Off Track')
    expect(wrapper.text()).toContain('Confidence: 65%')
    expect(wrapper.text()).toContain('2 weeks behind schedule')
    expect(wrapper.text()).toContain('Resource constraints')
    expect(wrapper.text()).toContain('Technical debt')
  })

  it('displays health history when available', async () => {
    const mockHealthData = {
      overall_health: 'green',
      timestamp: new Date().toISOString(),
      timeline_prediction: { on_track: true, confidence: 0.8 },
      risk_factors: [],
      recommendations: []
    }
    
    const mockHistory = {
      history: [
        { timestamp: '2024-01-01T10:00:00', overall_health: 'green' },
        { timestamp: '2024-01-01T11:00:00', overall_health: 'yellow' },
        { timestamp: '2024-01-01T12:00:00', overall_health: 'green' }
      ]
    }
    
    fetch
      .mockResolvedValueOnce({ ok: true, json: async () => mockHealthData })
      .mockResolvedValueOnce({ ok: true, json: async () => mockHistory })
    
    const wrapper = createWrapper()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))
    
    expect(wrapper.find('.health-history').exists()).toBe(true)
    const historyItems = wrapper.findAll('.history-item')
    expect(historyItems).toHaveLength(3)
  })

  it('formats timestamps correctly', () => {
    const wrapper = createWrapper()
    const vm = wrapper.vm
    
    const timestamp = '2024-01-15T14:30:00'
    const formatted = vm.formatTime(timestamp)
    
    expect(formatted).toMatch(/Jan 15/)
    expect(formatted).toMatch(/2:30 PM/i)
    
    const shortFormatted = vm.formatTime(timestamp, true)
    expect(shortFormatted).toMatch(/2:30 PM/i)
    expect(shortFormatted).not.toMatch(/Jan/)
  })

  it('returns correct health icons', () => {
    const wrapper = createWrapper()
    const vm = wrapper.vm
    
    expect(vm.getHealthIcon('green')).toBe('✅')
    expect(vm.getHealthIcon('yellow')).toBe('⚠️')
    expect(vm.getHealthIcon('red')).toBe('🚨')
    expect(vm.getHealthIcon('unknown')).toBe('❓')
    expect(vm.getHealthIcon('invalid')).toBe('❓')
  })

  it('returns correct trend icons', () => {
    const wrapper = createWrapper()
    const vm = wrapper.vm
    
    expect(vm.getTrendIcon('improving')).toBe('↗️')
    expect(vm.getTrendIcon('stable')).toBe('→')
    expect(vm.getTrendIcon('declining')).toBe('↘️')
    expect(vm.getTrendIcon('unknown')).toBe('→')
  })
})