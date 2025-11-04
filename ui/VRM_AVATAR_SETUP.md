# VRM 3D Avatar Setup Guide

## Overview

This guide explains how to use the VRM 3D avatar feature in your React UI.

## Installation

1. **Install Dependencies**

   Run the following command in the `ui` directory:

   ```bash
   pnpm install
   ```

   This will install:
   - `three` - 3D graphics library
   - `@pixiv/three-vrm` - VRM model loader
   - `@react-three/fiber` - React renderer for three.js
   - `@react-three/drei` - Useful helpers for R3F

## Setup

2. **Add Your VRM Model**

   Place your VRM model file in the public folder:

   ```
   ui/public/models/avatar.vrm
   ```

   Create the `models` directory if it doesn't exist:

   ```bash
   mkdir ui/public/models
   ```

## Usage

3. **Toggle the Avatar**
   - Click the **user icon button** in the control bar at the bottom of the screen
   - The 3D avatar will appear in the center of the screen
   - Click the button again to hide the avatar

4. **Interact with the Avatar**
   - **Rotate**: Click and drag to rotate the avatar
   - **Zoom**: Scroll to zoom in/out
   - **Pan**: Right-click and drag to pan the view

## Features

- ✅ Automatic loading indicator
- ✅ Error handling with user-friendly messages
- ✅ Automatic blinking animation
- ✅ High-resolution rendering with proper lighting
- ✅ OrbitControls for intuitive camera control
- ✅ Smooth show/hide animations
- ✅ Non-blocking UI (avatar doesn't interfere with other elements)

## Customization

### Change Avatar Model Path

Edit `session-view.tsx` to specify a custom path:

```tsx
<VRMAvatar visible={avatarOpen} modelPath="/models/my-custom-avatar.vrm" />
```

### Adjust Camera Position

Edit `vrm-avatar.tsx` to change the initial camera position:

```tsx
<Canvas
  camera={{ position: [0, 1.4, 1.5], fov: 30 }}  // Adjust these values
  // ...
>
```

### Modify Lighting

Edit the lighting setup in `vrm-avatar.tsx`:

```tsx
<ambientLight intensity={0.8} />  // Adjust intensity
<directionalLight position={[1, 2, 3]} intensity={1.5} castShadow />
```

## Troubleshooting

### Avatar Not Loading

1. **Check file path**: Ensure `avatar.vrm` exists in `ui/public/models/`
2. **Check console**: Open browser DevTools (F12) and look for error messages
3. **Verify VRM format**: Ensure your file is a valid VRM 1.0 model

### Performance Issues

- Use optimized VRM models (lower polygon count)
- Reduce texture resolution if needed
- Close the avatar when not in use

### Styling Issues

If the avatar appears too small/large:

- Adjust the `h-[80vh] w-[80vw]` classes in `vrm-avatar.tsx`
- Modify the camera `fov` value (lower = more zoomed in)

## File Structure

```
ui/
├── components/
│   └── app/
│       ├── vrm-avatar.tsx          # Main VRM component
│       ├── session-view.tsx        # Integrated avatar here
│       └── agent-control-bar/
│           └── agent-control-bar.tsx  # Added toggle button
├── public/
│   └── models/
│       └── avatar.vrm              # Your VRM model file
└── package.json                    # Dependencies added
```

## Technical Details

### Component Architecture

- **VRMAvatar**: Main component that handles loading and rendering
- **VRMModel**: Internal component that manages the VRM instance
- **AnimatePresence**: Handles smooth show/hide transitions

### Blinking Animation

The avatar automatically blinks every 3-5 seconds using a sine wave function:

```tsx
const blinkCycle = Math.sin(t * 0.5) * 0.5 + 0.5;
const shouldBlink = blinkCycle > 0.95;
```

### Memory Management

- VRM resources are properly disposed when component unmounts
- Uses `VRMUtils.deepDispose()` to clean up scene objects

## Next Steps

Future enhancements you can add:

- Lip-sync animation based on audio input
- Facial expressions based on sentiment
- Body animations and gestures
- Multiple avatar support
- Avatar customization UI

## Support

For VRM format specifications, visit: https://vrm.dev/en/
For three.js documentation, visit: https://threejs.org/docs/
