'use client';

import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import type { TrackReference } from '@livekit/components-react';
import { VRM, VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';

// Simple OrbitControls implementation
class SimpleOrbitControls {
  private camera: THREE.Camera;
  private domElement: HTMLElement;
  private target = new THREE.Vector3(0, 1.2, 0);
  private spherical = new THREE.Spherical();
  private offset = new THREE.Vector3();
  private isDragging = false;
  private rotateStart = new THREE.Vector2();
  private rotateDelta = new THREE.Vector2();
  private minDistance = 0.5;
  private maxDistance = 5;

  constructor(camera: THREE.Camera, domElement: HTMLElement) {
    this.camera = camera;
    this.domElement = domElement;

    this.domElement.addEventListener('mousedown', this.onMouseDown);
    this.domElement.addEventListener('wheel', this.onWheel);
  }

  private onMouseDown = (event: MouseEvent) => {
    this.isDragging = true;
    this.rotateStart.set(event.clientX, event.clientY);

    document.addEventListener('mousemove', this.onMouseMove);
    document.addEventListener('mouseup', this.onMouseUp);
  };

  private onMouseMove = (event: MouseEvent) => {
    if (!this.isDragging) return;

    this.rotateDelta.set(event.clientX - this.rotateStart.x, event.clientY - this.rotateStart.y);

    const rotateSpeed = 0.005;
    this.spherical.theta -= this.rotateDelta.x * rotateSpeed;
    this.spherical.phi -= this.rotateDelta.y * rotateSpeed;

    this.spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, this.spherical.phi));

    this.rotateStart.set(event.clientX, event.clientY);
    this.update();
  };

  private onMouseUp = () => {
    this.isDragging = false;
    document.removeEventListener('mousemove', this.onMouseMove);
    document.removeEventListener('mouseup', this.onMouseUp);
  };

  private onWheel = (event: WheelEvent) => {
    event.preventDefault();
    this.spherical.radius += event.deltaY * 0.001;
    this.spherical.radius = Math.max(
      this.minDistance,
      Math.min(this.maxDistance, this.spherical.radius)
    );
    this.update();
  };

  update() {
    this.offset.setFromSpherical(this.spherical);
    this.camera.position.copy(this.target).add(this.offset);
    this.camera.lookAt(this.target);
  }

  initialize() {
    this.offset.copy(this.camera.position).sub(this.target);
    this.spherical.setFromVector3(this.offset);
    this.update();
  }

  dispose() {
    this.domElement.removeEventListener('mousedown', this.onMouseDown);
    this.domElement.removeEventListener('wheel', this.onWheel);
    document.removeEventListener('mousemove', this.onMouseMove);
    document.removeEventListener('mouseup', this.onMouseUp);
  }
}

interface VRMAvatarSceneProps {
  modelPath: string;
  audioTrack?: TrackReference;
}

// Easing functions for natural motion
const easeInOutCubic = (t: number): number => {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
};

const easeOutQuad = (t: number): number => {
  return 1 - (1 - t) * (1 - t);
};

const easeInOutQuad = (t: number): number => {
  return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
};

// Smooth interpolation with configurable speed
const smoothLerp = (current: number, target: number, factor: number, deltaTime: number): number => {
  const adjustedFactor = 1 - Math.pow(1 - factor, deltaTime * 60);
  return current + (target - current) * adjustedFactor;
};

