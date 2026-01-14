import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import { Text, Billboard, Sparkles } from '@react-three/drei'
import * as THREE from 'three'
import { getTransientState } from '../store/useSensorStore'

/**
 * Industrial Rig 3D Model with real-time sensor data binding.
 *
 * Visual mappings from sensor_readings table:
 * - rpm → fan rotation speed
 * - temperature → emissive color (black→red→orange)
 * - vibration → position shake
 * - anomalyScore → warning light + particles
 *
 * @param {string} rigId - Machine identifier (A, B, or C)
 * @param {Array} position - [x, y, z] world position
 * @param {string} label - Display name (e.g., "RIG ALPHA")
 */
export function RigModel({ rigId, position = [0, 0, 0], label = 'RIG' }) {
  // Refs for animated parts
  const groupRef = useRef()
  const fanRef = useRef()
  const warningLightRef = useRef()
  const heatCoreRef = useRef()
  const sparklesRef = useRef()

  // Store base position for shake calculations
  const basePosition = useMemo(() => [...position], [position])

  // Reusable color object to avoid allocations
  const tempColor = useMemo(() => new THREE.Color(), [])

  // Animation loop - runs every frame
  useFrame((state, delta) => {
    const data = getTransientState().rigs[rigId]
    if (!data || !groupRef.current) return

    // === RPM → Fan Rotation ===
    // Map RPM (0-5000) to rotation speed (0-10 rad/s)
    if (fanRef.current) {
      const rotationSpeed = (data.rpm / 5000) * 10
      fanRef.current.rotation.y += rotationSpeed * delta
    }

    // === Temperature → Emissive Color ===
    // Map temp (60-100°F) to color gradient: black → red → orange (bloom)
    if (heatCoreRef.current) {
      const tempNormalized = Math.max(0, Math.min(1, (data.temperature - 60) / 40))

      if (tempNormalized < 0.5) {
        // Cold to warm: black (0,0,0) → red (1,0,0)
        tempColor.setRGB(tempNormalized * 2, 0, 0)
      } else {
        // Warm to hot: red (1,0,0) → orange (1,0.5,0)
        tempColor.setRGB(1, (tempNormalized - 0.5) * 1.0, 0)
      }

      heatCoreRef.current.material.emissive = tempColor
      // Emissive intensity ramps up for bloom effect
      heatCoreRef.current.material.emissiveIntensity = tempNormalized * 5
    }

    // === Vibration → Position Shake ===
    // Threshold: 2 mm/s, max shake at 10 mm/s
    if (groupRef.current && data.vibration > 2) {
      const shakeIntensity = Math.min((data.vibration - 2) / 8, 1) * 0.05
      groupRef.current.position.x = basePosition[0] + (Math.random() - 0.5) * shakeIntensity
      groupRef.current.position.z = basePosition[2] + (Math.random() - 0.5) * shakeIntensity
    } else if (groupRef.current) {
      // Reset to base position when vibration is low
      groupRef.current.position.x = basePosition[0]
      groupRef.current.position.z = basePosition[2]
    }

    // === Anomaly → Warning Light ===
    if (warningLightRef.current) {
      const hasAnomaly = data.anomalyScore > 0.5
      warningLightRef.current.visible = hasAnomaly

      if (hasAnomaly) {
        // Pulsing strobe effect
        const pulse = Math.sin(state.clock.elapsedTime * 15) * 0.5 + 0.5
        warningLightRef.current.material.emissiveIntensity = pulse * 4 + 1
      }
    }

    // === Anomaly → Sparkle Particles ===
    if (sparklesRef.current) {
      sparklesRef.current.visible = data.anomalyScore > 0.3
    }
  })

  return (
    <group ref={groupRef} position={position}>
      {/* === BASE PLATFORM === */}
      <mesh position={[0, 0.25, 0]} castShadow receiveShadow>
        <boxGeometry args={[5, 0.5, 5]} />
        <meshStandardMaterial
          color="#1a1a1a"
          metalness={0.9}
          roughness={0.3}
        />
      </mesh>

      {/* === MAIN HOUSING === */}
      <mesh position={[0, 2, 0]} castShadow receiveShadow>
        <boxGeometry args={[3.5, 3, 3.5]} />
        <meshStandardMaterial
          color="#222222"
          metalness={0.8}
          roughness={0.4}
        />
      </mesh>

      {/* === HEAT CORE (Emissive) === */}
      <mesh
        ref={heatCoreRef}
        position={[0, 2, 0]}
      >
        <cylinderGeometry args={[1, 1, 2.5, 16]} />
        <meshStandardMaterial
          color="#111111"
          emissive="#000000"
          emissiveIntensity={0}
          metalness={0.5}
          roughness={0.5}
          toneMapped={false} // Allow bloom to blow out
        />
      </mesh>

      {/* === ROTATING FAN/TURBINE === */}
      <group ref={fanRef} position={[0, 4.5, 0]}>
        {/* Fan hub */}
        <mesh castShadow>
          <cylinderGeometry args={[0.3, 0.3, 0.4, 8]} />
          <meshStandardMaterial color="#333" metalness={0.9} roughness={0.2} />
        </mesh>

        {/* Fan blades */}
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <mesh
            key={i}
            rotation={[Math.PI / 8, (Math.PI / 3) * i, 0]}
            position={[
              Math.sin((Math.PI / 3) * i) * 0.8,
              0,
              Math.cos((Math.PI / 3) * i) * 0.8
            ]}
            castShadow
          >
            <boxGeometry args={[0.6, 0.08, 0.25]} />
            <meshStandardMaterial
              color="#444"
              metalness={0.95}
              roughness={0.15}
            />
          </mesh>
        ))}
      </group>

      {/* === TOP EXHAUST STACK === */}
      <mesh position={[0, 5.5, 0]} castShadow>
        <cylinderGeometry args={[0.4, 0.6, 1.5, 8]} />
        <meshStandardMaterial
          color="#1a1a1a"
          metalness={0.7}
          roughness={0.5}
        />
      </mesh>

      {/* === WARNING LIGHT === */}
      <mesh
        ref={warningLightRef}
        position={[0, 6.5, 0]}
        visible={false}
      >
        <sphereGeometry args={[0.25, 16, 16]} />
        <meshStandardMaterial
          color="#ff0000"
          emissive="#ff0000"
          emissiveIntensity={2}
          toneMapped={false}
        />
      </mesh>

      {/* === ANOMALY SPARKLES === */}
      <Sparkles
        ref={sparklesRef}
        count={50}
        scale={[4, 6, 4]}
        position={[0, 3, 0]}
        size={3}
        speed={0.8}
        color="#ff4400"
        visible={false}
      />

      {/* === SIDE PIPES === */}
      <SidePipes />

      {/* === CONTROL PANEL === */}
      <mesh position={[1.8, 1.5, 0]} rotation={[0, Math.PI / 2, 0]} castShadow>
        <boxGeometry args={[1, 1.5, 0.2]} />
        <meshStandardMaterial color="#0a0a0a" metalness={0.5} roughness={0.6} />
      </mesh>

      {/* Control panel screen glow */}
      <mesh position={[1.9, 1.5, 0]} rotation={[0, Math.PI / 2, 0]}>
        <planeGeometry args={[0.8, 0.5]} />
        <meshStandardMaterial
          color="#00ffff"
          emissive="#00ffff"
          emissiveIntensity={0.5}
          toneMapped={false}
        />
      </mesh>

      {/* === RIG LABEL === */}
      <Billboard position={[0, 7.5, 0]} follow={true}>
        <Text
          fontSize={0.6}
          color="#00ffff"
          anchorX="center"
          anchorY="middle"
          outlineWidth={0.03}
          outlineColor="#000000"
        >
          {label}
        </Text>
      </Billboard>

      {/* === RIG ID (smaller) === */}
      <Billboard position={[0, 6.8, 0]} follow={true}>
        <Text
          fontSize={0.3}
          color="#666666"
          anchorX="center"
          anchorY="middle"
        >
          ID: {rigId}
        </Text>
      </Billboard>
    </group>
  )
}

/**
 * Decorative side pipes
 */
function SidePipes() {
  return (
    <>
      {/* Left pipe */}
      <mesh position={[-2, 1.5, 0]} rotation={[0, 0, Math.PI / 2]} castShadow>
        <cylinderGeometry args={[0.15, 0.15, 2, 8]} />
        <meshStandardMaterial color="#333" metalness={0.9} roughness={0.3} />
      </mesh>

      {/* Right pipe */}
      <mesh position={[2, 2, 0]} rotation={[0, 0, Math.PI / 2]} castShadow>
        <cylinderGeometry args={[0.12, 0.12, 2, 8]} />
        <meshStandardMaterial color="#333" metalness={0.9} roughness={0.3} />
      </mesh>

      {/* Back pipes */}
      <mesh position={[0, 1, -2]} rotation={[Math.PI / 2, 0, 0]} castShadow>
        <cylinderGeometry args={[0.2, 0.2, 1.5, 8]} />
        <meshStandardMaterial color="#2a2a2a" metalness={0.85} roughness={0.35} />
      </mesh>
    </>
  )
}

export default RigModel
