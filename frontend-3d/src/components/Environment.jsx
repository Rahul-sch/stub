import { useRef } from 'react'
import {
  MeshReflectorMaterial,
  Environment as DreiEnvironment,
  Stars,
  Grid
} from '@react-three/drei'
import * as THREE from 'three'

/**
 * Factory environment with cyberpunk industrial aesthetic.
 *
 * Features:
 * - HDRI environment lighting (warehouse preset)
 * - Reflective factory floor
 * - Atmospheric fog
 * - Moody directional and point lights
 * - Stars backdrop for depth
 */
export function Environment() {
  return (
    <>
      {/* HDRI Environment for reflections and ambient lighting */}
      <DreiEnvironment
        preset="warehouse"
        background={false}
        environmentIntensity={0.3}
      />

      {/* Atmospheric fog - pushed very far back for visibility */}
      <fog attach="fog" args={['#1a1a2e', 100, 250]} />

      {/* Ambient - BRIGHT for visibility everywhere */}
      <ambientLight intensity={0.8} color="#ffffff" />

      {/* Hemisphere light for natural fill - boosted */}
      <hemisphereLight
        skyColor="#aaaacc"
        groundColor="#444444"
        intensity={0.8}
        position={[0, 50, 0]}
      />

      {/* Main overhead light - white, covers whole scene */}
      <directionalLight
        position={[0, 50, 0]}
        intensity={1.5}
        color="#ffffff"
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-far={150}
        shadow-camera-left={-80}
        shadow-camera-right={80}
        shadow-camera-top={80}
        shadow-camera-bottom={-80}
        shadow-bias={-0.0001}
      />

      {/* Key light - cyan industrial accent */}
      <directionalLight
        position={[15, 30, 10]}
        intensity={1.0}
        color="#00ffff"
      />

      {/* Back light - illuminates player spawn area */}
      <directionalLight
        position={[0, 30, 50]}
        intensity={1.0}
        color="#ffffff"
      />

      {/* Fill light - warm industrial */}
      <pointLight
        position={[-20, 15, -20]}
        intensity={0.3}
        color="#ff6600"
        distance={80}
        decay={2}
      />

      {/* Accent light - purple cyberpunk */}
      <pointLight
        position={[30, 10, 20]}
        intensity={0.2}
        color="#9945FF"
        distance={60}
        decay={2}
      />

      {/* Rim lights for each rig position */}
      <RigLights />

      {/* Factory floor with reflections */}
      <FactoryFloor />

      {/* Grid helper for spatial reference */}
      <Grid
        position={[0, 0.01, 0]}
        args={[100, 100]}
        cellSize={2}
        cellThickness={0.5}
        cellColor="#00ffff"
        sectionSize={10}
        sectionThickness={1}
        sectionColor="#00ffff"
        fadeDistance={80}
        fadeStrength={1}
        followCamera={false}
        infiniteGrid={true}
      />

      {/* Stars for depth and atmosphere */}
      <Stars
        radius={200}
        depth={100}
        count={2000}
        factor={4}
        saturation={0}
        fade
        speed={0.5}
      />

      {/* Factory walls (optional boundaries) */}
      <FactoryWalls />
    </>
  )
}

/**
 * Overhead rig lights - one for each machine position
 */
function RigLights() {
  const rigPositions = [
    { x: -20, color: '#00ffff' },  // Rig A - cyan
    { x: 0, color: '#00ff41' },    // Rig B - green
    { x: 20, color: '#ff6600' }    // Rig C - orange
  ]

  return (
    <>
      {rigPositions.map((rig, i) => (
        <spotLight
          key={i}
          position={[rig.x, 20, 0]}
          target-position={[rig.x, 0, 0]}
          angle={0.4}
          penumbra={0.5}
          intensity={0.8}
          color={rig.color}
          castShadow
          shadow-mapSize={[1024, 1024]}
        />
      ))}
    </>
  )
}

/**
 * Reflective factory floor with physics collider
 */
function FactoryFloor() {
  const floorRef = useRef()

  return (
    <mesh
      ref={floorRef}
      rotation={[-Math.PI / 2, 0, 0]}
      position={[0, 0, 0]}
      receiveShadow
    >
      <planeGeometry args={[200, 200]} />
      <MeshReflectorMaterial
        blur={[400, 100]}
        resolution={1024}
        mixBlur={1}
        mixStrength={10}
        roughness={0.7}
        depthScale={1.2}
        minDepthThreshold={0.4}
        maxDepthThreshold={1.4}
        color="#222233"
        metalness={0.5}
        mirror={0.3}
      />
    </mesh>
  )
}

/**
 * Factory boundary walls (invisible colliders with subtle visual)
 */
function FactoryWalls() {
  // Walls are just for visual boundary - no physics needed
  return null
}

export default Environment