export default function VRMAvatarScene({ modelPath, audioTrack }: VRMAvatarSceneProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    // Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x000000);

    // Camera
    const camera = new THREE.PerspectiveCamera(30, width / height, 0.1, 100);
    camera.position.set(0, 1.4, 1.5);

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.shadowMap.enabled = true;
    container.appendChild(renderer.domElement);

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
    scene.add(ambientLight);

    const directionalLight1 = new THREE.DirectionalLight(0xffffff, 1.5);
    directionalLight1.position.set(1, 2, 3);
    directionalLight1.castShadow = true;
    scene.add(directionalLight1);

    const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.5);
    directionalLight2.position.set(-1, 1, -1);
    scene.add(directionalLight2);

    const hemisphereLight = new THREE.HemisphereLight(0xffffff, 0x444444, 0.5);
    scene.add(hemisphereLight);

    // Controls
    const controls = new SimpleOrbitControls(camera, renderer.domElement);
    controls.initialize();

    // Clock for animation
    const clock = new THREE.Clock();
    let vrm: VRM | null = null;
    let nextBlinkTime = 2 + Math.random() * 3;

    // Audio analysis for lip-sync
    let audioContext: AudioContext | null = null;
    let analyser: AnalyserNode | null = null;
    let dataArray: Uint8Array = new Uint8Array(0);
    let audioSource: MediaStreamAudioSourceNode | null = null;

    // Animation state with smooth interpolation
    let isSpeaking = false;
    let speechIntensity = 0;
    let targetSpeechIntensity = 0;
    let gesturePhase = 0;
    let currentGesture = 0;
    let nextGestureTime = 0;
    let gestureTransitionProgress = 0;
    let previousGesture = 0;

    // Smooth interpolation targets for body parts
    const headRotation = { x: 0, y: 0, z: 0 };
    const targetHeadRotation = { x: 0, y: 0, z: 0 };
    const previousHeadRotation = { x: 0, y: 0, z: 0 };
    
    const leftArmRotation = { x: 0, y: 0, z: -1.2 };
    const rightArmRotation = { x: 0, y: 0, z: 1.2 };
    const targetLeftArmRotation = { x: 0, y: 0, z: -1.2 };
    const targetRightArmRotation = { x: 0, y: 0, z: 1.2 };
    
    const leftLowerArmRotation = { x: -0.2 };
    const rightLowerArmRotation = { x: -0.2 };
    const targetLeftLowerArmRotation = { x: -0.2 };
    const targetRightLowerArmRotation = { x: -0.2 };
    
    const handRotation = { left: { x: 0, y: 0, z: 0 }, right: { x: 0, y: 0, z: 0 } };
    const targetHandRotation = { left: { x: 0, y: 0, z: 0 }, right: { x: 0, y: 0, z: 0 } };

    // Additional animation state
    let eyebrowIntensity = 0;
    let targetEyebrowIntensity = 0;
    const neckRotation = { x: 0, y: 0, z: 0 };
    const targetNeckRotation = { x: 0, y: 0, z: 0 };

    // Facial expression state with smooth transitions
    let currentExpression = 'neutral';
    let previousExpression = 'neutral';
    let expressionIntensity = 0;
    let targetExpressionIntensity = 0;
    let nextExpressionTime = 0;
    let expressionTransitionProgress = 1;

    // Mouth shape smoothing
    const mouthShapes = { aa: 0, ih: 0, ou: 0, oh: 0 };
    const targetMouthShapes = { aa: 0, ih: 0, ou: 0, oh: 0 };

    // Expression values for smooth blending
    const expressionValues = {
      happy: 0,
      surprised: 0,
      relaxed: 0,
      neutral: 0,
      sad: 0,
      angry: 0,
      blink: 0,
    };
    const targetExpressionValues = {
      happy: 0,
      surprised: 0,
      relaxed: 0,
      neutral: 0,
      sad: 0,
      angry: 0,
      blink: 0,
    };

    // Load VRM
    const loader = new GLTFLoader();
    loader.register((parser) => new VRMLoaderPlugin(parser));

    loader.load(
      modelPath,
      (gltf) => {
        vrm = gltf.userData.vrm as VRM;
        if (!vrm) {
          setError('Invalid VRM model');
          setLoading(false);
          return;
        }

        VRMUtils.removeUnnecessaryVertices(gltf.scene);
        VRMUtils.removeUnnecessaryJoints(gltf.scene);
        vrm.scene.traverse((obj) => (obj.frustumCulled = false));

        scene.add(vrm.scene);
        setLoading(false);
        setError(null);

        // Setup audio analysis for lip-sync
        if (audioTrack?.publication.track) {
          try {
            const mediaStream = new MediaStream([audioTrack.publication.track.mediaStreamTrack]);
            audioContext = new AudioContext();
            analyser = audioContext.createAnalyser();
            analyser.fftSize = 256;
            analyser.smoothingTimeConstant = 0.85;
            dataArray = new Uint8Array(analyser.frequencyBinCount);
            audioSource = audioContext.createMediaStreamSource(mediaStream);
            audioSource.connect(analyser);
          } catch (err) {
            console.warn('Failed to setup audio analysis:', err);
          }
        }
      },
      undefined,
      (err: unknown) => {
        const errorMessage = err instanceof Error ? err.message : 'Failed to load VRM model';
        setError(errorMessage);
        setLoading(false);
      }
    );

    // Animation loop with comprehensive lip-sync and natural movements
    function animate() {
      requestAnimationFrame(animate);

      if (vrm) {
        const deltaTime = clock.getDelta();
        const elapsedTime = clock.elapsedTime;

        // Update VRM (required for proper animation)
        vrm.update(deltaTime);

        // Audio analysis for lip-sync
        let audioVolume = 0;
        let lowFreq = 0;
        let midFreq = 0;
        let highFreq = 0;

        if (analyser && dataArray && dataArray.length > 0) {
          try {
            analyser.getByteFrequencyData(dataArray);

            // Calculate volume (average of all frequencies)
            const sum = dataArray.reduce((acc, val) => acc + val, 0);
            audioVolume = sum / dataArray.length / 255;

            // Analyze frequency bands for more natural mouth shapes
            const third = Math.floor(dataArray.length / 3);
            lowFreq = dataArray.slice(0, third).reduce((a, b) => a + b, 0) / third / 255;
            midFreq = dataArray.slice(third, third * 2).reduce((a, b) => a + b, 0) / third / 255;
            highFreq = dataArray.slice(third * 2).reduce((a, b) => a + b, 0) / third / 255;

            // Detect speech with hysteresis to prevent flickering
            const speakingThreshold = isSpeaking ? 0.015 : 0.025;
            isSpeaking = audioVolume > speakingThreshold;
            targetSpeechIntensity = isSpeaking ? Math.min(audioVolume * 2, 1) : 0;
          } catch (err) {
            console.warn('Audio analysis error:', err);
          }
        }

        // Ultra smooth speech intensity transitions
        speechIntensity = smoothLerp(speechIntensity, targetSpeechIntensity, 0.15, deltaTime);

        // Smooth expression transitions
        if (isSpeaking && elapsedTime >= nextExpressionTime && expressionTransitionProgress >= 1) {
          previousExpression = currentExpression;
          const expressions = ['happy', 'surprised', 'thinking', 'relaxed'];
          currentExpression = expressions[Math.floor(Math.random() * expressions.length)];
          targetExpressionIntensity = 0.25 + Math.random() * 0.35;
          nextExpressionTime = elapsedTime + 2.5 + Math.random() * 3;
          expressionTransitionProgress = 0;
        } else if (!isSpeaking && currentExpression !== 'neutral') {
          previousExpression = currentExpression;
          currentExpression = 'neutral';
          targetExpressionIntensity = 0;
          expressionTransitionProgress = 0;
        }

        // Update expression transition progress
        if (expressionTransitionProgress < 1) {
          expressionTransitionProgress = Math.min(1, expressionTransitionProgress + deltaTime * 0.8);
        }

        // Smooth expression intensity
        const easedTransition = easeInOutQuad(expressionTransitionProgress);
        expressionIntensity = smoothLerp(expressionIntensity, targetExpressionIntensity, 0.08, deltaTime);

        // Natural blinking
        if (elapsedTime >= nextBlinkTime && !isSpeaking) {
          nextBlinkTime = elapsedTime + 2.5 + Math.random() * 3.5;
        }
        const blinkProgress = Math.max(0, 1 - Math.abs(elapsedTime - nextBlinkTime + 0.15) / 0.15);
        const smoothBlinkProgress = easeInOutCubic(blinkProgress);
        targetExpressionValues.blink = smoothBlinkProgress;

        // Smooth mouth movements
        if (isSpeaking) {
          targetMouthShapes.aa = lowFreq * 0.8;
          targetMouthShapes.ih = highFreq * 0.6;
          targetMouthShapes.ou = midFreq * 0.5;
          targetMouthShapes.oh = (lowFreq + midFreq) * 0.4;
        } else {
          targetMouthShapes.aa = 0;
          targetMouthShapes.ih = 0;
          targetMouthShapes.ou = 0;
          targetMouthShapes.oh = 0;
        }

        // Ultra smooth mouth shape transitions
        mouthShapes.aa = smoothLerp(mouthShapes.aa, targetMouthShapes.aa, 0.25, deltaTime);
        mouthShapes.ih = smoothLerp(mouthShapes.ih, targetMouthShapes.ih, 0.25, deltaTime);
        mouthShapes.ou = smoothLerp(mouthShapes.ou, targetMouthShapes.ou, 0.25, deltaTime);
        mouthShapes.oh = smoothLerp(mouthShapes.oh, targetMouthShapes.oh, 0.25, deltaTime);

        // Set expression targets based on current expression
        Object.keys(targetExpressionValues).forEach(key => {
          if (key !== 'blink') {
            targetExpressionValues[key as keyof typeof targetExpressionValues] = 0;
          }
        });

        if (isSpeaking) {
          if (currentExpression === 'happy') {
            targetExpressionValues.happy = expressionIntensity * 0.7 * easedTransition;
            targetExpressionValues.relaxed = expressionIntensity * 0.2 * easedTransition;
          } else if (currentExpression === 'surprised') {
            targetExpressionValues.surprised = expressionIntensity * 0.6 * easedTransition;
          } else if (currentExpression === 'thinking') {
            targetExpressionValues.neutral = expressionIntensity * 0.4 * easedTransition;
            targetExpressionValues.relaxed = expressionIntensity * 0.3 * easedTransition;
          } else if (currentExpression === 'relaxed') {
            targetExpressionValues.relaxed = expressionIntensity * 0.5 * easedTransition;
            targetExpressionValues.happy = expressionIntensity * 0.2 * easedTransition;
          } else {
            targetExpressionValues.happy = speechIntensity * 0.15;
          }
        }

        // Smooth all expression values
        Object.keys(expressionValues).forEach(key => {
          const k = key as keyof typeof expressionValues;
          expressionValues[k] = smoothLerp(expressionValues[k], targetExpressionValues[k], 0.1, deltaTime);
        });

        // Apply expressions to VRM
        if (vrm.expressionManager) {
          vrm.expressionManager.setValue('aa', Math.min(mouthShapes.aa, 1));
          vrm.expressionManager.setValue('ih', Math.min(mouthShapes.ih, 1));
          vrm.expressionManager.setValue('ou', Math.min(mouthShapes.ou, 1));
          vrm.expressionManager.setValue('oh', Math.min(mouthShapes.oh, 1));
          vrm.expressionManager.setValue('blink', expressionValues.blink);
          vrm.expressionManager.setValue('happy', expressionValues.happy);
          vrm.expressionManager.setValue('surprised', expressionValues.surprised);
          vrm.expressionManager.setValue('relaxed', expressionValues.relaxed);
          vrm.expressionManager.setValue('neutral', expressionValues.neutral);
        }

        if (vrm.humanoid) {
          // Base breathing animation (always active)
          const breathCycle = Math.sin(elapsedTime * 1.2) * 0.008;
          const swayCycle = Math.sin(elapsedTime * 0.6) * 0.006;

          // Enhanced breathing when speaking
          const speakingBreath = isSpeaking ? speechIntensity * 0.015 : 0;

          // Spine movement
          const spine = vrm.humanoid.getNormalizedBoneNode('spine');
          if (spine) {
            spine.rotation.x = breathCycle + speakingBreath;
            spine.rotation.z = swayCycle;
          }

          // Chest movement
          const chest = vrm.humanoid.getNormalizedBoneNode('chest');
          if (chest) {
            chest.rotation.x = (breathCycle + speakingBreath) * 0.5;
          }

          // Natural head and neck movements with smooth gesture transitions
          const head = vrm.humanoid.getNormalizedBoneNode('head');
          const neck = vrm.humanoid.getNormalizedBoneNode('neck');

          if (head) {
            if (isSpeaking) {
              // Trigger new gesture with smooth transition
              if (elapsedTime >= nextGestureTime) {
                previousGesture = currentGesture;
                previousHeadRotation.x = targetHeadRotation.x;
                previousHeadRotation.y = targetHeadRotation.y;
                previousHeadRotation.z = targetHeadRotation.z;
                
                currentGesture = Math.floor(Math.random() * 7);
                nextGestureTime = elapsedTime + 2 + Math.random() * 2;
                gesturePhase = 0;
                gestureTransitionProgress = 0;
              }

              gesturePhase += deltaTime;
              
              // Smooth gesture transition
              if (gestureTransitionProgress < 1) {
                gestureTransitionProgress = Math.min(1, gestureTransitionProgress + deltaTime * 1.5);
              }
              const easedGestureTransition = easeInOutQuad(gestureTransitionProgress);

              // Calculate target head rotation based on current gesture
              let newTargetHeadRotation = { x: 0, y: 0, z: 0 };
              let newTargetNeckRotation = { x: 0, y: 0, z: 0 };
              let newTargetEyebrow = 0;

              switch (currentGesture) {
                case 1: // Gentle nod
                  newTargetHeadRotation.x = Math.sin(gesturePhase * 2) * 0.08;
                  newTargetHeadRotation.y = Math.sin(elapsedTime * 0.3) * 0.015;
                  newTargetNeckRotation.x = Math.sin(gesturePhase * 2) * 0.025;
                  newTargetEyebrow = 0.18;
                  break;
                case 2: // Subtle tilt
                  newTargetHeadRotation.x = Math.sin(elapsedTime * 0.5) * 0.025;
                  newTargetHeadRotation.y = Math.sin(elapsedTime * 0.4) * 0.035;
                  newTargetHeadRotation.z = Math.sin(gesturePhase * 1) * 0.06;
                  newTargetNeckRotation.z = Math.sin(gesturePhase * 1) * 0.018;
                  newTargetEyebrow = 0.12;
                  break;
                case 3: // Gentle shake
                  newTargetHeadRotation.x = Math.sin(elapsedTime * 0.4) * 0.018;
                  newTargetHeadRotation.y = Math.sin(gesturePhase * 1.8) * 0.055;
                  newTargetNeckRotation.y = Math.sin(gesturePhase * 1.8) * 0.018;
                  newTargetEyebrow = 0.08;
                  break;
                case 4: // Forward lean
                  newTargetHeadRotation.x = 0.04 + Math.sin(elapsedTime * 0.6) * 0.015;
                  newTargetHeadRotation.y = Math.sin(elapsedTime * 0.4) * 0.025;
                  newTargetNeckRotation.x = 0.025;
                  newTargetEyebrow = 0.2;
                  break;
                case 5: // Side glance
                  newTargetHeadRotation.x = Math.sin(elapsedTime * 0.5) * 0.018;
                  newTargetHeadRotation.y = 0.05 + Math.sin(gesturePhase * 1.2) * 0.025;
                  newTargetHeadRotation.z = Math.sin(elapsedTime * 0.4) * 0.015;
                  newTargetNeckRotation.y = 0.018;
                  newTargetEyebrow = 0.08;
                  break;
                case 6: // Thoughtful look down
                  newTargetHeadRotation.x = 0.06 + Math.sin(elapsedTime * 0.5) * 0.02;
                  newTargetHeadRotation.y = Math.sin(elapsedTime * 0.3) * 0.02;
                  newTargetHeadRotation.z = Math.sin(elapsedTime * 0.4) * 0.01;
                  newTargetNeckRotation.x = 0.03;
                  newTargetEyebrow = 0.1;
                  break;
                default: // Subtle natural movement
                  newTargetHeadRotation.x = Math.sin(elapsedTime * 0.5) * 0.02;
                  newTargetHeadRotation.y = Math.sin(elapsedTime * 0.4) * 0.028;
                  newTargetHeadRotation.z = Math.sin(elapsedTime * 0.3) * 0.012;
                  newTargetNeckRotation.x = Math.sin(elapsedTime * 0.6) * 0.008;
                  newTargetNeckRotation.y = Math.sin(elapsedTime * 0.5) * 0.008;
                  newTargetEyebrow = 0.04;
              }

              // Blend between previous and new gesture
              targetHeadRotation.x = previousHeadRotation.x + (newTargetHeadRotation.x - previousHeadRotation.x) * easedGestureTransition;
              targetHeadRotation.y = previousHeadRotation.y + (newTargetHeadRotation.y - previousHeadRotation.y) * easedGestureTransition;
              targetHeadRotation.z = previousHeadRotation.z + (newTargetHeadRotation.z - previousHeadRotation.z) * easedGestureTransition;
              
              targetNeckRotation.x = newTargetNeckRotation.x;
              targetNeckRotation.y = newTargetNeckRotation.y;
              targetNeckRotation.z = newTargetNeckRotation.z;
              targetEyebrowIntensity = newTargetEyebrow;

              // Add speech-driven micro-movements
              targetHeadRotation.x += speechIntensity * Math.sin(elapsedTime * 2.2) * 0.012;
              targetHeadRotation.y += speechIntensity * Math.cos(elapsedTime * 1.8) * 0.01;
            } else {
              // Idle: very gentle looking around
              targetHeadRotation.x = Math.sin(elapsedTime * 0.35) * 0.035;
              targetHeadRotation.y = Math.sin(elapsedTime * 0.28) * 0.05;
              targetHeadRotation.z = Math.sin(elapsedTime * 0.22) * 0.012;
              targetNeckRotation.x = Math.sin(elapsedTime * 0.4) * 0.008;
              targetNeckRotation.y = Math.sin(elapsedTime * 0.3) * 0.008;
              targetNeckRotation.z = 0;
              targetEyebrowIntensity = 0;
              currentGesture = 0;
              gesturePhase = 0;
              gestureTransitionProgress = 1;
              nextGestureTime = elapsedTime + 2;
            }

            // Ultra smooth interpolation
            headRotation.x = smoothLerp(headRotation.x, targetHeadRotation.x, 0.08, deltaTime);
            headRotation.y = smoothLerp(headRotation.y, targetHeadRotation.y, 0.08, deltaTime);
            headRotation.z = smoothLerp(headRotation.z, targetHeadRotation.z, 0.08, deltaTime);

            head.rotation.x = headRotation.x;
            head.rotation.y = headRotation.y;
            head.rotation.z = headRotation.z;
          }

          // Neck movement
          if (neck) {
            neckRotation.x = smoothLerp(neckRotation.x, targetNeckRotation.x, 0.06, deltaTime);
            neckRotation.y = smoothLerp(neckRotation.y, targetNeckRotation.y, 0.06, deltaTime);
            neckRotation.z = smoothLerp(neckRotation.z, targetNeckRotation.z, 0.06, deltaTime);

            neck.rotation.x = neckRotation.x;
            neck.rotation.y = neckRotation.y;
            neck.rotation.z = neckRotation.z;
          }

          // Smooth eyebrow movements
          eyebrowIntensity = smoothLerp(eyebrowIntensity, targetEyebrowIntensity, 0.08, deltaTime);
          if (vrm.expressionManager && isSpeaking && currentExpression === 'neutral') {
            vrm.expressionManager.setValue('surprised', eyebrowIntensity * 0.15);
          }

          // Arm positioning and gestures
          const leftUpperArm = vrm.humanoid.getNormalizedBoneNode('leftUpperArm');
          const rightUpperArm = vrm.humanoid.getNormalizedBoneNode('rightUpperArm');
          const leftLowerArm = vrm.humanoid.getNormalizedBoneNode('leftLowerArm');
          const rightLowerArm = vrm.humanoid.getNormalizedBoneNode('rightLowerArm');
          const leftHand = vrm.humanoid.getNormalizedBoneNode('leftHand');
          const rightHand = vrm.humanoid.getNormalizedBoneNode('rightHand');

          if (isSpeaking) {
            const baseGestureIntensity = Math.min(speechIntensity * 0.25, 0.15);
            const emphasisMultiplier = speechIntensity > 0.5 ? 1.6 : 1.1;
            const gestureIntensity = baseGestureIntensity * emphasisMultiplier;

            // Smooth arm movements
            targetLeftArmRotation.x = Math.sin(elapsedTime * 1.1) * gestureIntensity * 1.2;
            targetLeftArmRotation.y = Math.cos(elapsedTime * 0.85) * gestureIntensity * 0.7;
            targetLeftArmRotation.z = -1.2 + Math.sin(elapsedTime * 0.75) * gestureIntensity * 0.6;

            targetRightArmRotation.x = Math.sin(elapsedTime * 1.1 + 1.5) * gestureIntensity * 1.2;
            targetRightArmRotation.y = -Math.cos(elapsedTime * 0.85) * gestureIntensity * 0.7;
            targetRightArmRotation.z = 1.2 - Math.sin(elapsedTime * 0.75 + 1.5) * gestureIntensity * 0.6;

            // Smooth lower arm movement
            const lowerArmIntensity = gestureIntensity * 1.1;
            targetLeftLowerArmRotation.x = -0.2 + Math.sin(elapsedTime * 1.4) * lowerArmIntensity;
            targetRightLowerArmRotation.x = -0.2 + Math.cos(elapsedTime * 1.4) * lowerArmIntensity;

            // Smooth hand movements
            targetHandRotation.left.x = Math.sin(elapsedTime * 1.6) * gestureIntensity * 0.4;
            targetHandRotation.left.y = Math.cos(elapsedTime * 1.3) * gestureIntensity * 0.35;
            targetHandRotation.left.z = Math.sin(elapsedTime * 1.1) * gestureIntensity * 0.35;

            targetHandRotation.right.x = Math.sin(elapsedTime * 1.6 + 1) * gestureIntensity * 0.4;
            targetHandRotation.right.y = -Math.cos(elapsedTime * 1.3) * gestureIntensity * 0.35;
            targetHandRotation.right.z = Math.cos(elapsedTime * 1.1) * gestureIntensity * 0.35;
          } else {
            // Relaxed idle pose
            targetLeftArmRotation.x = Math.sin(elapsedTime * 0.65) * 0.012;
            targetLeftArmRotation.y = 0;
            targetLeftArmRotation.z = -1.2;

            targetRightArmRotation.x = Math.sin(elapsedTime * 0.65 + Math.PI) * 0.012;
            targetRightArmRotation.y = 0;
            targetRightArmRotation.z = 1.2;

            targetLeftLowerArmRotation.x = -0.2;
            targetRightLowerArmRotation.x = -0.2;

            targetHandRotation.left.x = 0;
            targetHandRotation.left.y = 0;
            targetHandRotation.left.z = 0;
            targetHandRotation.right.x = 0;
            targetHandRotation.right.y = 0;
            targetHandRotation.right.z = 0;
          }

          // Ultra smooth arm interpolation
          leftArmRotation.x = smoothLerp(leftArmRotation.x, targetLeftArmRotation.x, 0.1, deltaTime);
          leftArmRotation.y = smoothLerp(leftArmRotation.y, targetLeftArmRotation.y, 0.1, deltaTime);
          leftArmRotation.z = smoothLerp(leftArmRotation.z, targetLeftArmRotation.z, 0.1, deltaTime);

          rightArmRotation.x = smoothLerp(rightArmRotation.x, targetRightArmRotation.x, 0.1, deltaTime);
          rightArmRotation.y = smoothLerp(rightArmRotation.y, targetRightArmRotation.y, 0.1, deltaTime);
          rightArmRotation.z = smoothLerp(rightArmRotation.z, targetRightArmRotation.z, 0.1, deltaTime);

          leftLowerArmRotation.x = smoothLerp(leftLowerArmRotation.x, targetLeftLowerArmRotation.x, 0.1, deltaTime);
          rightLowerArmRotation.x = smoothLerp(rightLowerArmRotation.x, targetRightLowerArmRotation.x, 0.1, deltaTime);

          handRotation.left.x = smoothLerp(handRotation.left.x, targetHandRotation.left.x, 0.1, deltaTime);
          handRotation.left.y = smoothLerp(handRotation.left.y, targetHandRotation.left.y, 0.1, deltaTime);
          handRotation.left.z = smoothLerp(handRotation.left.z, targetHandRotation.left.z, 0.1, deltaTime);
          handRotation.right.x = smoothLerp(handRotation.right.x, targetHandRotation.right.x, 0.1, deltaTime);
          handRotation.right.y = smoothLerp(handRotation.right.y, targetHandRotation.right.y, 0.1, deltaTime);
          handRotation.right.z = smoothLerp(handRotation.right.z, targetHandRotation.right.z, 0.1, deltaTime);

          // Apply smoothed rotations
          if (leftUpperArm) {
            leftUpperArm.rotation.x = leftArmRotation.x;
            leftUpperArm.rotation.y = leftArmRotation.y;
            leftUpperArm.rotation.z = leftArmRotation.z;
          }
          if (rightUpperArm) {
            rightUpperArm.rotation.x = rightArmRotation.x;
            rightUpperArm.rotation.y = rightArmRotation.y;
            rightUpperArm.rotation.z = rightArmRotation.z;
          }
          if (leftLowerArm) {
            leftLowerArm.rotation.x = leftLowerArmRotation.x;
          }
          if (rightLowerArm) {
            rightLowerArm.rotation.x = rightLowerArmRotation.x;
          }
          if (leftHand) {
            leftHand.rotation.x = handRotation.left.x;
            leftHand.rotation.y = handRotation.left.y;
            leftHand.rotation.z = handRotation.left.z;
          }
          if (rightHand) {
            rightHand.rotation.x = handRotation.right.x;
            rightHand.rotation.y = handRotation.right.y;
            rightHand.rotation.z = handRotation.right.z;
          }

          // Smooth shoulder movement
          const leftShoulder = vrm.humanoid.getNormalizedBoneNode('leftShoulder');
          const rightShoulder = vrm.humanoid.getNormalizedBoneNode('rightShoulder');
          
          if (isSpeaking && speechIntensity > 0.35) {
            if (leftShoulder) {
              const targetShoulderZ = Math.sin(elapsedTime * 1.3) * 0.03;
              const targetShoulderY = Math.cos(elapsedTime * 1.1) * 0.015;
              leftShoulder.rotation.z = smoothLerp(leftShoulder.rotation.z, targetShoulderZ, 0.08, deltaTime);
              leftShoulder.rotation.y = smoothLerp(leftShoulder.rotation.y, targetShoulderY, 0.08, deltaTime);
            }
            if (rightShoulder) {
              const targetShoulderZ = -Math.sin(elapsedTime * 1.3) * 0.03;
              const targetShoulderY = -Math.cos(elapsedTime * 1.1) * 0.015;
              rightShoulder.rotation.z = smoothLerp(rightShoulder.rotation.z, targetShoulderZ, 0.08, deltaTime);
              rightShoulder.rotation.y = smoothLerp(rightShoulder.rotation.y, targetShoulderY, 0.08, deltaTime);
            }
          } else {
            if (leftShoulder) {
              leftShoulder.rotation.z = smoothLerp(leftShoulder.rotation.z, 0, 0.08, deltaTime);
              leftShoulder.rotation.y = smoothLerp(leftShoulder.rotation.y, 0, 0.08, deltaTime);
            }
            if (rightShoulder) {
              rightShoulder.rotation.z = smoothLerp(rightShoulder.rotation.z, 0, 0.08, deltaTime);
              rightShoulder.rotation.y = smoothLerp(rightShoulder.rotation.y, 0, 0.08, deltaTime);
            }
          }

          // Additional natural body sway
          const hips = vrm.humanoid.getNormalizedBoneNode('hips');
          if (hips) {
            const hipSway = Math.sin(elapsedTime * 0.5) * 0.005;
            hips.rotation.y = hipSway;
          }

          // Finger animations for more natural look
          const fingerBones = [
            'leftThumbProximal', 'leftThumbIntermediate', 'leftThumbDistal',
            'leftIndexProximal', 'leftIndexIntermediate', 'leftIndexDistal',
            'leftMiddleProximal', 'leftMiddleIntermediate', 'leftMiddleDistal',
            'leftRingProximal', 'leftRingIntermediate', 'leftRingDistal',
            'leftLittleProximal', 'leftLittleIntermediate', 'leftLittleDistal',
            'rightThumbProximal', 'rightThumbIntermediate', 'rightThumbDistal',
            'rightIndexProximal', 'rightIndexIntermediate', 'rightIndexDistal',
            'rightMiddleProximal', 'rightMiddleIntermediate', 'rightMiddleDistal',
            'rightRingProximal', 'rightRingIntermediate', 'rightRingDistal',
            'rightLittleProximal', 'rightLittleIntermediate', 'rightLittleDistal'
          ];

          if (isSpeaking && speechIntensity > 0.3) {
            fingerBones.forEach((boneName, index) => {
              const bone = vrm.humanoid.getNormalizedBoneNode(boneName as any);
              if (bone) {
                const fingerCurl = Math.sin(elapsedTime * 1.5 + index * 0.2) * speechIntensity * 0.15;
                bone.rotation.z = smoothLerp(bone.rotation.z, fingerCurl, 0.1, deltaTime);
              }
            });
          } else {
            fingerBones.forEach((boneName) => {
              const bone = vrm.humanoid.getNormalizedBoneNode(boneName as any);
              if (bone) {
                bone.rotation.z = smoothLerp(bone.rotation.z, 0, 0.1, deltaTime);
              }
            });
          }
        }
      }

      renderer.render(scene, camera);
    }
    animate();

    // Handle resize
    function handleResize() {
      const newWidth = container.clientWidth;
      const newHeight = container.clientHeight;
      camera.aspect = newWidth / newHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(newWidth, newHeight);
    }
    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      controls.dispose();

      // Cleanup audio context
      if (audioSource) {
        audioSource.disconnect();
      }
      if (audioContext) {
        audioContext.close();
      }

      if (vrm) {
        VRMUtils.deepDispose(vrm.scene);
      }

      scene.traverse((obj) => {
        if (obj instanceof THREE.Mesh) {
          obj.geometry?.dispose();
          if (Array.isArray(obj.material)) {
            obj.material.forEach((mat) => mat.dispose());
          } else {
            obj.material?.dispose();
          }
        }
      });

      renderer.dispose();
      container.removeChild(renderer.domElement);
    };
  }, [modelPath, audioTrack]);

  return (
    <div ref={containerRef} className="relative h-full w-full">
      {loading && (
        <div className="text-foreground/70 absolute inset-0 flex items-center justify-center bg-black/50">
          Loading Avatar...
        </div>
      )}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/50 text-red-500">
          Error: {error}
        </div>
      )}
    </div>
  );
}