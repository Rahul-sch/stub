import { useSensorStore, getTransientState, getKetchupTransientState } from '../store/useSensorStore'
import { useEffect, useState } from 'react'

/**
 * Heads-Up Display overlay for the 3D Digital Twin.
 *
 * Features:
 * - Connection status indicator
 * - Crosshair reticle
 * - Alert notifications panel (Rig + Ketchup)
 * - Quick stats for each rig/line
 * - Controls hint
 * - View mode toggle (Rig Alpha / Ketchup Factory)
 */
export function HUD() {
  const connected = useSensorStore((s) => s.connected)
  const connectionError = useSensorStore((s) => s.connectionError)
  const alerts = useSensorStore((s) => s.alerts)
  const selectedRig = useSensorStore((s) => s.selectedRig)
  const selectedKetchupLine = useSensorStore((s) => s.selectedKetchupLine)
  const viewMode = useSensorStore((s) => s.viewMode)
  const dismissAlert = useSensorStore((s) => s.dismissAlert)
  const setViewMode = useSensorStore((s) => s.setViewMode)

  return (
    <div className="fixed inset-0 pointer-events-none font-mono z-50">
      {/* Top-left: Connection Status + View Toggle */}
      <div className="absolute top-4 left-4">
        <ConnectionStatus connected={connected} error={connectionError} />
        <ViewModeToggle viewMode={viewMode} setViewMode={setViewMode} />
      </div>

      {/* Top-right: Alerts Panel */}
      <AlertsPanel alerts={alerts} onDismiss={dismissAlert} />

      {/* Center: Crosshair */}
      <Crosshair />

      {/* Bottom-left: Quick Stats (based on view mode) */}
      {viewMode === 'rig' ? <QuickStats /> : <KetchupQuickStats />}

      {/* Bottom-right: Controls & Branding */}
      <ControlsHint viewMode={viewMode} />

      {/* Selected Info Panel (Rig or Ketchup Line) */}
      {selectedRig && <RigInfoPanel rigId={selectedRig} />}
      {selectedKetchupLine && <KetchupLineInfoPanel lineId={selectedKetchupLine} />}
    </div>
  )
}

/**
 * View mode toggle (Rig Alpha / Ketchup Factory)
 */
function ViewModeToggle({ viewMode, setViewMode }) {
  return (
    <div className="mt-3 pointer-events-auto">
      <div className="flex gap-1 text-xs">
        <button
          onClick={() => setViewMode('rig')}
          className={`px-2 py-1 rounded transition-colors ${
            viewMode === 'rig'
              ? 'bg-rig-cyan text-black'
              : 'bg-black/50 text-gray-400 hover:text-white border border-gray-700'
          }`}
        >
          RIG ALPHA
        </button>
        <button
          onClick={() => setViewMode('ketchup')}
          className={`px-2 py-1 rounded transition-colors ${
            viewMode === 'ketchup'
              ? 'bg-red-600 text-white'
              : 'bg-black/50 text-gray-400 hover:text-white border border-gray-700'
          }`}
        >
          KETCHUP
        </button>
      </div>
    </div>
  )
}

/**
 * Connection status indicator
 */
function ConnectionStatus({ connected, error }) {
  return (
    <div>
      <div className={`
        flex items-center gap-2 px-3 py-2 rounded
        ${connected
          ? 'bg-black/70 border border-rig-green/50'
          : 'bg-black/70 border border-rig-red/50'
        }
      `}>
        <div className={`
          w-2 h-2 rounded-full
          ${connected ? 'bg-rig-green animate-pulse' : 'bg-rig-red'}
        `} />
        <span className={`text-xs ${connected ? 'text-rig-green' : 'text-rig-red'}`}>
          {connected ? 'LIVE' : error || 'DISCONNECTED'}
        </span>
      </div>

      {connected && (
        <div className="mt-2 text-xs text-gray-500">
          <span className="text-rig-cyan">●</span> Streaming @ 10 Hz
        </div>
      )}
    </div>
  )
}

/**
 * Alerts notification panel (supports both Rig and Ketchup alerts)
 */
