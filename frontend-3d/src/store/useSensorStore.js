import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'

/**
 * Transient state for high-frequency sensor updates.
 * This is mutated directly in useFrame callbacks to avoid React re-renders.
 *
 * Structure matches sensor_readings table columns:
 * - rpm: double precision (0-5000)
 * - temperature: double precision (60-100°F)
 * - vibration: double precision (0-10 mm/s)
 * - pressure: double precision (0-200 PSI)
 * - bearing_temp: integer (0-200°F)
 * - anomalyScore: float (0-1, from ML pipeline)
 */
const transientState = {
  rigs: {
    A: {
      rpm: 2500,
      temperature: 72,
      vibration: 1.5,
      pressure: 100,
      bearing_temp: 120,
      anomalyScore: 0,
      isRunning: true
    },
    B: {
      rpm: 2200,
      temperature: 75,
      vibration: 2.0,
      pressure: 95,
      bearing_temp: 125,
      anomalyScore: 0,
      isRunning: true
    },
    C: {
      rpm: 2800,
      temperature: 70,
      vibration: 1.2,
      pressure: 105,
      bearing_temp: 118,
      anomalyScore: 0,
      isRunning: true
    }
  }
}

/**
 * Ketchup Factory Transient State for 25 production lines.
 * Mutated directly in useFrame callbacks to avoid React re-renders.
 *
 * Ketchup-specific sensors:
 * - fill_level: 0-100% (bottle fill)
 * - viscosity: 2500-4500 cP (sauce thickness)
 * - sauce_temp: 140-185°F (sauce temperature)
 * - cap_torque: 1.5-3.5 Nm (cap tightening)
 * - bottle_flow_rate: 80-200 bottles/min
 * - label_alignment: -5 to +5 degrees
 * - anomaly_score: 0-1 (from ML pipeline)
 * - anomaly_type: string (overfill, underfill, viscosity_fault, etc.)
 */
const ketchupTransientState = {
  lines: Object.fromEntries(
    Array.from({ length: 25 }, (_, i) => [
      `L${String(i + 1).padStart(2, '0')}`,
      {
        fill_level: 95.0,
        viscosity: 3500.0,
        sauce_temp: 165.0,
        cap_torque: 2.5,
        bottle_flow_rate: 150.0,
        label_alignment: 0.0,
        bottle_count: 0,
        anomaly_score: 0.0,
        anomaly_type: null
      }
    ])
  )
}

/**
 * Direct access to transient state for useFrame callbacks.
 * Use this in animation loops to avoid triggering React re-renders.
 *
 * @example
 * useFrame((state, delta) => {
 *   const data = getTransientState().rigs['A']
 *   meshRef.current.rotation.y += (data.rpm / 5000) * 10 * delta
 * })
 */
export const getTransientState = () => transientState

/**
 * Update transient rig data directly.
 * Called from Socket.IO event handlers.
 */
export const updateTransientRig = (rigId, data) => {
  if (transientState.rigs[rigId]) {
    Object.assign(transientState.rigs[rigId], data)
  }
}

/**
 * Direct access to ketchup factory transient state for useFrame callbacks.
 * Use this in animation loops to avoid triggering React re-renders.
 *
 * @example
 * useFrame((state, delta) => {
 *   const data = getKetchupTransientState().lines['L01']
 *   conveyorRef.current.material.map.offset.x += (data.bottle_flow_rate / 150) * delta
 * })
 */
export const getKetchupTransientState = () => ketchupTransientState

/**
 * Update ketchup production line data directly.
 * Called from Socket.IO event handlers.
 */
export const updateKetchupLine = (lineId, data) => {
  if (ketchupTransientState.lines[lineId]) {
    Object.assign(ketchupTransientState.lines[lineId], data)
  }
}

/**
 * Main Zustand store for UI state that DOES trigger re-renders.
 * Use this for:
 * - Connection status
 * - Alert notifications
 * - Selected rig (for HUD focus)
 * - System settings
 */
export const useSensorStore = create(
  subscribeWithSelector((set, get) => ({
    // Connection state
    connected: false,
    connectionError: null,
    lastUpdate: null,

    // UI state
    selectedRig: null,
    selectedKetchupLine: null,
    showDebug: false,
    isPaused: false,
    viewMode: 'rig', // 'rig' or 'ketchup'

    // Alerts (triggers HUD re-render)
    alerts: [],
    maxAlerts: 10,

    // System info
    systemStatus: {
      kafka: 'unknown',
      database: 'unknown',
      ml: 'unknown'
    },

    // Actions
    setConnected: (connected) => set({ connected, connectionError: null }),
    setConnectionError: (error) => set({ connectionError: error, connected: false }),
    setLastUpdate: (timestamp) => set({ lastUpdate: timestamp }),

    setSelectedRig: (rigId) => set({ selectedRig: rigId }),
    clearSelectedRig: () => set({ selectedRig: null }),

    setSelectedKetchupLine: (lineId) => set({ selectedKetchupLine: lineId }),
    clearSelectedKetchupLine: () => set({ selectedKetchupLine: null }),

    setViewMode: (mode) => set({ viewMode: mode }),

    toggleDebug: () => set((state) => ({ showDebug: !state.showDebug })),
    togglePause: () => set((state) => ({ isPaused: !state.isPaused })),

    addAlert: (alert) => set((state) => ({
      alerts: [
        {
          id: Date.now(),
          timestamp: new Date().toISOString(),
          ...alert
        },
        ...state.alerts
      ].slice(0, state.maxAlerts)
    })),

    clearAlerts: () => set({ alerts: [] }),

    dismissAlert: (alertId) => set((state) => ({
      alerts: state.alerts.filter(a => a.id !== alertId)
    })),

    setSystemStatus: (status) => set((state) => ({
      systemStatus: { ...state.systemStatus, ...status }
    })),

    // Computed getters
    getAlertCount: () => get().alerts.length,
    hasActiveAlerts: () => get().alerts.some(a => a.severity === 'critical'),
  }))
)

export default useSensorStore
