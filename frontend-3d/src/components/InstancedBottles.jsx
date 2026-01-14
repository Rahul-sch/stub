import { useRef, useMemo, useEffect } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { getKetchupTransientState } from '../store/useSensorStore'

/**
 * Instanced ketchup bottles for a single production line.
 * Uses THREE.InstancedMesh for performance - renders many bottles in one draw call.
 *
 * Props:
 * - lineId: Production line ID (L01-L25)
 * - count: Number of bottle instances (default 8)
 * - conveyorLength: Length of the conveyor in units (default 10)
 *
 * Data bindings:
 * - bottle_flow_rate → bottle movement speed
 * - label_alignment → bottle tilt angle
 * - fill_level → bottle color intensity (visual feedback)
 */
export function InstancedBottles({
  lineId,
  count = 8,
  conveyorLength = 10,
  bottleScale = 0.35
}) {
  const meshRef = useRef()
  const dummy = useMemo(() => new THREE.Object3D(), [])
  const colorArray = useRef(new Float32Array(count * 3))

  // Create bottle geometry (simplified ketchup bottle shape)
  const geometry = useMemo(() => {
    // Composite geometry: bottle body + neck + cap
    const bodyGeo = new THREE.CylinderGeometry(0.3, 0.35, 1.2, 8)
    const neckGeo = new THREE.CylinderGeometry(0.12, 0.2, 0.4, 8)
    const capGeo = new THREE.CylinderGeometry(0.15, 0.15, 0.15, 8)

    // Position parts
    neckGeo.translate(0, 0.8, 0)
    capGeo.translate(0, 1.1, 0)

    // Merge into single geometry
    const mergedGeo = new THREE.BufferGeometry()

    // For simplicity, just use the body geometry
    // In production, you'd merge or use a loaded GLB
    return bodyGeo
  }, [])

  // Create material with vertex colors for fill level visualization
  const material = useMemo(() => {
    return new THREE.MeshStandardMaterial({
      color: '#cc0000',
      roughness: 0.3,
      metalness: 0.1,
      transparent: true,
      opacity: 0.95
    })
  }, [])

  // Initialize instance matrices
  useEffect(() => {
    if (!meshRef.current) return

    for (let i = 0; i < count; i++) {
      dummy.position.set(0, 0, 0)
      dummy.rotation.set(0, 0, 0)
      dummy.scale.setScalar(bottleScale)
      dummy.updateMatrix()
      meshRef.current.setMatrixAt(i, dummy.matrix)
    }
    meshRef.current.instanceMatrix.needsUpdate = true
  }, [count, dummy, bottleScale])

  // Animation loop - move bottles along conveyor
  useFrame((state, delta) => {
    if (!meshRef.current) return

    const data = getKetchupTransientState().lines[lineId]
    if (!data) return

    // Speed based on bottle flow rate (normalized to 1.0 at 150 bottles/min)
    const speed = (data.bottle_flow_rate / 150) * 0.8
    const tilt = (data.label_alignment / 5) * 0.15 // Label misalignment → tilt

    // Color intensity based on fill level
    const fillIntensity = data.fill_level / 100

    for (let i = 0; i < count; i++) {
      // Calculate position along conveyor (staggered by index)
      const phase = (i / count)
      const t = ((state.clock.elapsedTime * speed + phase) % 1)

      // X position: -conveyorLength/2 to +conveyorLength/2
      const x = -conveyorLength / 2 + t * conveyorLength

      // Y position: on top of conveyor
      const y = 0.9

      // Z position: centered with slight stagger
      const z = (i % 2) * 0.05 - 0.025

      dummy.position.set(x, y, z)

      // Rotation: upright with label misalignment tilt
      dummy.rotation.set(0, 0, tilt)

      dummy.scale.setScalar(bottleScale)
      dummy.updateMatrix()

      meshRef.current.setMatrixAt(i, dummy.matrix)
    }

    meshRef.current.instanceMatrix.needsUpdate = true

    // Update material color based on fill level (darker = fuller)
    material.color.setRGB(
      0.8 * fillIntensity,
      0.1 * fillIntensity,
      0.05 * fillIntensity
    )
  })

  return (
    <instancedMesh
      ref={meshRef}
      args={[geometry, material, count]}
      castShadow
      receiveShadow
    />
  )
}

/**
 * Global instanced bottles for all 25 lines.
 * Uses a single InstancedMesh for maximum performance.
 */
export function GlobalInstancedBottles({ lines, bottlesPerLine = 6 }) {
  const meshRef = useRef()
  const totalCount = lines.length * bottlesPerLine
  const dummy = useMemo(() => new THREE.Object3D(), [])

  // Create bottle geometry
  const geometry = useMemo(() => {
    return new THREE.CylinderGeometry(0.3, 0.35, 1.2, 6)
  }, [])

  const material = useMemo(() => {
    return new THREE.MeshStandardMaterial({
      color: '#cc0000',
      roughness: 0.3,
      metalness: 0.1
    })
  }, [])

  useFrame((state, delta) => {
    if (!meshRef.current) return

    let instanceIndex = 0

    lines.forEach((line, lineIndex) => {
      const data = getKetchupTransientState().lines[line.id]
      if (!data) return

      const speed = (data.bottle_flow_rate / 150) * 0.8
      const tilt = (data.label_alignment / 5) * 0.15
      const conveyorLength = 10

      for (let i = 0; i < bottlesPerLine; i++) {
        const phase = i / bottlesPerLine
        const t = ((state.clock.elapsedTime * speed + phase) % 1)

        const localX = -conveyorLength / 2 + t * conveyorLength
        const localY = 0.9
        const localZ = (i % 2) * 0.05 - 0.025

        // Transform to world position
        const worldX = line.position[0] + localX
        const worldY = line.position[1] + localY
        const worldZ = line.position[2] + localZ

        dummy.position.set(worldX, worldY, worldZ)
        dummy.rotation.set(0, 0, tilt)
        dummy.scale.setScalar(0.35)
        dummy.updateMatrix()

        meshRef.current.setMatrixAt(instanceIndex, dummy.matrix)
        instanceIndex++
      }
    })

    meshRef.current.instanceMatrix.needsUpdate = true
  })

  return (
    <instancedMesh
      ref={meshRef}
      args={[geometry, material, totalCount]}
      castShadow
      receiveShadow
    />
  )
}

export default InstancedBottles