function AlertsPanel({ alerts, onDismiss }) {
  if (alerts.length === 0) return null

  return (
    <div className="absolute top-4 right-4 w-80 pointer-events-auto">
      <div className="hud-panel-danger p-3">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-rig-red text-sm font-semibold flex items-center gap-2">
            <span className="animate-pulse">⚠</span>
            ALERTS ({alerts.length})
          </h4>
        </div>

        <div className="space-y-2 max-h-48 overflow-y-auto hud-scroll">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={`
                text-xs p-2 rounded border-l-2
                ${alert.severity === 'critical'
                  ? 'bg-red-900/30 border-rig-red text-red-200'
                  : 'bg-yellow-900/30 border-rig-yellow text-yellow-200'
                }
              `}
            >
              <div className="flex justify-between items-start">
                <div>
                  {alert.type === 'ketchup_anomaly' ? (
                    <span className="font-semibold">[{alert.line_id}]</span>
                  ) : (
                    <span className="font-semibold">[RIG {alert.machine_id}]</span>
                  )}
                  <span className="ml-2">{alert.message}</span>
                </div>
                <button
                  onClick={() => onDismiss(alert.id)}
                  className="text-gray-400 hover:text-white ml-2"
                >
                  ×
                </button>
              </div>
              <div className="text-gray-400 mt-1">
                Score: {((alert.score || 0) * 100).toFixed(0)}%
                {alert.method && ` | Method: ${alert.method.toUpperCase()}`}
                {alert.anomaly_type && ` | Type: ${alert.anomaly_type.toUpperCase()}`}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

/**
 * Center crosshair reticle
 */
function Crosshair() {
  return (
    <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
      <div className="w-6 h-6 border border-rig-cyan/40 rounded-full" />
      <div className="absolute top-1/2 left-1/2 w-1 h-1 bg-rig-cyan rounded-full transform -translate-x-1/2 -translate-y-1/2" />
      <div className="absolute top-1/2 left-0 w-1.5 h-px bg-rig-cyan/40 transform -translate-y-1/2 -translate-x-2" />
      <div className="absolute top-1/2 right-0 w-1.5 h-px bg-rig-cyan/40 transform -translate-y-1/2 translate-x-2" />
      <div className="absolute left-1/2 top-0 w-px h-1.5 bg-rig-cyan/40 transform -translate-x-1/2 -translate-y-2" />
      <div className="absolute left-1/2 bottom-0 w-px h-1.5 bg-rig-cyan/40 transform -translate-x-1/2 translate-y-2" />
    </div>
  )
}

/**
 * Quick stats panel for Rig Alpha
 */
function QuickStats() {
  const [stats, setStats] = useState({ A: {}, B: {}, C: {} })

  useEffect(() => {
    const interval = setInterval(() => {
      const transient = getTransientState()
      setStats({
        A: { ...transient.rigs.A },
        B: { ...transient.rigs.B },
        C: { ...transient.rigs.C }
      })
    }, 500)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="absolute bottom-16 left-4">
      <div className="hud-panel p-3 text-xs">
        <h4 className="text-rig-cyan text-sm mb-2 font-semibold">RIG STATUS</h4>
        <div className="space-y-2">
          {['A', 'B', 'C'].map((rigId) => (
            <RigStatRow key={rigId} rigId={rigId} data={stats[rigId]} />
          ))}
        </div>
      </div>
    </div>
  )
}

/**
 * Quick stats panel for Ketchup Factory (shows line grid overview)
 */
function KetchupQuickStats() {
  const [stats, setStats] = useState({})

  useEffect(() => {
    const interval = setInterval(() => {
      const transient = getKetchupTransientState()
      const newStats = {}
      Object.keys(transient.lines).forEach(lineId => {
        newStats[lineId] = { ...transient.lines[lineId] }
      })
      setStats(newStats)
    }, 500)
    return () => clearInterval(interval)
  }, [])

  // Create 5x5 grid of lines
  const grid = []
  for (let row = 0; row < 5; row++) {
    const rowLines = []
    for (let col = 0; col < 5; col++) {
      const lineNum = row * 5 + col + 1
      const lineId = `L${String(lineNum).padStart(2, '0')}`
      rowLines.push({ lineId, data: stats[lineId] || {} })
    }
    grid.push(rowLines)
  }

  return (
    <div className="absolute bottom-16 left-4">
      <div className="hud-panel p-3 text-xs">
        <h4 className="text-red-500 text-sm mb-2 font-semibold">KETCHUP FACTORY STATUS</h4>

        {/* Mini grid visualization */}
        <div className="grid grid-cols-5 gap-1 mb-3">
          {grid.flat().map(({ lineId, data }) => {
            const hasAnomaly = (data?.anomaly_score || 0) > 0.5
            const fillNormal = (data?.fill_level || 95) >= 88 && (data?.fill_level || 95) <= 98
            return (
              <div
                key={lineId}
                className={`w-6 h-6 flex items-center justify-center text-[8px] rounded
                  ${hasAnomaly ? 'bg-red-600 animate-pulse' : fillNormal ? 'bg-green-800' : 'bg-yellow-700'}
                `}
                title={`${lineId}: Fill ${data?.fill_level?.toFixed(0) || 0}%`}
              >
                {lineId.substring(1)}
              </div>
            )
          })}
        </div>

        {/* Summary stats */}
        <div className="flex gap-4 text-[10px]">
          <div>
            <span className="text-gray-400">Active Lines:</span>
            <span className="text-green-400 ml-1">25</span>
          </div>
          <div>
            <span className="text-gray-400">Anomalies:</span>
            <span className="text-red-400 ml-1">
              {Object.values(stats).filter(s => (s.anomaly_score || 0) > 0.5).length}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * Single rig stat row
 */
function RigStatRow({ rigId, data }) {
  const hasAnomaly = (data?.anomalyScore || 0) > 0.5
  const tempColor = (data?.temperature || 70) > 85 ? 'text-rig-red' : 'text-rig-green'
  const vibColor = (data?.vibration || 0) > 4.5 ? 'text-rig-yellow' : 'text-rig-green'

  return (
    <div className={`flex items-center gap-3 ${hasAnomaly ? 'text-rig-red' : 'text-gray-300'}`}>
      <span className="font-bold w-4">{rigId}</span>
      <div className="flex gap-4 text-[10px]">
        <span>RPM: <span className="text-rig-cyan">{(data?.rpm || 0).toFixed(0)}</span></span>
        <span>TEMP: <span className={tempColor}>{(data?.temperature || 0).toFixed(1)}°F</span></span>
        <span>VIB: <span className={vibColor}>{(data?.vibration || 0).toFixed(2)}</span></span>
        {hasAnomaly && <span className="text-rig-red animate-pulse">⚠ ANOMALY</span>}
      </div>
    </div>
  )
}

/**
 * Controls hint at bottom
 */
function ControlsHint({ viewMode }) {
  return (
    <div className="absolute bottom-4 left-4 right-4 flex justify-between items-end pointer-events-auto">
      <div className="text-gray-500 text-xs">
        <span className="text-gray-400">WASD</span> Move |
        <span className="text-gray-400"> MOUSE</span> Look |
        <span className="text-gray-400"> CLICK</span> Select |
        <span className="text-gray-400"> ESC</span> Deselect
      </div>

      <div className="flex flex-col items-end gap-2">
        <div className={`text-xs ${viewMode === 'ketchup' ? 'text-red-400/60' : 'text-rig-cyan/40'}`}>
          {viewMode === 'ketchup' ? 'KETCHUP FACTORY DIGITAL TWIN v1.0' : 'RIG ALPHA DIGITAL TWIN v2.0'}
        </div>

        {/* Dashboard Link Button */}
        <a
          href="http://localhost:5000"
          target="_blank"
          rel="noopener noreferrer"
          className="px-3 py-1 text-xs rounded bg-black/60 border border-gray-600 text-gray-300 hover:text-white hover:border-gray-400 transition-colors"
        >
          📊 ORIGINAL DASHBOARD
        </a>
      </div>
    </div>
  )
}

/**
 * Detailed rig info panel (when selected)
 */
function RigInfoPanel({ rigId }) {
  const [data, setData] = useState({})

  useEffect(() => {
    const interval = setInterval(() => {
      setData({ ...getTransientState().rigs[rigId] })
    }, 100)
    return () => clearInterval(interval)
  }, [rigId])

  return (
    <div className="absolute top-1/2 right-4 transform -translate-y-1/2 pointer-events-auto">
      <div className="hud-panel p-4 w-64">
        <h3 className="text-rig-cyan text-lg font-bold mb-3">
          RIG {rigId} <span className="text-xs text-gray-400">INSPECTION</span>
        </h3>

        <div className="space-y-3 text-sm">
          <DataRow label="RPM" value={data.rpm?.toFixed(0)} unit="" normal={true} />
          <DataRow label="Temperature" value={data.temperature?.toFixed(1)} unit="°F" normal={(data.temperature || 70) < 85} />
          <DataRow label="Vibration" value={data.vibration?.toFixed(2)} unit="mm/s" normal={(data.vibration || 0) < 4.5} />
          <DataRow label="Pressure" value={data.pressure?.toFixed(0)} unit="PSI" normal={true} />
          <DataRow label="Bearing Temp" value={data.bearing_temp?.toFixed(0)} unit="°F" normal={(data.bearing_temp || 120) < 160} />

          <div className="border-t border-gray-700 pt-2 mt-2">
            <DataRow label="Anomaly Score" value={((data.anomalyScore || 0) * 100).toFixed(0)} unit="%" normal={(data.anomalyScore || 0) < 0.5} />
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * Detailed ketchup line info panel (when selected)
 */
function KetchupLineInfoPanel({ lineId }) {
  const [data, setData] = useState({})

  useEffect(() => {
    const interval = setInterval(() => {
      setData({ ...getKetchupTransientState().lines[lineId] })
    }, 100)
    return () => clearInterval(interval)
  }, [lineId])

  const fillNormal = (data?.fill_level || 95) >= 88 && (data?.fill_level || 95) <= 98
  const viscNormal = (data?.viscosity || 3500) >= 2800 && (data?.viscosity || 3500) <= 4200
  const tempNormal = (data?.sauce_temp || 165) >= 145 && (data?.sauce_temp || 165) <= 180
  const torqueNormal = (data?.cap_torque || 2.5) >= 1.8 && (data?.cap_torque || 2.5) <= 3.2
  const flowNormal = (data?.bottle_flow_rate || 150) >= 90 && (data?.bottle_flow_rate || 150) <= 180
  const labelNormal = Math.abs(data?.label_alignment || 0) <= 3

  return (
    <div className="absolute top-1/2 right-4 transform -translate-y-1/2 pointer-events-auto">
      <div className="hud-panel-ketchup p-4 w-72">
        <h3 className="text-red-500 text-lg font-bold mb-3">
          {lineId} <span className="text-xs text-gray-400">INSPECTION</span>
        </h3>

        {/* Fill Level Bar */}
        <div className="mb-4">
          <div className="flex justify-between text-xs mb-1">
            <span className="text-gray-400">FILL LEVEL</span>
            <span className={fillNormal ? 'text-green-400' : 'text-yellow-400'}>
              {data?.fill_level?.toFixed(1) || 0}%
            </span>
          </div>
          <div className="h-2 bg-gray-800 rounded overflow-hidden">
            <div
              className={`h-full rounded transition-all ${
                fillNormal ? 'bg-red-600' : data?.fill_level > 98 ? 'bg-yellow-500' : 'bg-orange-500'
              }`}
              style={{ width: `${data?.fill_level || 0}%` }}
            />
          </div>
        </div>

        {/* Sensor Grid */}
        <div className="space-y-2 text-sm">
          <DataRow label="Viscosity" value={data?.viscosity?.toFixed(0)} unit="cP" normal={viscNormal} />
          <DataRow label="Sauce Temp" value={data?.sauce_temp?.toFixed(1)} unit="°F" normal={tempNormal} />
          <DataRow label="Cap Torque" value={data?.cap_torque?.toFixed(2)} unit="Nm" normal={torqueNormal} />
          <DataRow label="Flow Rate" value={data?.bottle_flow_rate?.toFixed(0)} unit="b/min" normal={flowNormal} />
          <DataRow label="Label Align" value={data?.label_alignment?.toFixed(1)} unit="°" normal={labelNormal} />

          <div className="border-t border-gray-700 pt-2 mt-2">
            <DataRow label="Bottle Count" value={data?.bottle_count?.toLocaleString()} unit="" normal={true} />
            <DataRow
              label="Anomaly Score"
              value={((data?.anomaly_score || 0) * 100).toFixed(0)}
              unit="%"
              normal={(data?.anomaly_score || 0) < 0.5}
            />
          </div>
        </div>

        {/* Anomaly Alert */}
        {(data?.anomaly_score || 0) > 0.5 && (
          <div className="mt-3 p-2 bg-red-900/50 border border-red-500 rounded animate-pulse">
            <span className="text-red-400 text-xs font-bold">
              ⚠ {data?.anomaly_type?.toUpperCase() || 'ANOMALY'} DETECTED
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Data row helper
 */
function DataRow({ label, value, unit, normal }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-gray-400">{label}</span>
      <span className={normal ? 'text-green-400' : 'text-red-400'}>
        {value || '—'} {unit}
      </span>
    </div>
  )
}

export default HUD
