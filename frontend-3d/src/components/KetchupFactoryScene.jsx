import { useMemo, useRef, useEffect } from 'react'
import { useThree, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

import { KetchupEnvironment } from './KetchupEnvironment'
import { BottlingLine } from './BottlingLine'
import { KetchupTank } from './KetchupTank'
import { CrateStacks, Forklift, Pallet } from './CrateStacks'
import { SauceParticles } from './SauceParticles'
import { useSensorStore, getKetchupTransientState } from '../store/useSensorStore'

/**
 * Ketchup Factory Scene - 25 Production Lines (5x5 Grid)
 *
 * Layout:
 * - 25 production lines arranged in 5 rows × 5 columns
 * - 4 large storage tanks in corners
 * - Crate stacks and forklifts for atmosphere
 * - Interactive click-to-select with camera fly-to
 */

// Generate 25 production line positions (5x5 grid)
const KETCHUP_LINES = Array.from({ length: 25 }, (_, i) => {
  const row = Math.floor(i / 5)
  const col = i % 5
  return {
    id: `L${String(i + 1).padStart(2, '0')}`,
    position: [(col - 2) * 30, 0, (row - 2) * 25],
    row,
    col,
    label: `LINE ${i + 1}`
  }
})

// Storage tank positions (corners)
const TANK_POSITIONS = [
  { position: [-80, 0, -60], label: 'TANK A', fill: 92 },
  { position: [80, 0, -60], label: 'TANK B', fill: 78 },
  { position: [-80, 0, 60], label: 'TANK C', fill: 85 },
  { position: [80, 0, 60], label: 'TANK D', fill: 95 }
]

// Crate stack positions (scattered around)
const CRATE_POSITIONS = [
  [-90, 0, -30], [-90, 0, 0], [-90, 0, 30],
  [90, 0, -30], [90, 0, 0], [90, 0, 30],
  [-50, 0, -70], [0, 0, -70], [50, 0, -70],
  [-50, 0, 70], [0, 0, 70], [50, 0, 70]
]

// Forklift positions
const FORKLIFT_POSITIONS = [
  { position: [-70, 0, -40], rotation: Math.PI / 4 },
  { position: [70, 0, 40], rotation: -Math.PI / 3 },
  { position: [-40, 0, 65], rotation: Math.PI / 2 }
]

export function KetchupFactoryScene() {
  const selectedLine = useSensorStore(s => s.selectedKetchupLine)
  const setSelectedLine = useSensorStore(s => s.setSelectedKetchupLine)

  return (
    <>
      {/* Environment (lighting, fog, floor, particles) */}
      <KetchupEnvironment />

      {/* 25 Production Lines */}
      {KETCHUP_LINES.map((line) => (
        <group key={line.id}>
          <BottlingLine
            lineId={line.id}
            position={line.position}
            label={line.label}
          />
          <SauceParticles lineId={line.id} position={line.position} />

          {/* Click hitbox for selection */}
          <LineClickArea
            lineId={line.id}
            position={line.position}
            selected={selectedLine === line.id}
            onSelect={() => setSelectedLine(line.id)}
          />
        </group>
      ))}

      {/* Storage Tanks (corners) */}
      {TANK_POSITIONS.map((tank, i) => (
        <KetchupTank
          key={i}
          position={tank.position}
          label={tank.label}
          fillPercent={tank.fill}
        />
      ))}

      {/* Crate Stacks */}
      <CrateStacks positions={CRATE_POSITIONS} maxHeight={4} />

      {/* Forklifts */}
      {FORKLIFT_POSITIONS.map((fork, i) => (
        <Forklift
          key={i}
          position={fork.position}
          rotation={fork.rotation}
        />
      ))}

      {/* Pallets scattered around */}
      {CRATE_POSITIONS.map((pos, i) => (
        <Pallet key={i} position={[pos[0], -0.1, pos[2]]} />
      ))}

      {/* Factory signage */}
      <FactorySignage />

      {/* Selection highlight effect */}
      {selectedLine && (
        <SelectionHighlight lineId={selectedLine} />
      )}

      {/* Camera controller for fly-to animation */}
      <CameraController
        selectedLine={selectedLine}
        lines={KETCHUP_LINES}
      />
    </>
  )
}

/**
 * Invisible click area for line selection.
 */
function LineClickArea({ lineId, position, selected, onSelect }) {
  const meshRef = useRef()

  useFrame((state) => {
    if (meshRef.current && selected) {
      // Pulse effect when selected
      const scale = 1 + Math.sin(state.clock.elapsedTime * 4) * 0.02
      meshRef.current.scale.setScalar(scale)
    }
  })

  return (
    <mesh
      ref={meshRef}
      position={[position[0], 2, position[2]]}
      onClick={(e) => {
        e.stopPropagation()
        onSelect()
      }}
      onPointerOver={() => document.body.style.cursor = 'pointer'}
      onPointerOut={() => document.body.style.cursor = 'auto'}
    >
      <boxGeometry args={[18, 5, 6]} />
      <meshBasicMaterial visible={false} />
    </mesh>
  )
}

/**
 * Visual highlight for selected production line.
 */
function SelectionHighlight({ lineId }) {
  const line = KETCHUP_LINES.find(l => l.id === lineId)
  if (!line) return null

  const ringRef = useRef()

  useFrame((state) => {
    if (ringRef.current) {
      ringRef.current.rotation.z = state.clock.elapsedTime * 0.5
    }
  })

  return (
    <group position={[line.position[0], 0.1, line.position[2]]}>
      {/* Ground ring */}
      <mesh ref={ringRef} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[9, 10, 32]} />
        <meshBasicMaterial color="#00ffff" transparent opacity={0.5} />
      </mesh>

      {/* Vertical beams */}
      {[0, Math.PI / 2, Math.PI, Math.PI * 1.5].map((angle, i) => {
        const x = Math.cos(angle) * 9.5
        const z = Math.sin(angle) * 9.5
        return (
          <mesh key={i} position={[x, 3, z]}>
            <cylinderGeometry args={[0.05, 0.05, 6, 8]} />
            <meshBasicMaterial color="#00ffff" transparent opacity={0.6} />
          </mesh>
        )
      })}

    </group>
  )
}

