import { useRef } from 'react'
import {
  MeshReflectorMaterial,
  Environment as DreiEnvironment,
  Grid,
  Sparkles
} from '@react-three/drei'
import * as THREE from 'three'

/**
 * Ketchup Factory environment with warm industrial aesthetic.
 *
 * Features:
 * - HDRI environment lighting (warehouse preset)
 * - Reflective factory floor
 * - Red/warm industrial color scheme
 * - Atmospheric fog
 * - Overhead row lighting for 25 production lines
 * - Dust particles for atmosphere
 */
export function KetchupEnvironment() {
  return (
    <>
      {/* HDRI Environment for reflections and ambient lighting */}
      <DreiEnvironment
        preset="warehouse"
        background={false}
        environmentIntensity={0.4}
      />

      {/* Atmospheric fog - warm red tint */}
      <fog attach="fog" args={['#1a0a0a', 80, 200]} />

      {/* Ambient - warm factory lighting */}
      <ambientLight intensity={0.6} color="#ffe0d0" />

      {/* Hemisphere light for natural fill */}
      <hemisphereLight
        skyColor="#ffccaa"
        groundColor="#442222"
        intensity={0.6}
        position={[0, 50, 0]}
      />

      {/* Main overhead light - bright white */}
      <directionalLight
        position={[0, 60, 0]}
        intensity={1.2}
        color="#ffffff"
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-far={200}
        shadow-camera-left={-100}
        shadow-camera-right={100}
        shadow-camera-top={100}
        shadow-camera-bottom={-100}
        shadow-bias={-0.0001}
      />

      {/* Row lights - one for each row of 5 lines */}
      <RowLights />

      {/* Red accent lights (ketchup theme) */}
      <pointLight
        position={[-80, 12, 0]}
        intensity={1.0}
        color="#ff3300"
        distance={120}
        decay={2}
      />
      <pointLight
        position={[80, 12, 0]}
        intensity={1.0}
        color="#ff3300"
        distance={120}
        decay={2}
      />

      {/* Corner accent lights - orange/yellow */}
      <pointLight position={[-70, 8, -60]} intensity={0.4} color="#ff6600" distance={60} decay={2} />
      <pointLight position={[70, 8, -60]} intensity={0.4} color="#ff6600" distance={60} decay={2} />
      <pointLight position={[-70, 8, 60]} intensity={0.4} color="#ff6600" distance={60} decay={2} />
      <pointLight position={[70, 8, 60]} intensity={0.4} color="#ff6600" distance={60} decay={2} />

      {/* Factory floor with reflections */}
      <KetchupFactoryFloor />

      {/* Grid helper for spatial reference */}
      <Grid
        position={[0, 0.02, 0]}
        args={[200, 150]}
        cellSize={5}
        cellThickness={0.5}
        cellColor="#ff3300"
        sectionSize={25}
        sectionThickness={1}
        sectionColor="#ff6600"
        fadeDistance={120}
        fadeStrength={1}
        followCamera={false}
        infiniteGrid={true}
      />


      {/* Dust particles for factory atmosphere */}
      <Sparkles
        count={400}
        scale={[180, 30, 140]}
        size={1.5}
        speed={0.15}
        color="#ffaa88"
        opacity={0.4}
      />
    </>
  )
}

/**
 * Overhead row lights - industrial fluorescent style
 * One light strip per row (5 rows for 25 lines)
 */
function RowLights() {
  const rowPositions = [-50, -25, 0, 25, 50]
  const colors = ['#ffffff', '#fff8f0', '#ffffff', '#fff8f0', '#ffffff']

  return (
    <>
      {rowPositions.map((z, i) => (
        <group key={i}>
          {/* Main row light */}
          <rectAreaLight
            position={[0, 18, z]}
            width={140}
            height={3}
            intensity={3}
            color={colors[i]}
            rotation={[-Math.PI / 2, 0, 0]}
          />
          {/* Secondary fill lights along the row */}
          {[-60, -30, 0, 30, 60].map((x, j) => (
            <spotLight
              key={j}
              position={[x, 16, z]}
              angle={0.5}
              penumbra={0.6}
              intensity={0.6}
              color="#ffffff"
              castShadow
              shadow-mapSize={[512, 512]}
            />
          ))}
        </group>
      ))}
    </>
  )
}

/**
 * Reflective factory floor
 */
function KetchupFactoryFloor() {
  const floorRef = useRef()

  return (
    <mesh
      ref={floorRef}
      rotation={[-Math.PI / 2, 0, 0]}
      position={[0, 0, 0]}
      receiveShadow
    >
      <planeGeometry args={[300, 200]} />
      <MeshReflectorMaterial
        blur={[400, 100]}
        resolution={1024}
        mixBlur={1}
        mixStrength={12}
        roughness={0.75}
        depthScale={1.2}
        minDepthThreshold={0.4}
        maxDepthThreshold={1.4}
        color="#2a2020"
        metalness={0.4}
        mirror={0.25}
      />
    </mesh>
  )
}

export default KetchupEnvironment
