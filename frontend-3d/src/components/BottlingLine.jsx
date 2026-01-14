import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { RoundedBox } from '@react-three/drei'
import { getKetchupTransientState } from '../store/useSensorStore'
import { InstancedBottles } from './InstancedBottles'

/**
 * Complete ketchup bottling production line.
 *
 * Layout (left to right):
 * [TANK] → [FILL STATION] → [CONVEYOR] → [CAP STATION] → [SCANNER] → [OUTPUT]
 *
 * Props:
 * - lineId: Production line ID (L01-L25)
 * - position: [x, y, z] world position
 * - label: Display label
 *
 * Data bindings:
 * - fill_level → Fill robot arm animation, drip effect
 * - viscosity → Tank color intensity
 * - sauce_temp → Steam particles, tank glow
 * - cap_torque → Cap robot shake on fault
 * - bottle_flow_rate → Conveyor speed, bottle spawn rate
 * - label_alignment → Bottle tilt angle
 * - anomaly_score → Scanner flash, warning strobe
 */
export function BottlingLine({ lineId, position = [0, 0, 0], label = '' }) {
  const groupRef = useRef()

  // Refs for animated parts
  const fillArmRef = useRef()
  const capArmRef = useRef()
  const scannerRef = useRef()
  const conveyorBeltRef = useRef()
  const warningLightRef = useRef()
  const tankGlowRef = useRef()

  // Conveyor texture with UV scrolling
  const conveyorTexture = useMemo(() => {
    const canvas = document.createElement('canvas')
    canvas.width = 256
    canvas.height = 64
    const ctx = canvas.getContext('2d')

    // Conveyor belt pattern
    ctx.fillStyle = '#333333'
    ctx.fillRect(0, 0, 256, 64)

    // Ridges
    ctx.fillStyle = '#444444'
    for (let i = 0; i < 16; i++) {
      ctx.fillRect(i * 16, 0, 8, 64)
    }

    const texture = new THREE.CanvasTexture(canvas)
    texture.wrapS = THREE.RepeatWrapping
    texture.wrapT = THREE.RepeatWrapping
    texture.repeat.set(4, 1)
    return texture
  }, [])

  // Animation loop
  useFrame((state, delta) => {
    const data = getKetchupTransientState().lines[lineId]
    if (!data) return

    const {
      fill_level,
      viscosity,
      sauce_temp,
      cap_torque,
      bottle_flow_rate,
      label_alignment,
      anomaly_score,
      anomaly_type
    } = data

    // 1. CONVEYOR BELT ANIMATION
    if (conveyorBeltRef.current?.material?.map) {
      const scrollSpeed = (bottle_flow_rate / 150) * delta * 0.5
      conveyorBeltRef.current.material.map.offset.x += scrollSpeed
    }

    // 2. FILL ARM ANIMATION (bobbing based on flow rate)
    if (fillArmRef.current) {
      const cycleSpeed = bottle_flow_rate / 100
      fillArmRef.current.position.y = 2.5 + Math.sin(state.clock.elapsedTime * cycleSpeed * 3) * 0.2
    }

    // 3. CAP ARM ANIMATION (shake on torque fault)
    if (capArmRef.current) {
      const torqueDelta = Math.abs(cap_torque - 2.5)
      if (torqueDelta > 0.7) {
        // Shake on fault
        capArmRef.current.position.x += (Math.random() - 0.5) * torqueDelta * 0.015
        capArmRef.current.position.z += (Math.random() - 0.5) * torqueDelta * 0.015
      }
      // Bobbing animation
      capArmRef.current.position.y = 2.5 + Math.sin(state.clock.elapsedTime * 2 + 1) * 0.15
    }

    // 4. SCANNER GLOW (anomaly detection)
    if (scannerRef.current) {
      const hasAnomaly = anomaly_score > 0.5
      if (hasAnomaly) {
        // Red pulsing glow on anomaly
        const pulse = 0.5 + Math.sin(state.clock.elapsedTime * 10) * 0.5
        scannerRef.current.material.emissive.setRGB(1, 0, 0)
        scannerRef.current.material.emissiveIntensity = 1 + pulse
      } else {
        // Green idle glow
        scannerRef.current.material.emissive.setRGB(0, 1, 0)
        scannerRef.current.material.emissiveIntensity = 0.3
      }
    }

    // 5. WARNING LIGHT (strobe on anomaly)
    if (warningLightRef.current) {
      if (anomaly_score > 0.5) {
        const flash = Math.sin(state.clock.elapsedTime * 15) > 0
        warningLightRef.current.visible = flash
        warningLightRef.current.material.emissiveIntensity = flash ? 3 : 0
      } else {
        warningLightRef.current.visible = false
      }
    }

    // 6. TANK GLOW (high temperature)
    if (tankGlowRef.current) {
      if (sauce_temp > 175) {
        const intensity = (sauce_temp - 175) / 10
        tankGlowRef.current.material.emissive.setRGB(1, 0.3, 0)
        tankGlowRef.current.material.emissiveIntensity = intensity
      } else {
        tankGlowRef.current.material.emissiveIntensity = 0
      }
    }
  })

  return (
    <group ref={groupRef} position={position}>

      {/* KETCHUP TANK (left side) */}
      <group position={[-6, 0, 0]}>
        <mesh ref={tankGlowRef} position={[0, 2, 0]} castShadow>
          <cylinderGeometry args={[1.2, 1.4, 4, 16]} />
          <meshStandardMaterial
            color="#880000"
            roughness={0.3}
            metalness={0.7}
            emissive="#ff0000"
            emissiveIntensity={0}
          />
        </mesh>
        {/* Tank top */}
        <mesh position={[0, 4.2, 0]}>
          <cylinderGeometry args={[1.2, 1.2, 0.3, 16]} />
          <meshStandardMaterial color="#444444" metalness={0.8} roughness={0.2} />
        </mesh>
        {/* Pipe to fill station */}
        <mesh position={[2, 2.5, 0]} rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[0.15, 0.15, 2, 8]} />
          <meshStandardMaterial color="#666666" metalness={0.8} roughness={0.3} />
        </mesh>
      </group>

      {/* FILL STATION */}
      <group position={[-3, 0, 0]}>
        {/* Fill arm */}
        <mesh ref={fillArmRef} position={[0, 2.5, 0]}>
          <boxGeometry args={[0.3, 1.5, 0.3]} />
          <meshStandardMaterial color="#666666" metalness={0.7} roughness={0.3} />
        </mesh>
        {/* Nozzle */}
        <mesh position={[0, 1.5, 0]}>
          <coneGeometry args={[0.15, 0.4, 8]} />
          <meshStandardMaterial color="#444444" metalness={0.8} roughness={0.2} />
        </mesh>
        {/* Base */}
        <mesh position={[0, 0.3, 0]}>
          <boxGeometry args={[1.5, 0.6, 1.5]} />
          <meshStandardMaterial color="#333333" metalness={0.5} roughness={0.5} />
        </mesh>
      </group>

      {/* CONVEYOR BELT */}
      <group position={[0, 0, 0]}>
        {/* Belt surface */}
        <mesh ref={conveyorBeltRef} position={[0, 0.5, 0]} receiveShadow>
          <boxGeometry args={[10, 0.2, 1.5]} />
          <meshStandardMaterial
            map={conveyorTexture}
            color="#555555"
            roughness={0.8}
            metalness={0.2}
          />
        </mesh>
        {/* Side rails */}
        <mesh position={[0, 0.7, 0.8]}>
          <boxGeometry args={[10, 0.3, 0.1]} />
          <meshStandardMaterial color="#444444" metalness={0.6} roughness={0.4} />
        </mesh>
        <mesh position={[0, 0.7, -0.8]}>
          <boxGeometry args={[10, 0.3, 0.1]} />
          <meshStandardMaterial color="#444444" metalness={0.6} roughness={0.4} />
        </mesh>
        {/* Legs */}
        {[-4, -2, 0, 2, 4].map((x, i) => (
          <mesh key={i} position={[x, 0.2, 0]}>
            <boxGeometry args={[0.2, 0.4, 1.5]} />
            <meshStandardMaterial color="#333333" metalness={0.5} roughness={0.5} />
          </mesh>
        ))}
      </group>

      {/* INSTANCED BOTTLES ON CONVEYOR */}
      <InstancedBottles lineId={lineId} count={8} conveyorLength={10} />

      {/* CAP STATION */}
      <group position={[3, 0, 0]}>
        {/* Cap arm */}
        <mesh ref={capArmRef} position={[0, 2.5, 0]}>
          <boxGeometry args={[0.3, 1.2, 0.3]} />
          <meshStandardMaterial color="#666666" metalness={0.7} roughness={0.3} />
        </mesh>
        {/* Cap gripper */}
        <mesh position={[0, 1.6, 0]}>
          <cylinderGeometry args={[0.2, 0.25, 0.3, 8]} />
          <meshStandardMaterial color="#555555" metalness={0.8} roughness={0.2} />
        </mesh>
        {/* Base */}
        <mesh position={[0, 0.3, 0]}>
          <boxGeometry args={[1.2, 0.6, 1.2]} />
          <meshStandardMaterial color="#333333" metalness={0.5} roughness={0.5} />
        </mesh>
      </group>

      {/* SCANNER STATION */}
      <group position={[5.5, 0, 0]}>
        {/* Scanner housing */}
        <mesh ref={scannerRef} position={[0, 1.8, 0]} castShadow>
          <RoundedBox args={[1, 0.8, 1.2]} radius={0.1}>
            <meshStandardMaterial
              color="#222222"
              metalness={0.6}
              roughness={0.4}
              emissive="#00ff00"
              emissiveIntensity={0.3}
            />
          </RoundedBox>
        </mesh>
        {/* Scanner beam area */}
        <mesh position={[0, 1, 0]} rotation={[0, 0, 0]}>
          <boxGeometry args={[0.1, 1, 1]} />
          <meshBasicMaterial color="#00ff00" transparent opacity={0.2} />
        </mesh>
        {/* Base */}
        <mesh position={[0, 0.3, 0]}>
          <boxGeometry args={[1, 0.6, 1.2]} />
          <meshStandardMaterial color="#333333" metalness={0.5} roughness={0.5} />
        </mesh>
      </group>

      {/* WARNING LIGHT */}
      <mesh ref={warningLightRef} position={[0, 4, 1]} visible={false}>
        <sphereGeometry args={[0.3, 16, 16]} />
        <meshStandardMaterial
          color="#ff0000"
          emissive="#ff0000"
          emissiveIntensity={3}
        />
      </mesh>

      {/* OUTPUT/CRATE AREA (right side) */}
      <group position={[7, 0, 0]}>
        {/* Output crate */}
        <mesh position={[0, 0.5, 0]} castShadow>
          <boxGeometry args={[1.5, 1, 1.5]} />
          <meshStandardMaterial color="#4a3520" roughness={0.9} metalness={0.1} />
        </mesh>
      </group>

      {/* BASE PLATFORM */}
      <mesh position={[0, -0.1, 0]} receiveShadow>
        <boxGeometry args={[16, 0.2, 4]} />
        <meshStandardMaterial color="#1a1a1a" roughness={0.9} metalness={0.2} />
      </mesh>
    </group>
  )
}

export default BottlingLine
