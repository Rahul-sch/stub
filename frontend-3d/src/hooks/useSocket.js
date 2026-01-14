import { useEffect, useRef, useCallback } from 'react'
import { io } from 'socket.io-client'
import { useSensorStore, updateTransientRig, updateKetchupLine } from '../store/useSensorStore'

/**
 * Socket.IO hook for real-time sensor data streaming.
 *
 * Connects to Flask-SocketIO backend and handles:
 * - rig_telemetry: High-frequency sensor updates (10 Hz)
 * - anomaly_alert: ML-detected anomalies
 * - system_status: Backend health checks
 *
 * Uses transient state pattern to avoid React re-renders on telemetry updates.
 */
export function useSocket() {
  const socketRef = useRef(null)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 10

  const setConnected = useSensorStore((s) => s.setConnected)
  const setConnectionError = useSensorStore((s) => s.setConnectionError)
  const setLastUpdate = useSensorStore((s) => s.setLastUpdate)
  const addAlert = useSensorStore((s) => s.addAlert)
  const setSystemStatus = useSensorStore((s) => s.setSystemStatus)

  const handleTelemetry = useCallback((data) => {
    // Direct mutation of transient state - no React re-render
    const { machine_id, rpm, temperature, vibration, pressure, bearing_temp, anomaly_score } = data

    if (machine_id && ['A', 'B', 'C'].includes(machine_id)) {
      updateTransientRig(machine_id, {
        rpm: rpm ?? 0,
        temperature: temperature ?? 70,
        vibration: vibration ?? 0,
        pressure: pressure ?? 100,
        bearing_temp: bearing_temp ?? 120,
        anomalyScore: anomaly_score ?? 0,
        isRunning: rpm > 0
      })
    }

    // Update last update timestamp (throttled to 1 Hz for UI)
    setLastUpdate(data.timestamp)
  }, [setLastUpdate])

  const handleAnomalyAlert = useCallback((data) => {
    // Anomaly alerts trigger UI updates
    addAlert({
      type: 'anomaly',
      severity: data.anomaly_score > 0.8 ? 'critical' : 'warning',
      machine_id: data.machine_id,
      message: `Anomaly detected on RIG ${data.machine_id}`,
      score: data.anomaly_score,
      sensors: data.detected_sensors || [],
      method: data.detection_method || 'hybrid'
    })

    // Also update transient state with anomaly flag
    if (data.machine_id) {
      updateTransientRig(data.machine_id, {
        anomalyScore: data.anomaly_score
      })
    }
  }, [addAlert])

  const handleSystemStatus = useCallback((data) => {
    setSystemStatus(data)
  }, [setSystemStatus])

  // Ketchup Factory telemetry handler
  const handleKetchupTelemetry = useCallback((data) => {
    const {
      line_id, fill_level, viscosity, sauce_temp,
      cap_torque, bottle_flow_rate, label_alignment,
      bottle_count, anomaly_score, anomaly_type
    } = data

    if (line_id && line_id.startsWith('L')) {
      updateKetchupLine(line_id, {
        fill_level: fill_level ?? 95.0,
        viscosity: viscosity ?? 3500.0,
        sauce_temp: sauce_temp ?? 165.0,
        cap_torque: cap_torque ?? 2.5,
        bottle_flow_rate: bottle_flow_rate ?? 150.0,
        label_alignment: label_alignment ?? 0.0,
        bottle_count: bottle_count ?? 0,
        anomaly_score: anomaly_score ?? 0.0,
        anomaly_type: anomaly_type ?? null
      })
    }
  }, [])

  // Ketchup Factory anomaly alert handler
  const handleKetchupAnomalyAlert = useCallback((data) => {
    addAlert({
      type: 'ketchup_anomaly',
      severity: data.anomaly_score > 0.8 ? 'critical' : 'warning',
      line_id: data.line_id,
      message: `KETCHUP LINE ${data.line_id}: ${data.anomaly_type || 'Anomaly detected'}`,
      score: data.anomaly_score,
      anomaly_type: data.anomaly_type
    })

    // Also update transient state
    if (data.line_id) {
      updateKetchupLine(data.line_id, {
        anomaly_score: data.anomaly_score,
        anomaly_type: data.anomaly_type
      })
    }
  }, [addAlert])

  useEffect(() => {
    // Create socket connection to backend
    const socket = io('http://localhost:5000', {
      transports: ['websocket', 'polling'],
      path: '/socket.io',
      reconnection: true,
      reconnectionAttempts: maxReconnectAttempts,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 10000
    })

    socketRef.current = socket

    // Connection events
    socket.on('connect', () => {
      console.log('[Socket] Connected to server')
      reconnectAttempts.current = 0
      setConnected(true)

      // Subscribe to all machines
      socket.emit('subscribe_machines', { machines: ['A', 'B', 'C'] })
    })

    socket.on('disconnect', (reason) => {
      console.log('[Socket] Disconnected:', reason)
      setConnected(false)
    })

    socket.on('connect_error', (error) => {
      console.error('[Socket] Connection error:', error.message)
      reconnectAttempts.current++

      if (reconnectAttempts.current >= maxReconnectAttempts) {
        setConnectionError(`Failed to connect after ${maxReconnectAttempts} attempts`)
      }
    })

    // Data events - Rig Alpha
    socket.on('rig_telemetry', handleTelemetry)
    socket.on('anomaly_alert', handleAnomalyAlert)
    socket.on('system_status', handleSystemStatus)

    // Data events - Ketchup Factory
    socket.on('ketchup_telemetry', handleKetchupTelemetry)
    socket.on('ketchup_anomaly_alert', handleKetchupAnomalyAlert)

    // Confirmation events
    socket.on('machines_subscribed', (data) => {
      console.log('[Socket] Subscribed to machines:', data.machines)
    })

    // Cleanup on unmount
    return () => {
      console.log('[Socket] Cleaning up connection')
      socket.off('rig_telemetry', handleTelemetry)
      socket.off('anomaly_alert', handleAnomalyAlert)
      socket.off('system_status', handleSystemStatus)
      socket.off('ketchup_telemetry', handleKetchupTelemetry)
      socket.off('ketchup_anomaly_alert', handleKetchupAnomalyAlert)
      socket.disconnect()
    }
  }, [handleTelemetry, handleAnomalyAlert, handleSystemStatus, handleKetchupTelemetry, handleKetchupAnomalyAlert, setConnected, setConnectionError])

  // Return socket ref for manual emit calls if needed
  return socketRef
}

/**
 * Hook to emit events to the server.
 * Useful for control signals (acknowledge alerts, request data, etc.)
 */
export function useSocketEmit() {
  const socketRef = useRef(null)

  useEffect(() => {
    // Get existing socket or create new one
    socketRef.current = io('http://localhost:5000', {
      transports: ['websocket'],
      path: '/socket.io',
      autoConnect: false // Don't auto-connect, use existing
    })
  }, [])

  const emit = useCallback((event, data) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit(event, data)
    }
  }, [])

  return emit
}

export default useSocket
