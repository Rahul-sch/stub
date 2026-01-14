import { useRef, useCallback } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import { useSensorStore } from '../store/useSensorStore'

/**
 * Interaction system for rig selection via raycasting.
 *
 * Features:
 * - Casts ray from camera center each frame
 * - Detects when looking at a rig
 * - Updates selected rig in store (triggers HUD update)
 *
 * @param {Array} rigs - Array of rig configurations with positions
 */
export function InteractionSystem({ rigs = [] }) {
  const { camera, scene } = useThree()
  const raycaster = useRef(new THREE.Raycaster())
  const direction = useRef(new THREE.Vector3())

  const setSelectedRig = useSensorStore((s) => s.setSelectedRig)
  const clearSelectedRig = useSensorStore((s) => s.clearSelectedRig)

  // Detection distance
  const maxDistance = 30

  // Frame-based raycasting
  useFrame(() => {
    // Get camera forward direction
    camera.getWorldDirection(direction.current)

    // Set up raycaster from camera position
    raycaster.current.set(camera.position, direction.current)
    raycaster.current.far = maxDistance

    // Check intersections with scene
    const intersects = raycaster.current.intersectObjects(scene.children, true)

    let foundRig = null

    for (const intersect of intersects) {
      // Traverse up the parent chain to find rig group
      let obj = intersect.object

      while (obj) {
        // Check if this object's position matches a rig position
        for (const rig of rigs) {
          const rigX = rig.position[0]
          const rigZ = rig.position[2]

          // Check if object is within rig bounding area
          if (obj.position) {
            const worldPos = new THREE.Vector3()
            obj.getWorldPosition(worldPos)

            const dx = Math.abs(worldPos.x - rigX)
            const dz = Math.abs(worldPos.z - rigZ)

            // If within rig bounds (5 unit radius)
            if (dx < 5 && dz < 5 && intersect.distance < maxDistance) {
              foundRig = rig.id
              break
            }
          }
        }

        if (foundRig) break
        obj = obj.parent
      }

      if (foundRig) break
    }

    // Update store
    if (foundRig) {
      setSelectedRig(foundRig)
    } else {
      clearSelectedRig()
    }
  })

  // This component doesn't render anything
  return null
}

/**
 * Simple proximity-based interaction (alternative to raycasting).
 * More performant but less precise.
 */
export function ProximityInteraction({ rigs = [], activationDistance = 10 }) {
  const { camera } = useThree()

  const setSelectedRig = useSensorStore((s) => s.setSelectedRig)
  const clearSelectedRig = useSensorStore((s) => s.clearSelectedRig)

  useFrame(() => {
    let closestRig = null
    let closestDistance = Infinity

    for (const rig of rigs) {
      const dx = camera.position.x - rig.position[0]
      const dz = camera.position.z - rig.position[2]
      const distance = Math.sqrt(dx * dx + dz * dz)

      if (distance < activationDistance && distance < closestDistance) {
        closestDistance = distance
        closestRig = rig.id
      }
    }

    if (closestRig) {
      setSelectedRig(closestRig)
    } else {
      clearSelectedRig()
    }
  })

  return null
}

export default InteractionSystem
