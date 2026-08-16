# Native Tabs with Liquid Glass

Expo Router v6 native tabs that automatically render with iOS 26 liquid glass.

## Table of Contents
- [Setup](#setup)
- [Basic Usage](#basic-usage)
- [Tab Bar Items](#tab-bar-items)
- [SDK 54 to 55 Migration](#sdk-54-to-55-migration)
- [Liquid Glass Colors](#liquid-glass-colors)
- [iOS 26 Features](#ios-26-features)
- [Advanced Configuration](#advanced-configuration)
- [Known Issues](#known-issues)
- [Limitations](#limitations)

## Setup

Requires Expo Router v6 with unstable native tabs (alpha API). Syntax differs by SDK.

```bash
# current unstable channel
npx expo install expo-router@next
```

File structure:
```
app/
  _layout.tsx        # NativeTabs layout
  (tabs)/
    index.tsx        # Home tab
    search.tsx       # Search tab
    account.tsx      # Account tab
```

## Basic Usage

```tsx
import { NativeTabs } from 'expo-router/unstable-native-tabs';

export default function TabLayout() {
  return (
    <NativeTabs>
      <NativeTabs.Trigger name="index">
        <NativeTabs.Trigger.TabBarIcon
          ios={{ default: 'house', selected: 'house.fill' }}
          androidIconName="home"
        />
        <NativeTabs.Trigger.TabBarLabel>Home</NativeTabs.Trigger.TabBarLabel>
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="search">
        <NativeTabs.Trigger.TabBarIcon
          ios={{ default: 'magnifyingglass', selected: 'magnifyingglass' }}
          androidIconName="search"
        />
        <NativeTabs.Trigger.TabBarLabel>Search</NativeTabs.Trigger.TabBarLabel>
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="account">
        <NativeTabs.Trigger.TabBarIcon
          ios={{ default: 'person', selected: 'person.fill' }}
          androidIconName="person"
        />
        <NativeTabs.Trigger.TabBarLabel>Account</NativeTabs.Trigger.TabBarLabel>
      </NativeTabs.Trigger>
    </NativeTabs>
  );
}
```

On iOS 26, the tab bar automatically uses liquid glass material.

## Tab Bar Items

### Icon (SDK 55+ compound API)

```tsx
// SF Symbols (iOS) + Material Symbols (Android)
<NativeTabs.Trigger.TabBarIcon
  ios={{ default: 'house', selected: 'house.fill' }}
  androidIconName="home"
/>

// Custom image
<NativeTabs.Trigger.TabBarIcon src={require('./assets/icon.png')} />

// State variants (different icons for selected/default)
<NativeTabs.Trigger.TabBarIcon
  ios={{ default: 'house', selected: 'house.fill' }}
  androidIconName="home"
/>

// Rendering mode (iOS)
<NativeTabs.Trigger.TabBarIcon
  ios={{ default: 'star.fill', selected: 'star.fill' }}
  renderingMode="template"
/>
```

### Label

```tsx
<NativeTabs.Trigger.TabBarLabel>Home</NativeTabs.Trigger.TabBarLabel>

// Hidden label (tab still works, just no text)
<NativeTabs.Trigger.TabBarLabel hidden>Home</NativeTabs.Trigger.TabBarLabel>
```

### Badge

```tsx
// Numeric badge
<NativeTabs.Trigger.TabBarBadge>3</NativeTabs.Trigger.TabBarBadge>

// Presence indicator (empty badge)
<NativeTabs.Trigger.TabBarBadge />
```

Legacy aliases on SDK 54:
- `Trigger.Icon`
- `Trigger.Label`
- `Trigger.Badge`

## SDK 54 to 55 Migration

Update trigger subcomponents:

```tsx
// SDK 54
<NativeTabs.Trigger.Icon sf="house.fill" md="home" />
<NativeTabs.Trigger.Label>Home</NativeTabs.Trigger.Label>

// SDK 55
<NativeTabs.Trigger.TabBarIcon
  ios={{ default: 'house', selected: 'house.fill' }}
  androidIconName="home"
/>
<NativeTabs.Trigger.TabBarLabel>Home</NativeTabs.Trigger.TabBarLabel>
```

`Icon` still works as an alias in SDK 55 for compatibility, but prefer `TabBarIcon`.

## Liquid Glass Colors

Liquid glass automatically adapts colors based on light/dark background. Use `DynamicColorIOS`
for proper adaptation:

```tsx
import { DynamicColorIOS } from 'react-native';

<NativeTabs
  labelStyle={{
    color: DynamicColorIOS({
      dark: 'white',
      light: 'black',
    }),
  }}
  tintColor={DynamicColorIOS({
    dark: 'white',
    light: 'black',
  })}
>
```

## iOS 26 Features

### Separate Search Tab

```tsx
<NativeTabs.Trigger name="search" role="search">
  <NativeTabs.Trigger.TabBarLabel>Search</NativeTabs.Trigger.TabBarLabel>
  <NativeTabs.Trigger.TabBarIcon
    ios={{ default: 'magnifyingglass', selected: 'magnifyingglass' }}
    androidIconName="search"
  />
</NativeTabs.Trigger>
```

### Search Bar in Tab Header

Wrap tab content in a Stack navigator with search bar options:

```tsx
// app/(tabs)/search/_layout.tsx
import { Stack } from 'expo-router';

export default function SearchLayout() {
  return (
    <Stack>
      <Stack.Screen
        name="index"
        options={{
          headerSearchBarOptions: {
            placeholder: 'Search...',
            onChangeText: (e) => { /* handle search */ },
          },
        }}
      />
    </Stack>
  );
}
```

### Minimize Tab Bar on Scroll

```tsx
<NativeTabs minimizeBehavior="onScrollDown">
  {/* tabs */}
</NativeTabs>
```

### Bottom Accessory (Mini Player)

Floating view above the tab bar for persistent controls:

```tsx
<NativeTabs
  bottomAccessory={
    <View style={{ height: 60, padding: 8 }}>
      <Text>Now Playing: Song Title</Text>
    </View>
  }
>
  {/* tabs */}
</NativeTabs>
```

## Advanced Configuration

### Per-Tab Headers with Stack Navigators

Each tab can have its own Stack navigator for per-screen header configuration:

```tsx
// app/(tabs)/home/_layout.tsx
import { Stack } from 'expo-router';

export default function HomeLayout() {
  return (
    <Stack
      screenOptions={{
        headerLargeTitle: true,
        headerBlurEffect: 'systemChromeMaterialDark',
        headerTransparent: true,
      }}
    >
      <Stack.Screen name="index" options={{ title: 'Home' }} />
    </Stack>
  );
}
```

### Safe Area Handling (SDK 55+)

- Android: Screens auto-wrapped in `SafeAreaView`
- iOS: Content inset adjustment on first `ScrollView`
- Override: `disableAutomaticContentInsets` prop

### Android-Specific

- Maximum 5 tabs (Material Design constraint)
- `disablePopToTop`: Prevents stack reset on active tab tap
- `disableScrollToTop`: Disables scroll-to-top behavior
- Keyboard avoidance enabled by default

### Web Fallback

Native tabs render a basic iPad-like tab bar on web. For custom web layouts:

```tsx
// app/_layout.web.tsx
import { Tabs } from 'expo-router/ui';

export default function WebTabLayout() {
  return <Tabs>{/* custom web tab UI */}</Tabs>;
}
```

## Known Issues

### White flash while pushing screens

Transparent `NativeTabs` can flash white in some stack transitions. Mitigate with a
`ThemeProvider` background:

```tsx
import { DarkTheme, ThemeProvider } from '@react-navigation/native';
import { NativeTabs } from 'expo-router/unstable-native-tabs';

export default function Layout() {
  return (
    <ThemeProvider value={DarkTheme}>
      <NativeTabs transparentBackground />
    </ThemeProvider>
  );
}
```

## Limitations

- 5-tab maximum on Android
- Cannot measure tab bar height programmatically
- No nested native tabs
- FlatList integration is limited
- Dynamically adding/removing tabs causes remounting and state loss
- Limited scroll-to-top support with FlatList
