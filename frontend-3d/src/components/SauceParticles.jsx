import { useRef, useMemo, useEffect } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { Sparkles, Cloud } from '@react-three/drei'
import { getKetchupTransientState } from '../store/useSensorStore'

/**
 * Particle effects for a single production line.
 *
 * Effects triggered by sensor data:
 * - Drip particles: fill_level > 98 (overfill)
 * - Steam particles: sauce_temp > 175 (high temp)
 * - Spark particles: cap_torque fault
 * - Alert particles: anomaly_score > 0.5
 */
export function SauceParticles({ lineId, position = [0, 0, 0] }) {
  const dripRef = useRef()
  const steamRef = useRef()
  const sparkRef = useRef()

  // Drip particles state
  const dripParticles = useRef([])
  const maxDrips = 20

  // Initialize drip particles
  useEffect(() => {
    dripParticles.current = Array.from({ length: maxDrips }).map(() => ({
      position: new THREE.Vector3(),
      velocity: new THREE.Vector3(),
      active: false,
      life: 0
    }))
  }, [])

  useFrame((state, delta) => {
    const data = getKetchupTransientState().lines[lineId]
    if (!data) return

    const { fill_level, sauce_temp, cap_torque, anomaly_score } = data

    // Update drip particles (overfill effect)
    if (fill_level > 98 && dripRef.current) {
      // Spawn new drips
      const spawnRate = (fill_level - 98) * 2 // More drips for higher overfill
      if (Math.random() < spawnRate * delta) {
        const inactiveParticle = dripParticles.current.find(p => !p.active)
        if (inactiveParticle) {
          inactiveParticle.active = true
          inactiveParticle.life = 1.5
          inactiveParticle.position.set(
            -3 + (Math.random() - 0.5) * 0.5, // Fill station X
            1.5,
            (Math.random() - 0.5) * 0.3
          )
          inactiveParticle.velocity.set(
            (Math.random() - 0.5) * 0.5,
            -2,
            (Math.random() - 0.5) * 0.5
          )
        }
      }

      // Update active drips
      const positions = dripRef.current.geometry.attributes.position
      let visibleCount = 0

      dripParticles.current.forEach((particle, i) => {
        if (particle.active) {
          particle.life -= delta
          particle.position.addScaledVector(particle.velocity, delta)
          particle.velocity.y -= 9.8 * delta // Gravity

          if (particle.life <= 0 || particle.position.y < 0) {
            particle.active = false
          } else {
            positions.setXYZ(visibleCount, particle.position.x, particle.position.y, particle.position.z)
            visibleCount++
          }
        }
      })

      // Hide unused particles
      for (let i = visibleCount; i < maxDrips; i++) {
        positions.setXYZ(i, 0, -100, 0)
      }

      positions.needsUpdate = true
    }
  })

  const data = getKetchupTransientState().lines[lineId] || {}

  return (
    <group position={position}>
      {/* DRIP PARTICLES (overfill) */}
      <points ref={dripRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={maxDrips}
            array={new Float32Array(maxDrips * 3)}
            itemSize={3}
          />
        </bufferGeometry>
        <pointsMaterial
          color="#880000"
          size={0.15}
          sizeAttenuation
          transparent
          opacity={0.8}
        />
      </points>

      {/* STEAM PARTICLES (high temp) */}
      {data.sauce_temp > 175 && (
        <group position={[-6, 4.5, 0]}>
          <Sparkles
            count={30}
            scale={[2, 3, 2]}
            size={3}
            speed={0.8}
            color="#ffffff"
            opacity={0.4}
          />
        </group>
      )}

      {/* ALERT GLOW (anomaly detected) */}
      {data.anomaly_score > 0.5 && (
        <AlertGlow intensity={data.anomaly_score} />
      )}
    </group>
  )
}

/**
 * Alert glow effect for anomaly visualization.
 */
function AlertGlow({ intensity = 0.5 }) {
  const glowRef = useRef()

  useFrame((state) => {
    if (glowRef.current) {
      const pulse = 0.5 + Math.sin(state.clock.elapsedTime * 8) * 0.5
      glowRef.current.material.opacity = intensity * 0.3 * pulse
    }
  })

  return (
    <mesh ref={glowRef} position={[0, 2, 0]}>
      <sphereGeometry args={[8, 16, 16]} />
      <meshBasicMaterial
        color="#ff0000"
        transparent
        opacity={0.2}
        side={THREE.BackSide}
      />
    </mesh>
  )
}

/**
 * Steam cloud effect for high temperature visualization.
 */
export function SteamCloud({ position = [0, 0, 0], intensity = 1 }) {
  const cloudRef = useRef()

  useFrame((state, delta) => {
    if (cloudRef.current) {
      cloudRef.current.position.y += delta * 0.3 * intensity
      cloudRef.current.rotation.y += delta * 0.2

      // Reset when too high
      if (cloudRef.current.position.y > 8) {
        cloudRef.current.position.y = 4
      }
    }
  })

  return (
    <group ref={cloudRef} position={position}>
      <Cloud
        opacity={0.3 * intensity}
        speed={0.4}
        segments={15}
        bounds={[2, 1, 2]}
        color="#ffffff"
      />
    </group>
  )
}

/**
 * Sparks effect for mechanical faults.
 */
export function SparkEffect({ position = [0, 0, 0], active = false }) {
  const particlesRef = useRef()
  const particles = useRef([])
  const maxParticles = 30

  useEffect(() => {
    particles.current = Array.from({ length: maxParticles }).map(() => ({
      position: new THREE.Vector3(),
      velocity: new THREE.Vector3(),
      life: 0,
      active: false
    }))
  }, [])

  useFrame((state, delta) => {
    if (!particlesRef.current) return

    // Spawn sparks when active
    if (active && Math.random() < 0.3) {
      const inactiveParticle = particles.current.find(p => !p.active)
      if (inactiveParticle) {
        inactiveParticle.active = true
        inactiveParticle.life = 0.5 + Math.random() * 0.5
        inactiveParticle.position.set(
          (Math.random() - 0.5) * 0.5,
          0,
          (Math.random() - 0.5) * 0.5
        )
        inactiveParticle.velocity.set(
          (Math.random() - 0.5) * 4,
          Math.random() * 3 + 2,
          (Math.random() - 0.5) * 4
        )
      }
    }

    // Update particles
    const positions = particlesRef.current.geometry.attributes.position
    let visibleCount = 0

    particles.current.forEach((particle) => {
      if (particle.active) {
        particle.life -= delta
        particle.position.addScaledVector(particle.velocity, delta)
        particle.velocity.y -= 15 * delta // Fast gravity for sparks

        if (particle.life <= 0) {
          particle.active = false
        } else {
          positions.setXYZ(visibleCount, particle.position.x, particle.position.y, particle.position.z)
          visibleCount++
        }
      }
    })

    for (let i = visibleCount; i < maxParticles; i++) {
      positions.setXYZ(i, 0, -100, 0)
    }

    positions.needsUpdate = true
  })

  return (
    <points ref={particlesRef} position={position}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={maxParticles}
          array={new Float32Array(maxParticles * 3)}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        color="#ffaa00"
        size={0.1}
        sizeAttenuation
        transparent
        opacity={0.9}
      />
    </points>
  )
}

export default SauceParticles
