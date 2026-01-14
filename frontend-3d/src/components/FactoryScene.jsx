import { useSensorStore } from '../store/useSensorStore'
import { Environment } from './Environment'
import { Player } from './Player'
import { RigModel } from './RigModel'
import { InteractionSystem } from './InteractionSystem'
import { KetchupFactoryScene } from './KetchupFactoryScene'

/**
 * Factory floor layout configuration for Rig Alpha.
 *
 * Positions are in world units (meters).
 * Matches machine_id values from database: A, B, C
 */
const RIG_LAYOUT = [
  {
    id: 'A',
    position: [-20, 0, 0],
    label: 'RIG ALPHA',
    color: '#00ffff'
  },
  {
    id: 'B',
    position: [0, 0, 0],
    label: 'RIG BETA',
    color: '#00ff41'
  },
  {
    id: 'C',
    position: [20, 0, 0],
    label: 'RIG GAMMA',
    color: '#ff6600'
  }
]

/**
 * Main factory scene composition with view mode switching.
 *
 * Modes:
 * - 'rig': Original Rig Alpha industrial scene (3 rigs)
 * - 'ketchup': Ketchup Factory scene (25 production lines)
 *
 * Both scenes share the same player controller and HUD.
 */
export function FactoryScene() {
  const viewMode = useSensorStore((s) => s.viewMode)

  // Render Ketchup Factory when in ketchup mode
  if (viewMode === 'ketchup') {
    return <KetchupFactoryScene />
  }

  // Default: Rig Alpha industrial scene
  return <RigAlphaScene />
}

/**
 * Original Rig Alpha industrial scene.
 *
 * Contains:
 * - Environment (lights, floor, fog, HDRI)
 * - Player controller
 * - Three industrial rigs with data binding
 * - Interaction system for rig inspection
 */
function RigAlphaScene() {
  return (
    <>
      {/* Environment setup */}
      <Environment />

      {/* First-person player - starts closer to rigs for visibility */}
      <Player startPosition={[0, 2, 15]} />

      {/* Industrial rigs - one for each machine_id in database */}
      {RIG_LAYOUT.map((rig) => (
        <RigModel
          key={rig.id}
          rigId={rig.id}
          position={rig.position}
          label={rig.label}
        />
      ))}

      {/* Interaction system (raycasting for rig selection) */}
      <InteractionSystem rigs={RIG_LAYOUT} />

      {/* Decorative elements */}
      <FactoryDecorations />
    </>
  )
}

/**
 * Additional factory decorations and props
 */
function FactoryDecorations() {
  return (
    <>
      {/* Support pillars */}
      {[-30, 30].map((x) =>
        [-20, 20].map((z) => (
          <Pillar key={`${x}-${z}`} position={[x, 0, z]} />
        ))
      )}

      {/* Overhead pipes */}
      <OverheadPipes />

      {/* Hazard markers */}
      <HazardZones />
    </>
  )
}

/**
 * Factory support pillar
 */
function Pillar({ position }) {
  return (
    <mesh position={[position[0], 6, position[2]]} castShadow>
      <cylinderGeometry args={[0.4, 0.5, 12, 8]} />
      <meshStandardMaterial
        color="#1a1a1a"
        metalness={0.7}
        roughness={0.4}
      />
    </mesh>
  )
}

/**
 * Overhead pipe system
 */
function OverheadPipes() {
  return (
    <group position={[0, 10, 0]}>
      {/* Main horizontal pipe */}
      <mesh rotation={[0, 0, Math.PI / 2]} castShadow>
        <cylinderGeometry args={[0.3, 0.3, 60, 8]} />
        <meshStandardMaterial
          color="#2a2a2a"
          metalness={0.85}
          roughness={0.3}
        />
      </mesh>

      {/* Cross pipes */}
      {[-20, 0, 20].map((x) => (
        <mesh key={x} position={[x, 0, 0]} rotation={[Math.PI / 2, 0, 0]} castShadow>
          <cylinderGeometry args={[0.2, 0.2, 30, 8]} />
          <meshStandardMaterial
            color="#2a2a2a"
            metalness={0.85}
            roughness={0.3}
          />
        </mesh>
      ))}
    </group>
  )
}

/**
 * Hazard zone floor markings
 */
function HazardZones() {
  return (
    <>
      {[-20, 0, 20].map((x) => (
        <mesh
          key={x}
          position={[x, 0.02, 0]}
          rotation={[-Math.PI / 2, 0, 0]}
        >
          <ringGeometry args={[4, 4.3, 32]} />
          <meshBasicMaterial
            color="#ff6600"
            transparent
            opacity={0.3}
          />
        </mesh>
      ))}
    </>
  )
}

export default FactoryScene
