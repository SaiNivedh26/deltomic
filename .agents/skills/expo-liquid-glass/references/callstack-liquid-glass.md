# @callstack/liquid-glass

Third-party Liquid Glass library from Callstack. Works in both vanilla React Native and Expo.

## Setup

```bash
npm install @callstack/liquid-glass
```

For Expo projects, prefer:

```bash
npx expo install @callstack/liquid-glass
```

## Compatibility

- React Native `>= 0.80.0`
- iOS/tvOS (Liquid Glass itself is iOS-family only)
- Liquid Glass effects require iOS/tvOS 26+
- In Expo workflows, prefer a development build for reliable testing

## Components

### LiquidGlassView

Drop-in glass panel component. Wrap any content to render it on glass.

```tsx
import { LiquidGlassView, isLiquidGlassAvailable } from '@callstack/liquid-glass';
import { Text, View } from 'react-native';

function GlassCard() {
  return (
    <LiquidGlassView
      style={[
        { width: 200, height: 100, borderRadius: 20 },
        !isLiquidGlassAvailable() && { backgroundColor: 'rgba(255,255,255,0.5)' },
      ]}
      interactive
      effect="clear"
    >
      <Text style={{ fontWeight: '600', color: 'white' }}>Hello</Text>
    </LiquidGlassView>
  );
}
```

**Props:**
- `interactive` (boolean): Touch-response animations (scale, bounce, shimmer)
- `effect`: `'clear'` (high transparency) | `'regular'` (medium transparency)
- `tintColor` (ColorValue): Overlay tint
- `colorScheme`: `'light'` | `'dark'` | `'system'`
- Inherits all `ViewProps`

### LiquidGlassContainerView

Groups glass elements for morphing/merging when close together.

```tsx
import { LiquidGlassContainerView, LiquidGlassView } from '@callstack/liquid-glass';

function MergingExample() {
  return (
    <LiquidGlassContainerView spacing={20}>
      <LiquidGlassView style={{ width: 100, height: 100, borderRadius: 50 }}>
        <Text>A</Text>
      </LiquidGlassView>
      <LiquidGlassView style={{ width: 100, height: 100, borderRadius: 50 }}>
        <Text>B</Text>
      </LiquidGlassView>
    </LiquidGlassContainerView>
  );
}
```

**Props:**
- `spacing`: Distance (points) at which glass elements begin merging

## Platform Detection

```tsx
import { isLiquidGlassAvailable } from '@callstack/liquid-glass';

if (isLiquidGlassAvailable()) {
  // Use LiquidGlassView
} else {
  // Fallback to BlurView or semi-transparent View
}
```

Falls back to normal `View` rendering when Liquid Glass APIs are unavailable.

## When to Choose This Over expo-glass-effect

- Non-Expo React Native projects
- Need `colorScheme` prop for explicit light/dark control
- Prefer Callstack's API surface
- Already using other Callstack libraries

For Expo projects, `expo-glass-effect` is the official recommendation.
