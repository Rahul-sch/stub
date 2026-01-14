# 3D FRONTEND CODE WALKTHROUGH
## React Three Fiber Digital Twin Implementation

**Document 06 of 09**  
**Reading Time:** 60-75 minutes  
**Level:** Advanced  
**Prerequisites:** Documents 01-05 + Basic React knowledge  

---

## 📋 TABLE OF CONTENTS

1. [React Three Fiber Overview](#1-react-three-fiber-overview)
2. [Main App Component](#2-main-app-component)
3. [WebSocket Integration](#3-websocket-integration)
4. [State Management (Zustand)](#4-state-management-zustand)
5. [RigModel Component](#5-rigmodel-component)
6. [Animation and Data Binding](#6-animation-and-data-binding)
7. [Performance Optimization](#7-performance-optimization)

---

## 1. REACT THREE FIBER OVERVIEW

### 1.1 What is React Three Fiber?

**React Three Fiber (R3F)** = React renderer for Three.js

**Normal React:**
```jsx
<div>
  <h1>Hello</h1>
  <button>Click</button>
</div>
```

**React Three Fiber:**
```jsx
<Canvas>
  <mesh>
    <boxGeometry />
    <meshStandardMaterial />
  </mesh>
</Canvas>
```

**Benefits:**
- Declarative 3D (like HTML for 3D)
- React hooks work in 3D
- Component reusability
- Automatic memory management

---

## 2. MAIN APP COMPONENT

### 2.1 App.jsx Structure

**Lines 1-10 (Imports):**
```jsx
import { Suspense, useEffect } from 'react'
import { Canvas } from '@react-three/fiber'
import { Loader, Preload } from '@react-three/drei'
import * as THREE from 'three'

import { FactoryScene } from './FactoryScene'
import { Effects } from './Effects'
import { HUD } from './HUD'
import { useSocket } from '../hooks/useSocket'
```

**Explanation:**

**`Suspense`**: React component for async loading
```jsx
<Suspense fallback={<Loading />}>
  <ExpensiveComponent />  {/* Loads async */}
</Suspense>
```

**`Canvas`**: R3F component creating WebGL context
- Sets up Three.js renderer
- Creates scene and camera
- Handles rendering loop

**`Loader`**: Progress bar for asset loading
**`Preload`**: Loads all assets upfront
**`THREE`**: Direct Three.js access for constants

### 2.2 Canvas Configuration

**Lines 29-49:**
```jsx
<Canvas
  shadows
  dpr={[1, 2]}
  gl={{
    antialias: true,
    toneMapping: THREE.ACESFilmicToneMapping,
    toneMappingExposure: 1.0,
    outputColorSpace: THREE.SRGBColorSpace,
    powerPreference: 'high-performance'
  }}
  camera={{
    fov: 65,
    near: 0.1,
    far: 500,
    position: [0, 2, 15]
  }}
  onCreated={({ gl }) => {
    gl.shadowMap.enabled = true
    gl.shadowMap.type = THREE.PCFSoftShadowMap
  }}
>
```

**Parameter Explanations:**

**`shadows`**: Enable shadow rendering
- More realistic
- Performance cost ~20%

**`dpr={[1, 2]}`**: Device pixel ratio
- `[1, 2]` = min 1.0, max 2.0
- Auto-adapts to screen (Retina displays use 2)
- Higher = Sharper but slower

**`antialias: true`**: Smooth edges
- Removes jagged lines
- Slight performance cost
- Essential for quality

**`toneMapping: THREE.ACESFilmicToneMapping`**: HDR tone mapping
- ACES = Academy Color Encoding System
- Used in film industry
- Makes bright areas glow realistically

**`toneMappingExposure: 1.0`**: Brightness
- 0.5 = Darker
- 1.0 = Normal (default)
- 2.0 = Brighter

**`outputColorSpace: THREE.SRGBColorSpace`**: Color space
- sRGB = Standard for monitors
- Ensures correct colors

**`powerPreference: 'high-performance'`**: GPU usage
- Use discrete GPU if available
- Better for complex scenes

**`fov: 65`**: Field of view (degrees)
- 60-75 = Natural (similar to human)
- 90+ = Wide angle (fisheye effect)
- 30- = Telephoto (narrow)

**`near: 0.1, far: 500`**: Clipping planes
- Objects < 0.1 units from camera: not rendered
- Objects > 500 units from camera: not rendered
- Balance: Small near, large far = Z-fighting
- Balance: Large near, small far = missed objects

**`position: [0, 2, 15]`**: Initial camera position
- X=0: Centered horizontally
- Y=2: 2 meters above ground
- Z=15: 15 meters back from origin

**`PCFSoftShadowMap`**: Shadow quality
- PCF = Percentage Closer Filtering
- Soft edges on shadows
- Better quality than basic shadows

---

## 3. WEBSOCKET INTEGRATION

### 3.1 useSocket Hook

**Lines 15-24 (useSocket.js):**
```jsx
export function useSocket() {
  const socketRef = useRef(null)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 10

  const setConnected = useSensorStore((s) => s.setConnected)
  const setConnectionError = useSensorStore((s) => s.setConnectionError)
  const setLastUpdate = useSensorStore((s) => s.setLastUpdate)
  const addAlert = useSensorStore((s) => s.addAlert)
```

**Explanation:**

**`useRef(null)`**: Store socket instance
- Persists across re-renders
- Doesn't trigger re-renders when changed
- Access via `.current`

**Store selectors:**
```jsx
const setConnected = useSensorStore((s) => s.setConnected)
```
- Extract function from Zustand store
- Only this component subscribes to this function
- Prevents unnecessary re-renders

### 3.2 Socket Connection Setup

**Lines 113-136:**
```jsx
useEffect(() => {
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

  socket.on('connect', () => {
    console.log('[Socket] Connected')
    reconnectAttempts.current = 0
    setConnected(true)

    // Subscribe to machines
    socket.emit('subscribe_machines', { machines: ['A', 'B', 'C'] })
  })

  socket.on('disconnect', (reason) => {
    console.log('[Socket] Disconnected:', reason)
    setConnected(false)
  })
```

**Configuration Explained:**

**`transports: ['websocket', 'polling']`**
- Try WebSocket first (best performance)
- Fall back to HTTP polling if WebSocket fails
- Polling = Request every N seconds

**`reconnection: true`**: Auto-reconnect
- If connection lost, automatically retry
- Essential for robust real-time apps

**`reconnectionAttempts: 10`**: Retry limit
- Try 10 times before giving up
- Prevents infinite retry on permanent failures

**`reconnectionDelay: 1000`**: Initial delay
- Wait 1 second before first retry
- Increases exponentially

**`reconnectionDelayMax: 5000`**: Max delay
- Cap at 5 seconds between retries
- Exponential backoff: 1s, 2s, 4s, 5s, 5s...

**`timeout: 10000`**: Connection timeout
- 10 seconds to establish connection
- If slower, consider failed

### 3.3 Telemetry Event Handler

**Lines 26-44:**
```jsx
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
```

**Explanation:**

**`useCallback`**: Memoize function
```jsx
const handleTelemetry = useCallback((data) => { ... }, [setLastUpdate])
```
- Creates function once
- Doesn't recreate on every render
- `[setLastUpdate]`: Dependencies (recreate if this changes)

**`??` Nullish coalescing:**
```jsx
rpm: rpm ?? 0
```
- If `rpm` is null or undefined, use 0
- Similar to `||` but only for null/undefined
- `0 ?? 1 = 0` (0 is valid)
- `null ?? 1 = 1` (null is not valid)

**`updateTransientRig()`**: Direct mutation
```jsx
updateTransientRig(machine_id, { rpm: 3500 })
```
- Mutates `transientState` object directly
- Does NOT trigger React re-render
- `useFrame` reads this state every frame (60 Hz)

**Why transient state?**
```
Without (normal React state):
  10 Hz socket updates
  → 10 setState() calls/second
  → 10 React re-renders/second
  → Lag, jank, poor performance

With (transient):
  10 Hz socket updates
  → updateTransientRig() mutation (no re-render)
  → useFrame() reads state (60 FPS)
  → Smooth, performant
```

---

## 4. STATE MANAGEMENT (ZUSTAND)

### 4.1 Transient State Pattern

**Lines 16-46 (useSensorStore.js):**
```jsx
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
    B: { ... },
    C: { ... }
  }
}

export const getTransientState = () => transientState

export const updateTransientRig = (rigId, data) => {
  if (transientState.rigs[rigId]) {
    Object.assign(transientState.rigs[rigId], data)
  }
}
```

**Key Points:**

**Plain JavaScript Object:**
- NOT a React state
- NOT managed by Zustand
- Just a regular object in module scope

**`Object.assign()`**: Shallow merge
```jsx
Object.assign(target, source)

Before: rigs.A = { rpm: 2500, temp: 72 }
Update: Object.assign(rigs.A, { rpm: 3500 })
After:  rigs.A = { rpm: 3500, temp: 72 }
```

**Why this works:**
```jsx
// Socket.IO receives update (10 Hz)
socket.on('rig_telemetry', (data) => {
  updateTransientRig('A', data)  // Mutate object
})

// Animation loop reads (60 FPS)
useFrame(() => {
  const data = getTransientState().rigs['A']  // Read object
  mesh.rotation.y = data.rpm * 0.0001  // Apply to 3D
})
```

### 4.2 UI State (Normal Zustand)

**Lines 133-199:**
```jsx
export const useSensorStore = create(
  subscribeWithSelector((set, get) => ({
    // State
    connected: false,
    alerts: [],
    selectedRig: null,

    // Actions
    setConnected: (connected) => set({ connected }),
    addAlert: (alert) => set((state) => ({
      alerts: [alert, ...state.alerts].slice(0, 10)
    })),
    setSelectedRig: (rigId) => set({ selectedRig: rigId })
  }))
)
```

**When to use which:**

| Data | State Type | Reason |
|------|-----------|--------|
| RPM, temp, vibration | Transient | 10 Hz updates, read in useFrame |
| Connection status | Zustand | Triggers UI re-render (indicator) |
| Alerts | Zustand | Triggers UI re-render (notification) |
| Selected rig | Zustand | Triggers UI re-render (HUD) |

---

## 5. RIGMODEL COMPONENT

### 5.1 Component Structure

**Lines 20-29:**
```jsx
export function RigModel({ rigId, position = [0, 0, 0], label = 'RIG' }) {
  // Refs for animated parts
  const groupRef = useRef()
  const fanRef = useRef()
  const warningLightRef = useRef()
  const heatCoreRef = useRef()
  const sparklesRef = useRef()

  // Store base position for shake calculations
  const basePosition = useMemo(() => [...position], [position])
```

**Props:**
- `rigId`: 'A', 'B', or 'C' (which machine)
- `position`: [x, y, z] in 3D space
- `label`: Display name above rig

**Refs:** Access DOM/3D objects
```jsx
const fanRef = useRef()

// Later in JSX:
<mesh ref={fanRef}>...</mesh>

// In useFrame:
fanRef.current.rotation.y += 0.1  // Direct manipulation
```

**`useMemo()`**: Cache computed value
```jsx
const basePosition = useMemo(() => [...position], [position])
```
- Computes once when `position` changes
- `[...position]`: Copy array (don't modify prop)
- Stored for shake reset

### 5.2 Animation Loop

**Lines 35-92 (useFrame hook):**
```jsx
useFrame((state, delta) => {
  const data = getTransientState().rigs[rigId]
  if (!data || !groupRef.current) return

  // === RPM → Fan Rotation ===
  if (fanRef.current) {
    const rotationSpeed = (data.rpm / 5000) * 10
    fanRef.current.rotation.y += rotationSpeed * delta
  }

  // === Temperature → Emissive Color ===
  if (heatCoreRef.current) {
    const tempNormalized = Math.max(0, Math.min(1, (data.temperature - 60) / 40))

    if (tempNormalized < 0.5) {
      // Cold to warm: black → red
      tempColor.setRGB(tempNormalized * 2, 0, 0)
    } else {
      // Warm to hot: red → orange
      tempColor.setRGB(1, (tempNormalized - 0.5) * 1.0, 0)
    }

    heatCoreRef.current.material.emissive = tempColor
    heatCoreRef.current.material.emissiveIntensity = tempNormalized * 5
  }

  // === Vibration → Shake ===
  if (groupRef.current && data.vibration > 2) {
    const shakeIntensity = Math.min((data.vibration - 2) / 8, 1) * 0.05
    groupRef.current.position.x = basePosition[0] + (Math.random() - 0.5) * shakeIntensity
    groupRef.current.position.z = basePosition[2] + (Math.random() - 0.5) * shakeIntensity
  } else if (groupRef.current) {
    groupRef.current.position.x = basePosition[0]
    groupRef.current.position.z = basePosition[2]
  }

  // === Anomaly → Warning Light ===
  if (warningLightRef.current) {
    const hasAnomaly = data.anomalyScore > 0.5
    warningLightRef.current.visible = hasAnomaly

    if (hasAnomaly) {
      const pulse = Math.sin(state.clock.elapsedTime * 15) * 0.5 + 0.5
      warningLightRef.current.material.emissiveIntensity = pulse * 4 + 1
    }
  }

  // === Sparkles for anomalies ===
  if (sparklesRef.current) {
    sparklesRef.current.visible = data.anomalyScore > 0.3
  }
})
```

**useFrame Explained:**

**`useFrame((state, delta) => { ... })`**
- Runs every frame (60 FPS)
- `state`: Three.js state (clock, camera, scene)
- `delta`: Time since last frame (seconds)

**RPM → Rotation:**
```jsx
const rotationSpeed = (data.rpm / 5000) * 10
fanRef.current.rotation.y += rotationSpeed * delta
```
- Normalize RPM: `rpm / 5000` = 0.0 to 1.0
- Scale to rotation speed: `× 10` = 0 to 10 rad/s
- Apply per frame: `× delta` (frame-rate independent)

**Example:**
```
RPM = 2500 (mid-range)
Normalized = 2500 / 5000 = 0.5
Speed = 0.5 × 10 = 5 rad/s

60 FPS (delta ≈ 0.0167):
  Per frame rotation: 5 × 0.0167 = 0.0835 radians
  Per second: 0.0835 × 60 = 5 radians ✓
```

**Temperature → Color:**
```jsx
const tempNormalized = (data.temperature - 60) / 40

if (tempNormalized < 0.5) {
  // 60-80°F: black → red
  tempColor.setRGB(tempNormalized * 2, 0, 0)
} else {
  // 80-100°F: red → orange
  tempColor.setRGB(1, (tempNormalized - 0.5) * 1.0, 0)
}
```

**Color mapping:**
```
60°F: tempNorm = 0.0 → RGB(0, 0, 0) = Black
70°F: tempNorm = 0.25 → RGB(0.5, 0, 0) = Dark red
80°F: tempNorm = 0.5 → RGB(1, 0, 0) = Red
90°F: tempNorm = 0.75 → RGB(1, 0.5, 0) = Orange
100°F: tempNorm = 1.0 → RGB(1, 1, 0) = Yellow-orange
```

**Emissive intensity:**
```jsx
heatCoreRef.current.material.emissiveIntensity = tempNormalized * 5
```
- Cool (60°F): intensity = 0 (no glow)
- Hot (100°F): intensity = 5 (bright glow with bloom)

**Vibration → Shake:**
```jsx
if (data.vibration > 2) {  // Threshold: 2 mm/s
  const shakeIntensity = Math.min((data.vibration - 2) / 8, 1) * 0.05
  groupRef.current.position.x = basePosition[0] + (Math.random() - 0.5) * shakeIntensity
  groupRef.current.position.z = basePosition[2] + (Math.random() - 0.5) * shakeIntensity
}
```

**Shake intensity calculation:**
```
Vibration = 2 mm/s: intensity = 0 (no shake)
Vibration = 6 mm/s: intensity = (6-2)/8 = 0.5
Vibration = 10 mm/s: intensity = (10-2)/8 = 1.0 (max)

Shake range: 1.0 × 0.05 = 0.05 units = 5cm
Random offset: (Math.random() - 0.5) = -0.25 to +0.25
Final shake: basePosition ± 0.0125 to ± 0.025
```

**Warning Light Pulse:**
```jsx
const pulse = Math.sin(state.clock.elapsedTime * 15) * 0.5 + 0.5
warningLightRef.current.material.emissiveIntensity = pulse * 4 + 1
```

**Pulse calculation:**
```
clock.elapsedTime = seconds since start
× 15 = 15 cycles per second (15 Hz strobe)

sin(x):
  Ranges: -1 to +1
  × 0.5: -0.5 to +0.5
  + 0.5: 0 to 1 (always positive)

intensity = pulse × 4 + 1:
  Min: 0 × 4 + 1 = 1 (dim)
  Max: 1 × 4 + 1 = 5 (bright)
  
Result: Pulsing between 1 and 5 intensity
```

---

## 6. ANIMATION AND DATA BINDING

### 6.1 Data Flow Summary

```
1. Consumer detects anomaly
     ↓
2. POST /api/internal/telemetry-update
     ↓
3. Flask updates telemetry_cache
     ↓
4. Background thread emits 'rig_telemetry' (10 Hz)
     ↓
5. useSocket hook receives event
     ↓
6. updateTransientRig() mutates state
     ↓
7. useFrame() reads state (60 FPS)
     ↓
8. Apply to 3D objects (rotation, color, shake)
     ↓
9. Three.js renders frame
     ↓
10. User sees animated 3D rig
```

### 6.2 Performance Characteristics

**Update Frequencies:**
- WebSocket: 10 Hz (100ms interval)
- useFrame: 60 FPS (16.67ms interval)
- React re-renders: ~1 Hz (only for UI state)

**Why This Works:**
- Transient updates: Fast (no React overhead)
- useFrame reads: 60 FPS (smooth animation)
- WebSocket provides data: 10 Hz (adequate)
- Interpolation: useFrame fills gaps between socket updates

---

## 7. PERFORMANCE OPTIMIZATION

### 7.1 Techniques Used

**1. Transient State**
```jsx
// ❌ Bad (triggers 10 re-renders/sec)
const [rpm, setRPM] = useState(0)
socket.on('data', (d) => setRPM(d.rpm))

// ✅ Good (zero re-renders)
updateTransientRig('A', { rpm: d.rpm })
useFrame(() => {
  const rpm = getTransientState().rigs.A.rpm
})
```

**2. useRef for 3D Objects**
```jsx
const meshRef = useRef()

// Direct manipulation (no React diffing)
meshRef.current.rotation.y += 0.1
```

**3. useMemo for Static Values**
```jsx
const tempColor = useMemo(() => new THREE.Color(), [])
// Created once, reused every frame
```

**4. useCallback for Event Handlers**
```jsx
const handleTelemetry = useCallback((data) => { ... }, [])
// Function created once, not recreated each render
```

**5. Lazy Imports**
```jsx
<Suspense fallback={<Loading />}>
  <FactoryScene />  // Loads async
</Suspense>
```

---

## 🎓 SUMMARY

You now understand the 3D frontend:

✅ **React Three Fiber**: Declarative 3D with React  
✅ **WebSocket Integration**: Real-time data streaming  
✅ **Transient State**: Performance optimization pattern  
✅ **RigModel**: Sensor-to-3D data binding  
✅ **Animation Loop**: useFrame for smooth motion  
✅ **Visual Mapping**: RPM→rotation, temp→color, vibration→shake  

**Next Document:** [07-HOW-TO-GUIDES.md](07-HOW-TO-GUIDES.md)
- Practical tutorials
- Setup instructions
- Troubleshooting

---

*Continue to Document 07: How-To Guides →*
