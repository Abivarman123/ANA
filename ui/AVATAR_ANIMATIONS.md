# VRM Avatar Animation System

## Overview
Comprehensive natural animation system with real-time lip-sync, smooth interpolated movements, and human-like body language for the VRM avatar.

## Features

### 1. **Audio-Driven Lip-Sync**
- Real-time audio analysis using Web Audio API
- Frequency band analysis (low, mid, high) for natural mouth shapes
- Viseme-based mouth movements:
  - **aa**: Open mouth (low frequencies)
  - **ih**: Narrow mouth (high frequencies)
  - **ou**: Rounded mouth (mid frequencies)
  - **oh**: Rounded open mouth (combined frequencies)
- Smooth transitions between speaking and idle states

### 2. **Smooth Interpolation System**
All movements use linear interpolation (lerp) for fluid, natural transitions:
- **Head movements**: 0.05 lerp factor (very smooth)
- **Arm movements**: 0.08 lerp factor (smooth)
- **No sudden jumps**: All rotations transition gradually
- **Prevents jitter**: Smooth blending between animation states

### 3. **Natural Head Movements**
When speaking:
- **Gentle nodding**: Vertical head movement (reduced intensity)
- **Subtle tilting**: Side-to-side head tilt for expression
- **Gentle shaking**: Horizontal head movement
- **Micro-movements**: Very subtle speech-driven adjustments
- **Timed gestures**: New gesture every 2-4 seconds (not random)

When idle:
- Very gentle looking around
- Minimal vertical and horizontal movements
- Smooth, continuous motion

### 4. **Body Language & Gestures**
When speaking:
- **Gentle arm gestures**: Reduced intensity (max 0.1 radians), slower movement (0.6-0.8 Hz)
- **Smooth hand movements**: Subtle articulation with interpolation
- **Minimal shoulder movement**: Only during strong emphasis (>0.6 intensity)
- **Enhanced breathing**: More pronounced chest/spine movement
- **Coordinated movements**: Arms move in natural opposition

When idle:
- Relaxed arm positioning (not T-pose)
- Very gentle breathing animation
- Minimal body sway
- Smooth transitions to speaking pose

### 5. **Facial Expressions**
- **Natural blinking**: Random intervals (2-5 seconds), pauses during speech
- **Subtle smile**: Appears when speaking
- **Expression smoothing**: Gradual transitions between expressions

## Technical Implementation

### Audio Analysis
```typescript
- AudioContext with AnalyserNode
- FFT size: 256
- Smoothing: 0.8
- Frequency bands analyzed for different mouth shapes
- Volume threshold: 0.02 for speech detection
```

### Animation Parameters
- **Speech intensity**: Smoothed with 0.3 lerp factor
- **Gesture intensity**: 0.3 * speech intensity
- **Breathing cycle**: 1.5 Hz sine wave
- **Sway cycle**: 0.8 Hz sine wave
- **Random gestures**: 1% chance per frame when speaking

### Bone Hierarchy
Animated bones:
- Spine, Chest (breathing)
- Head (gestures, looking)
- Left/Right Upper Arms (gestures)
- Left/Right Lower Arms (gestures)
- Left/Right Hands (articulation)
- Left/Right Shoulders (emphasis)

## Usage

The avatar automatically animates when:
1. Audio track is provided via `audioTrack` prop
2. Agent is speaking (audio volume > threshold)
3. In idle state (subtle ambient animations)

## Performance

- Efficient frequency analysis (256 FFT bins)
- Smooth 60 FPS animation loop
- Proper cleanup on unmount
- Audio context disposed correctly

## Customization

Adjust these values in `vrm-avatar-scene.tsx`:

```typescript
// Speech detection threshold
audioVolume > 0.02

// Gesture intensity
speechIntensity * 0.3

// Mouth shape multipliers
lowFreq * 0.8  // aa
highFreq * 0.6 // ih
midFreq * 0.5  // ou

// Animation speeds
elapsedTime * 1.5  // breathing
elapsedTime * 0.8  // sway
```

## Notes

- Requires VRM model with expression support (aa, ih, ou, oh, blink, happy)
- Requires VRM model with proper bone hierarchy
- Audio analysis only works when audioTrack is provided
- Falls back to idle animations when no audio
