import { Suspense, useEffect } from 'react'
import { Canvas } from '@react-three/fiber'
import { Loader, Preload } from '@react-three/drei'
import * as THREE from 'three'

import { FactoryScene } from './FactoryScene'
import { Effects } from './Effects'
import { HUD } from './HUD'
import { useSocket } from '../hooks/useSocket'

/**
 * Main Application Component
 *
 * Sets up:
 * - React Three Fiber Canvas with WebGL configuration
 * - Rapier physics world
 * - Keyboard controls for player movement
 * - Socket.IO connection for real-time data
 * - Post-processing effects
 * - HUD overlay
 */
export default function App() {
  // Initialize WebSocket connection
  useSocket()

  return (
    <div className="w-screen h-screen bg-rig-bg overflow-hidden">
      {/* Three.js Canvas */}
      <Canvas
        shadows
        dpr={[1, 2]}
        gl={{
          antialias: true,
          toneMapping: THREE.ACESFilmicToneMapping,
          toneMappingExposure: 1.0,
          outputColorSpace: THREE.SRGBColorSpace,
          powerPreference: 'high-performance'
        }}
        camera={{
          fov: 65,
          near: 0.1,
          far: 500,
          position: [0, 2, 15]
        }}
        onCreated={({ gl }) => {
          // Enable shadow maps
          gl.shadowMap.enabled = true
          gl.shadowMap.type = THREE.PCFSoftShadowMap
        }}
      >
        {/* Loading fallback */}
        <Suspense fallback={<LoadingFallback />}>
          {/* Main scene content (no physics needed for simple FPS) */}
          <FactoryScene />

          {/* Post-processing effects - TEMPORARILY DISABLED FOR DEBUGGING */}
          {/* <Effects /> */}

          {/* Preload assets */}
          <Preload all />
        </Suspense>
      </Canvas>

      {/* HTML Overlay UI */}
      <HUD />

      {/* Loading progress bar (drei) */}
      <Loader
        containerStyles={{
          background: '#0a0a0a',
        }}
        innerStyles={{
          background: '#00ffff',
          width: '200px',
          height: '3px',
        }}
        barStyles={{
          background: '#00ffff',
          height: '3px',
        }}
        dataStyles={{
          color: '#00ffff',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '12px',
        }}
        dataInterpolation={(p) => `LOADING DIGITAL TWIN... ${p.toFixed(0)}%`}
      />

      {/* Clickstart overlay */}
      <ClickToStart />
    </div>
  )
}

/**
 * 3D loading fallback (shown inside Canvas while assets load)
 */
function LoadingFallback() {
  return (
    <>
      <ambientLight intensity={0.1} />
      <mesh position={[0, 2, 0]}>
        <boxGeometry args={[2, 2, 2]} />
        <meshStandardMaterial color="#00ffff" wireframe />
      </mesh>
    </>
  )
}

/**
 * Click to start overlay (for pointer lock)
 */
function ClickToStart() {
  useEffect(() => {
    const overlay = document.getElementById('click-overlay')
    if (!overlay) return

    const handlePointerLockChange = () => {
      if (document.pointerLockElement) {
        overlay.style.display = 'none'
      } else {
        overlay.style.display = 'flex'
      }
    }

    document.addEventListener('pointerlockchange', handlePointerLockChange)
    return () => {
      document.removeEventListener('pointerlockchange', handlePointerLockChange)
    }
  }, [])

  return (
    <div
      id="click-overlay"
      className="fixed inset-0 bg-black/80 flex flex-col items-center justify-center z-40 cursor-pointer"
      onClick={() => document.body.requestPointerLock()}
    >
      <div className="text-center">
        <h1 className="text-4xl font-bold text-rig-cyan mb-4 tracking-widest glow-cyan">
          RIG ALPHA
        </h1>
        <p className="text-xl text-gray-300 mb-8">3D DIGITAL TWIN</p>
        <div className="border-2 border-rig-cyan/50 rounded-lg px-8 py-4 animate-pulse">
          <p className="text-rig-cyan text-lg">CLICK TO ENTER</p>
        </div>
        <p className="text-gray-500 text-sm mt-6">
          Use WASD to move, Mouse to look around
        </p>
      </div>
    </div>
  )
}
