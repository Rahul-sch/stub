import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

/**
 * Stacks of finished product crates scattered around the factory.
 *
 * Props:
 * - positions: Array of [x, y, z] positions for crate stacks
 * - maxHeight: Maximum stack height in crates
 */
export function CrateStacks({ positions = [], maxHeight = 4 }) {
  return (
    <group>
      {positions.map((pos, i) => (
        <CrateStack
          key={i}
          position={pos}
          height={Math.floor(Math.random() * maxHeight) + 1}
          rotation={Math.random() * 0.1 - 0.05}
        />
      ))}
    </group>
  )
}

/**
 * Single stack of crates.
 */
function CrateStack({ position = [0, 0, 0], height = 3, rotation = 0 }) {
  const groupRef = useRef()

  // Generate random crate variations
  const crates = useMemo(() => {
    return Array.from({ length: height }).map((_, i) => ({
      offset: [(Math.random() - 0.5) * 0.1, 0, (Math.random() - 0.5) * 0.1],
      rotation: (Math.random() - 0.5) * 0.05,
      color: Math.random() > 0.5 ? '#5a4530' : '#4a3520'
    }))
  }, [height])

  return (
    <group ref={groupRef} position={position} rotation={[0, rotation, 0]}>
      {crates.map((crate, i) => (
        <group key={i} position={[crate.offset[0], i * 1.1 + 0.5, crate.offset[2]]} rotation={[0, crate.rotation, 0]}>
          {/* Crate body */}
          <mesh castShadow receiveShadow>
            <boxGeometry args={[1.5, 1, 1.2]} />
            <meshStandardMaterial
              color={crate.color}
              roughness={0.9}
              metalness={0.05}
            />
          </mesh>

          {/* Crate slats (visual detail) */}
          {[-0.6, -0.3, 0, 0.3, 0.6].map((x, j) => (
            <mesh key={j} position={[x, 0, 0.61]}>
              <boxGeometry args={[0.08, 0.9, 0.02]} />
              <meshStandardMaterial color="#3a2510" roughness={0.95} />
            </mesh>
          ))}

          {/* Side handles */}
          <mesh position={[0.76, 0, 0]}>
            <boxGeometry args={[0.02, 0.3, 0.5]} />
            <meshStandardMaterial color="#3a2510" roughness={0.9} />
          </mesh>
          <mesh position={[-0.76, 0, 0]}>
            <boxGeometry args={[0.02, 0.3, 0.5]} />
            <meshStandardMaterial color="#3a2510" roughness={0.9} />
          </mesh>

          {/* Bottles inside (visible from top) */}
          {i === height - 1 && (
            <BottlesInCrate />
          )}
        </group>
      ))}
    </group>
  )
}

/**
 * Bottles visible inside the top crate.
 */
function BottlesInCrate() {
  const bottles = useMemo(() => {
    const result = []
    for (let x = 0; x < 3; x++) {
      for (let z = 0; z < 2; z++) {
        result.push({
          position: [(x - 1) * 0.4, 0.6, (z - 0.5) * 0.4],
          rotation: (Math.random() - 0.5) * 0.1
        })
      }
    }
    return result
  }, [])

  return (
    <group>
      {bottles.map((bottle, i) => (
        <mesh key={i} position={bottle.position} rotation={[0, bottle.rotation, 0]}>
          <cylinderGeometry args={[0.1, 0.12, 0.5, 6]} />
          <meshStandardMaterial color="#aa0000" roughness={0.3} metalness={0.1} />
        </mesh>
      ))}
    </group>
  )
}

/**
 * Pallet base for crate stacks.
 */
export function Pallet({ position = [0, 0, 0] }) {
  return (
    <group position={position}>
      {/* Top boards */}
      {[-0.6, -0.3, 0, 0.3, 0.6].map((z, i) => (
        <mesh key={i} position={[0, 0.1, z]}>
          <boxGeometry args={[1.6, 0.05, 0.15]} />
          <meshStandardMaterial color="#6a5540" roughness={0.95} metalness={0.05} />
        </mesh>
      ))}

      {/* Support blocks */}
      {[-0.5, 0, 0.5].map((x, i) => (
        <mesh key={i} position={[x, 0.025, 0]}>
          <boxGeometry args={[0.2, 0.05, 1.4]} />
          <meshStandardMaterial color="#5a4530" roughness={0.95} />
        </mesh>
      ))}

      {/* Bottom boards */}
      {[-0.5, 0.5].map((z, i) => (
        <mesh key={i} position={[0, -0.025, z]}>
          <boxGeometry args={[1.6, 0.05, 0.12]} />
          <meshStandardMaterial color="#6a5540" roughness={0.95} />
        </mesh>
      ))}
    </group>
  )
}

/**
 * Forklift for visual interest.
 */
export function Forklift({ position = [0, 0, 0], rotation = 0 }) {
  return (
    <group position={position} rotation={[0, rotation, 0]}>
      {/* Body */}
      <mesh position={[0, 0.8, 0]} castShadow>
        <boxGeometry args={[1.5, 1.2, 2.5]} />
        <meshStandardMaterial color="#ffaa00" roughness={0.6} metalness={0.3} />
      </mesh>

      {/* Cabin */}
      <mesh position={[0, 1.8, -0.3]}>
        <boxGeometry args={[1.3, 1.2, 1.5]} />
        <meshStandardMaterial color="#333333" roughness={0.5} metalness={0.4} />
      </mesh>

      {/* Mast */}
      <mesh position={[0, 1.5, 1.5]}>
        <boxGeometry args={[0.15, 3, 0.15]} />
        <meshStandardMaterial color="#555555" metalness={0.8} roughness={0.3} />
      </mesh>
      <mesh position={[0.4, 1.5, 1.5]}>
        <boxGeometry args={[0.15, 3, 0.15]} />
        <meshStandardMaterial color="#555555" metalness={0.8} roughness={0.3} />
      </mesh>
      <mesh position={[-0.4, 1.5, 1.5]}>
        <boxGeometry args={[0.15, 3, 0.15]} />
        <meshStandardMaterial color="#555555" metalness={0.8} roughness={0.3} />
      </mesh>

      {/* Forks */}
      <mesh position={[0.3, 0.3, 2]}>
        <boxGeometry args={[0.15, 0.1, 1.5]} />
        <meshStandardMaterial color="#444444" metalness={0.8} roughness={0.3} />
      </mesh>
      <mesh position={[-0.3, 0.3, 2]}>
        <boxGeometry args={[0.15, 0.1, 1.5]} />
        <meshStandardMaterial color="#444444" metalness={0.8} roughness={0.3} />
      </mesh>

      {/* Wheels */}
      {[
        [0.6, 0.25, 0.8],
        [-0.6, 0.25, 0.8],
        [0.6, 0.25, -0.8],
        [-0.6, 0.25, -0.8]
      ].map((pos, i) => (
        <mesh key={i} position={pos} rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[0.25, 0.25, 0.2, 16]} />
          <meshStandardMaterial color="#222222" roughness={0.9} />
        </mesh>
      ))}

      {/* Warning light */}
      <mesh position={[0, 2.5, -0.3]}>
        <sphereGeometry args={[0.15, 8, 8]} />
        <meshStandardMaterial
          color="#ff6600"
          emissive="#ff6600"
          emissiveIntensity={0.5}
        />
      </mesh>
    </group>
  )
}

export default CrateStacks
