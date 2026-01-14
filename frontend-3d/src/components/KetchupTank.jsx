import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

/**
 * Large ketchup storage tank for factory corners.
 *
 * Props:
 * - position: [x, y, z] world position
 * - label: Display label (e.g., "TANK A")
 * - fillPercent: 0-100 visual fill level indicator
 */
export function KetchupTank({ position = [0, 0, 0], label = 'STORAGE', fillPercent = 85 }) {
  const tankRef = useRef()
  const liquidRef = useRef()
  const bubbleRef = useRef()

  // Animate liquid surface
  useFrame((state, delta) => {
    if (liquidRef.current) {
      // Gentle wobble
      liquidRef.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.5) * 0.02
      liquidRef.current.position.y = 4 + Math.sin(state.clock.elapsedTime * 0.3) * 0.05
    }

    // Bubble animation
    if (bubbleRef.current) {
      const children = bubbleRef.current.children
      children.forEach((bubble, i) => {
        bubble.position.y += delta * 0.5
        if (bubble.position.y > 7) {
          bubble.position.y = 1
          bubble.position.x = (Math.random() - 0.5) * 1.5
          bubble.position.z = (Math.random() - 0.5) * 1.5
        }
      })
    }
  })

  const tankHeight = 10
  const tankRadius = 3
  const liquidHeight = (fillPercent / 100) * (tankHeight - 1)

  return (
    <group position={position}>
      {/* MAIN TANK BODY (transparent to show liquid) */}
      <mesh ref={tankRef} position={[0, tankHeight / 2, 0]} castShadow>
        <cylinderGeometry args={[tankRadius, tankRadius * 1.1, tankHeight, 24]} />
        <meshPhysicalMaterial
          color="#888888"
          metalness={0.9}
          roughness={0.1}
          transparent
          opacity={0.3}
          transmission={0.5}
          thickness={0.5}
        />
      </mesh>

      {/* LIQUID INSIDE */}
      <mesh ref={liquidRef} position={[0, liquidHeight / 2 + 0.5, 0]}>
        <cylinderGeometry args={[tankRadius * 0.95, tankRadius * 1.05, liquidHeight, 24]} />
        <meshStandardMaterial
          color="#990000"
          transparent
          opacity={0.85}
          roughness={0.4}
          metalness={0.1}
        />
      </mesh>

      {/* LIQUID SURFACE (top) */}
      <mesh position={[0, liquidHeight + 0.5, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[tankRadius * 0.95, 24]} />
        <meshStandardMaterial
          color="#bb0000"
          roughness={0.3}
          metalness={0.2}
        />
      </mesh>

      {/* BUBBLES (rising through liquid) */}
      <group ref={bubbleRef}>
        {Array.from({ length: 8 }).map((_, i) => (
          <mesh
            key={i}
            position={[
              (Math.random() - 0.5) * 2,
              Math.random() * liquidHeight + 1,
              (Math.random() - 0.5) * 2
            ]}
          >
            <sphereGeometry args={[0.1 + Math.random() * 0.1, 8, 8]} />
            <meshStandardMaterial
              color="#ff2222"
              transparent
              opacity={0.4}
            />
          </mesh>
        ))}
      </group>

      {/* TANK TOP CAP */}
      <mesh position={[0, tankHeight + 0.25, 0]}>
        <cylinderGeometry args={[tankRadius, tankRadius, 0.5, 24]} />
        <meshStandardMaterial color="#555555" metalness={0.8} roughness={0.2} />
      </mesh>

      {/* TANK BOTTOM BASE */}
      <mesh position={[0, 0.25, 0]}>
        <cylinderGeometry args={[tankRadius * 1.1, tankRadius * 1.2, 0.5, 24]} />
        <meshStandardMaterial color="#444444" metalness={0.8} roughness={0.2} />
      </mesh>

      {/* SUPPORT LEGS */}
      {[0, 1, 2, 3].map((i) => {
        const angle = (i * Math.PI * 2) / 4 + Math.PI / 4
        const x = Math.cos(angle) * tankRadius * 0.9
        const z = Math.sin(angle) * tankRadius * 0.9
        return (
          <mesh key={i} position={[x, -0.5, z]}>
            <cylinderGeometry args={[0.3, 0.4, 1, 8]} />
            <meshStandardMaterial color="#333333" metalness={0.7} roughness={0.3} />
          </mesh>
        )
      })}

      {/* PIPES */}
      {/* Input pipe (top) */}
      <mesh position={[tankRadius + 0.5, tankHeight - 1, 0]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.25, 0.25, 1, 8]} />
        <meshStandardMaterial color="#666666" metalness={0.8} roughness={0.3} />
      </mesh>

      {/* Output pipe (bottom) */}
      <mesh position={[tankRadius + 0.5, 1, 0]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.3, 0.3, 1, 8]} />
        <meshStandardMaterial color="#666666" metalness={0.8} roughness={0.3} />
      </mesh>

      {/* VALVE */}
      <mesh position={[tankRadius + 1, 1, 0]}>
        <boxGeometry args={[0.4, 0.6, 0.4]} />
        <meshStandardMaterial color="#ff4444" metalness={0.6} roughness={0.4} />
      </mesh>


      {/* FILL LEVEL INDICATOR (side gauge) */}
      <group position={[tankRadius + 0.3, tankHeight / 2, 0]}>
        {/* Gauge backing */}
        <mesh>
          <boxGeometry args={[0.2, tankHeight - 1, 0.3]} />
          <meshStandardMaterial color="#222222" metalness={0.5} roughness={0.5} />
        </mesh>
        {/* Gauge fill */}
        <mesh position={[0.05, -(tankHeight - 1) / 2 + liquidHeight / 2, 0]}>
          <boxGeometry args={[0.15, liquidHeight, 0.25]} />
          <meshStandardMaterial
            color="#ff0000"
            emissive="#ff0000"
            emissiveIntensity={0.3}
          />
        </mesh>
        {/* Gauge markings */}
        {[0, 25, 50, 75, 100].map((percent, i) => (
          <mesh
            key={i}
            position={[0.2, -(tankHeight - 1) / 2 + (percent / 100) * (tankHeight - 1), 0]}
          >
            <boxGeometry args={[0.1, 0.05, 0.1]} />
            <meshBasicMaterial color="#ffffff" />
          </mesh>
        ))}
      </group>

      {/* PLATFORM GRATING */}
      <mesh position={[0, -1, 0]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <ringGeometry args={[tankRadius * 0.5, tankRadius * 1.5, 24]} />
        <meshStandardMaterial
          color="#333333"
          metalness={0.7}
          roughness={0.5}
          side={THREE.DoubleSide}
        />
      </mesh>
    </group>
  )
}

export default KetchupTank
