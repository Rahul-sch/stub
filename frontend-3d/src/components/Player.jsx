import { useRef, useEffect } from 'react'
import { useThree, useFrame } from '@react-three/fiber'
import { PointerLockControls } from '@react-three/drei'
import * as THREE from 'three'

/**
 * Simple first-person player controller using PointerLockControls.
 *
 * Much simpler than Ecctrl - no physics, just camera movement.
 * This ensures the scene is visible while we debug.
 */
export function Player({ startPosition = [0, 2, 15] }) {
  const controlsRef = useRef()
  const { camera } = useThree()

  // Movement state
  const moveState = useRef({
    forward: false,
    backward: false,
    left: false,
    right: false
  })

  // Set initial camera position
  useEffect(() => {
    camera.position.set(...startPosition)
  }, [camera, startPosition])

  // Handle keyboard input
  useEffect(() => {
    const handleKeyDown = (e) => {
      switch (e.code) {
        case 'KeyW':
        case 'ArrowUp':
          moveState.current.forward = true
          break
        case 'KeyS':
        case 'ArrowDown':
          moveState.current.backward = true
          break
        case 'KeyA':
        case 'ArrowLeft':
          moveState.current.left = true
          break
        case 'KeyD':
        case 'ArrowRight':
          moveState.current.right = true
          break
      }
    }

    const handleKeyUp = (e) => {
      switch (e.code) {
        case 'KeyW':
        case 'ArrowUp':
          moveState.current.forward = false
          break
        case 'KeyS':
        case 'ArrowDown':
          moveState.current.backward = false
          break
        case 'KeyA':
        case 'ArrowLeft':
          moveState.current.left = false
          break
        case 'KeyD':
        case 'ArrowRight':
          moveState.current.right = false
          break
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    document.addEventListener('keyup', handleKeyUp)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('keyup', handleKeyUp)
    }
  }, [])

  // Movement loop
  useFrame((state, delta) => {
    if (!controlsRef.current?.isLocked) return

    const speed = 8 * delta
    const direction = new THREE.Vector3()

    // Get camera direction
    camera.getWorldDirection(direction)
    direction.y = 0
    direction.normalize()

    // Calculate right vector
    const right = new THREE.Vector3()
    right.crossVectors(camera.up, direction).normalize()

    // Apply movement
    if (moveState.current.forward) {
      camera.position.addScaledVector(direction, speed)
    }
    if (moveState.current.backward) {
      camera.position.addScaledVector(direction, -speed)
    }
    if (moveState.current.left) {
      camera.position.addScaledVector(right, speed)
    }
    if (moveState.current.right) {
      camera.position.addScaledVector(right, -speed)
    }

    // Keep camera at fixed height (no gravity for now)
    camera.position.y = startPosition[1]
  })

  return <PointerLockControls ref={controlsRef} />
}

export default Player
