# @expo/ui SwiftUI Integration

Full guide for using SwiftUI components with Liquid Glass in Expo apps.

## Table of Contents
- [Setup](#setup)
- [Host Component](#host-component)
- [Available Components](#available-components)
- [Glass Modifier](#glass-modifier)
- [Layout with HStack/VStack](#layout)
- [Modifiers System](#modifiers-system)
- [Patterns](#patterns)

## Setup

```bash
npx expo install @expo/ui
```

Requirements:
- SDK 54+
- Xcode 26+ (for glass modifiers)
- Development build required (not available in Expo Go)
- iOS, macOS, tvOS only (Android/web not yet supported)

Status: **Beta**. API surface can change between SDK releases.

## Host Component

`Host` is the bridge from React Native (UIKit) to SwiftUI. It uses `UIHostingController`
under the hood. Think of it like `<svg>` in the DOM or `<Canvas>` in react-native-skia.

```tsx
import { Host, Button } from '@expo/ui/swift-ui';

function Example() {
  return (
    <Host style={{ width: 200, height: 50 }}>
      <Button onPress={() => console.log('tap')}>Action</Button>
    </Host>
  );
}
```

**Host props:**
- `style`: Standard React Native styles (flex, dimensions, positioning)
- `matchContents`: Boolean - sizes Host to fit child SwiftUI content

**Layout rule:** Flexbox styles apply only to the `Host` container itself. Inside the Host,
use SwiftUI layout primitives (`HStack`, `VStack`, `Spacer`) instead of Yoga/flexbox.
Do NOT set layout props directly on wrapped SwiftUI views - this conflicts with SwiftUI
and causes undefined behavior.

## Available Components

Import from `@expo/ui/swift-ui`:

| Component | Key Props | Notes |
|---|---|---|
| `Button` | `variant` ("default", "borderless"), `onPress` | |
| `Text` | children (string) | SwiftUI Text, not RN Text |
| `HStack` | children | Horizontal layout |
| `VStack` | children | Vertical layout |
| `Spacer` | | Flexible space |
| `Form` | children | iOS settings-style form |
| `Section` | children | Group within Form |
| `Image` | | SwiftUI Image |
| `Toggle` | `checked`, `onValueChange`, `label`, `variant` ("switch", "checkbox") | |
| `Picker` | `options`, `selectedIndex`, `variant` ("segmented", "wheel", "menu") | |
| `Slider` | `value`, `onValueChange` | |
| `TextField` | `defaultValue`, `onChangeText`, `autocorrection` | |
| `DateTimePicker` | `displayedComponents`, `initialDate`, `variant`, `onDateSelected` | |
| `ColorPicker` | `label`, `selection`, `onValueChanged` | |
| `ContextMenu` | Nested `Items`/`Trigger` | |
| `BottomSheet` | `isOpened`, `onIsOpenedChange` | |
| `List` | `scrollEnabled`, `editModeEnabled`, etc. | Reorderable, deletable |
| `CircularProgress` | `progress`, `color` | |
| `LinearProgress` | `progress`, `color` | |
| `Gauge` | `min`, `max`, `current`, `color`, `type` | |

## Glass Modifier

Apply liquid glass to any SwiftUI component via the `glassEffect` modifier.

```tsx
import { Host, Text, VStack } from '@expo/ui/swift-ui';
import { glassEffect, padding, frame } from '@expo/ui/swift-ui/modifiers';

function GlassCard() {
  return (
    <Host style={{ width: 300, height: 200 }}>
      <VStack
        modifiers={[
          padding({ all: 20 }),
          frame({ maxWidth: 280 }),
          glassEffect({ glass: { variant: 'regular' } }),
        ]}
      >
        <Text>Glass Surface</Text>
      </VStack>
    </Host>
  );
}
```

### Glass variants

```tsx
// Regular - medium transparency, standard controls
glassEffect({ glass: { variant: 'regular' } })

// Clear - high transparency, media-rich backgrounds
glassEffect({ glass: { variant: 'clear' } })

// With tint color
glassEffect({ glass: { variant: 'regular', tint: '#007AFF' } })

// Interactive - enables touch animations (scale, bounce, shimmer)
glassEffect({ glass: { variant: 'regular', interactive: true } })
```

### Coordinated Glass Transitions

Use `Namespace` + `glassEffectID` to coordinate glass identity across transitions:

```tsx
import { Host, Namespace, Text } from '@expo/ui/swift-ui';
import { glassEffect, glassEffectID } from '@expo/ui/swift-ui/modifiers';

const glassNamespace = new Namespace('main');

<Host style={{ width: 220, height: 56 }}>
  <Text
    modifiers={[
      glassEffect({ glass: { variant: 'regular' } }),
      glassEffectID({ id: 'search-chip', in: glassNamespace }),
    ]}
  >
    Search
  </Text>
</Host>;
```

### Glass + Mesh Gradient (Liquid Glass Text)

Combine `expo-mesh-gradient` with `glassEffect` for liquid glass text:

```tsx
import { Host, Text } from '@expo/ui/swift-ui';
import { glassEffect, padding } from '@expo/ui/swift-ui/modifiers';
import { MeshGradient } from 'expo-mesh-gradient';

function GlassTitle() {
  return (
    <View style={{ flex: 1 }}>
      <MeshGradient
        style={StyleSheet.absoluteFill}
        points={[/* mesh gradient points */]}
        colors={[/* gradient colors */]}
      />
      <Host style={{ position: 'absolute', top: 100, alignSelf: 'center' }}>
        <Text
          modifiers={[
            padding({ all: 16 }),
            glassEffect({ glass: { variant: 'clear' } }),
          ]}
        >
          Liquid Glass Text
        </Text>
      </Host>
    </View>
  );
}
```

## Layout

SwiftUI layout inside Host uses stacks, not flexbox:

```tsx
import { Host, HStack, VStack, Text, Spacer } from '@expo/ui/swift-ui';
import { padding, glassEffect } from '@expo/ui/swift-ui/modifiers';

function GlassToolbar() {
  return (
    <Host style={{ width: '100%', height: 60 }}>
      <HStack modifiers={[padding({ horizontal: 16 }), glassEffect({ glass: { variant: 'regular' } })]}>
        <Text>Left</Text>
        <Spacer />
        <Text>Right</Text>
      </HStack>
    </Host>
  );
}
```

## Modifiers System

Import from `@expo/ui/swift-ui/modifiers`. Pass as arrays to the `modifiers` prop:

```tsx
modifiers={[
  padding({ all: 16 }),
  frame({ maxWidth: 300, minHeight: 50 }),
  glassEffect({ glass: { variant: 'regular' } }),
]}
```

Modifiers are applied in order (like SwiftUI modifier chains).

## Patterns

### Mixing RN and SwiftUI

React Native components can be nested as JSX children within Host:

```tsx
<Host style={{ flex: 1 }}>
  <VStack>
    <Text>SwiftUI Text</Text>
    {/* RN View as child - use with care */}
  </VStack>
</Host>
```

### Conditional Glass

```tsx
import { isGlassEffectAPIAvailable } from 'expo-glass-effect';

function AdaptiveCard() {
  const mods = [padding({ all: 16 })];
  if (isGlassEffectAPIAvailable()) {
    mods.push(glassEffect({ glass: { variant: 'regular' } }));
  }

  return (
    <Host style={{ width: 200, height: 100 }}>
      <VStack modifiers={mods}>
        <Text>Content</Text>
      </VStack>
    </Host>
  );
}
```