/**
 * Camera controller for smooth fly-to animations.
 */
function CameraController({ selectedLine, lines }) {
  const { camera } = useThree()
  const targetRef = useRef({
    position: new THREE.Vector3(0, 2, 80),
    lookAt: new THREE.Vector3(0, 0, 0)
  })
  const isAnimating = useRef(false)
  const clearSelection = useSensorStore(s => s.clearSelectedKetchupLine)

  useEffect(() => {
    if (selectedLine) {
      const line = lines.find(l => l.id === selectedLine)
      if (line) {
        // Calculate camera position: slightly above and behind the line
        targetRef.current.position.set(
          line.position[0] + 12,
          8,
          line.position[2] + 18
        )
        targetRef.current.lookAt.set(
          line.position[0],
          2,
          line.position[2]
        )
        isAnimating.current = true
      }
    } else {
      // Return to overview position
      targetRef.current.position.set(0, 40, 100)
      targetRef.current.lookAt.set(0, 0, 0)
      isAnimating.current = true
    }
  }, [selectedLine, lines])

  // Handle Escape key to clear selection
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.code === 'Escape' && selectedLine) {
        clearSelection()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [selectedLine, clearSelection])

  useFrame((state, delta) => {
    if (isAnimating.current) {
      // Smooth camera movement
      camera.position.lerp(targetRef.current.position, delta * 2)

      // Smooth look-at
      const currentLookAt = new THREE.Vector3()
      camera.getWorldDirection(currentLookAt)
      currentLookAt.multiplyScalar(10).add(camera.position)

      currentLookAt.lerp(targetRef.current.lookAt, delta * 2)
      camera.lookAt(currentLookAt)

      // Stop animating when close enough
      if (camera.position.distanceTo(targetRef.current.position) < 0.1) {
        isAnimating.current = false
      }
    }
  })

  return null
}

/**
 * Factory signage and branding (simplified - no Text).
 */
function FactorySignage() {
  return (
    <group>
      {/* Main factory sign */}
      <group position={[0, 20, -85]}>
        <mesh>
          <boxGeometry args={[60, 8, 0.5]} />
          <meshStandardMaterial color="#990000" metalness={0.6} roughness={0.4} />
        </mesh>
      </group>

      {/* Safety signs */}
      {[
        { pos: [-95, 8, -60] },
        { pos: [95, 8, 60] },
        { pos: [-95, 8, 60] }
      ].map((sign, i) => (
        <mesh key={i} position={sign.pos}>
          <boxGeometry args={[0.3, 4, 8]} />
          <meshStandardMaterial color="#ffcc00" />
        </mesh>
      ))}
    </group>
  )
}

export default KetchupFactoryScene
