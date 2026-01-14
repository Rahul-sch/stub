import {
  EffectComposer,
  Bloom,
  Vignette,
  Noise,
  ChromaticAberration,
  ToneMapping,
  SMAA
} from '@react-three/postprocessing'
import { BlendFunction, KernelSize, ToneMappingMode } from 'postprocessing'
import { useSensorStore, getTransientState } from '../store/useSensorStore'
import { useFrame } from '@react-three/fiber'
import { useRef, useMemo } from 'react'
import * as THREE from 'three'

/**
 * Post-processing effects pipeline for cyberpunk industrial aesthetic.
 *
 * Effects stack:
 * 1. SMAA - Anti-aliasing
 * 2. Bloom - Unreal-style glow for emissives
 * 3. Vignette - Darkened edges for focus
 * 4. Noise - Subtle film grain
 * 5. Chromatic Aberration - Dynamic based on anomaly state
 * 6. Tone Mapping - ACES Filmic for cinematic look
 */
export function Effects() {
  const chromaticRef = useRef()

  // Dynamic chromatic aberration based on anomaly state
  useFrame(() => {
    if (!chromaticRef.current) return

    // Check if any rig has high anomaly score
    const rigs = getTransientState().rigs
    const maxAnomalyScore = Math.max(
      rigs.A?.anomalyScore || 0,
      rigs.B?.anomalyScore || 0,
      rigs.C?.anomalyScore || 0
    )

    // Increase chromatic aberration during anomalies
    if (maxAnomalyScore > 0.5) {
      const intensity = (maxAnomalyScore - 0.5) * 0.01
      chromaticRef.current.offset.x = intensity * (Math.random() - 0.5)
      chromaticRef.current.offset.y = intensity * (Math.random() - 0.5)
    } else {
      // Subtle base aberration
      chromaticRef.current.offset.x = 0.0005
      chromaticRef.current.offset.y = 0.0005
    }
  })

  return (
    <EffectComposer multisampling={0}>
      {/* Anti-aliasing */}
      <SMAA />

      {/* Unreal Bloom - key to the cyberpunk glow effect
          - Lower threshold so more objects contribute to scene brightness */}
      <Bloom
        intensity={0.8}
        luminanceThreshold={0.6}
        luminanceSmoothing={0.9}
        kernelSize={KernelSize.LARGE}
        mipmapBlur={true}
      />

      {/* Vignette - darkens edges for cinematic focus - REDUCED */}
      <Vignette
        offset={0.5}
        darkness={0.3}
        blendFunction={BlendFunction.NORMAL}
      />

      {/* Film grain noise - subtle, adds texture */}
      <Noise
        opacity={0.04}
        blendFunction={BlendFunction.OVERLAY}
      />

      {/* Chromatic aberration - subtle color fringing
          Increases during anomalies for "distortion" effect */}
      <ChromaticAberration
        ref={chromaticRef}
        offset={new THREE.Vector2(0.0005, 0.0005)}
        blendFunction={BlendFunction.NORMAL}
        radialModulation={false}
      />

      {/* ACES Filmic tone mapping for cinematic colors */}
      <ToneMapping mode={ToneMappingMode.ACES_FILMIC} />
    </EffectComposer>
  )
}

/**
 * Minimal effects for lower-end hardware.
 * Use this if performance is an issue.
 */
export function EffectsMinimal() {
  return (
    <EffectComposer multisampling={0}>
      <Bloom
        intensity={1.0}
        luminanceThreshold={1.0}
        luminanceSmoothing={0.9}
        kernelSize={KernelSize.MEDIUM}
      />
      <Vignette offset={0.4} darkness={0.7} />
    </EffectComposer>
  )
}

export default Effects
