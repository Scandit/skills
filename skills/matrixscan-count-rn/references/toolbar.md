# MatrixScan Count view controls and toolbar in React Native

For an existing `BarcodeCountView`, keep its mode, camera lifecycle and listeners. Apply the visibility properties in the existing view ref callback.

### 5a — Visibility Toggles

All properties are `boolean`. Set them in the `ref` callback.

| Property | Default | Description |
|----------|---------|-------------|
| `shouldShowUserGuidanceView` | `true` | Show the user guidance / loading view. |
| `shouldShowListProgressBar` | `true` | Show progress bar when a capture list is active. |
| `shouldShowListButton` | `true` | Show the list button (lower-left). |
| `shouldShowExitButton` | `true` | Show the exit button (lower-right). |
| `shouldShowShutterButton` | `true` | Show the center shutter button. |
| `shouldShowHints` | `true` | Show on-screen hints. |
| `shouldShowClearHighlightsButton` | `false` | Show the "clear highlights" button above the shutter. |
| `shouldShowSingleScanButton` | `false` | Show a single-scan button (lower-left). |
| `shouldShowStatusModeButton` | `false` | Show status mode toggle button (RN 8.3+). |
| `shouldShowFloatingShutterButton` | `false` | Show a draggable floating shutter button. |
| `shouldShowToolbar` | `true` | Show the collapsible toolbar at the top. |
| `shouldShowScanAreaGuides` | `false` | Debug: visualize the active scan area. |
| `shouldShowTorchControl` | `false` | Show torch on/off button (RN 6.26+). |
| `shouldShowStatusIconsOnScan` | `false` | Auto-load status icons immediately on scan, bypassing the manual toggle (RN 8.3+). |
| `shouldDisableModeOnExitButtonTapped` | `true` | Auto-disable mode when exit is tapped (RN 6.19+). |

```tsx
ref={view => {
  if (view) {
    view.shouldShowExitButton = false;
    view.shouldShowToolbar = false;
    view.shouldShowClearHighlightsButton = true;
    view.shouldShowTorchControl = true;
    view.listener = viewListenerRef.current;
    view.uiListener = viewUiListenerRef.current;
  }
}}
```

### Applying toolbar settings

```typescript
import {
  BarcodeCountToolbarSettings,
} from 'scandit-react-native-datacapture-barcode';

ref={view => {
  if (view) {
    // BarcodeCountToolbarSettings constructor requires RN 8.3+
    const toolbarSettings = new BarcodeCountToolbarSettings();

    // Customize toolbar button labels and accessibility here (see section 5l below)
    toolbarSettings.audioOnButtonText = 'Sound On';
    toolbarSettings.audioOffButtonText = 'Sound Off';

    view.setToolbarSettings(toolbarSettings);
  }
}}
```

### 5l — BarcodeCountToolbarSettings (RN 8.3+)

`BarcodeCountToolbarSettings` controls the text labels and accessibility strings for the four toggle buttons in the collapsible toolbar: **audio**, **vibration**, **strap mode**, and **color scheme**. The constructor is available from react-native=8.3; all individual properties are available from react-native=6.17 but are only meaningful once the constructor is accessible.

#### Audio button

| Property | Platform | Description |
|----------|----------|-------------|
| `audioOnButtonText` | both | Label for the audio toggle when audio is **on**. |
| `audioOffButtonText` | both | Label for the audio toggle when audio is **off**. |
| `audioButtonAccessibilityHint` | iOS | VoiceOver hint for the audio toggle button. |
| `audioButtonAccessibilityLabel` | iOS | VoiceOver label for the audio toggle button. |
| `audioButtonContentDescription` | Android | TalkBack content description for the audio toggle button. |

```typescript
const toolbarSettings = new BarcodeCountToolbarSettings();

toolbarSettings.audioOnButtonText = 'Sound On';
toolbarSettings.audioOffButtonText = 'Sound Off';
toolbarSettings.audioButtonAccessibilityHint = 'Toggles scan sound';       // iOS VoiceOver
toolbarSettings.audioButtonAccessibilityLabel = 'Audio';                    // iOS VoiceOver
toolbarSettings.audioButtonContentDescription = 'Toggle scan audio';        // Android TalkBack

view.setToolbarSettings(toolbarSettings);
```

#### Vibration button

| Property | Platform | Description |
|----------|----------|-------------|
| `vibrationOnButtonText` | both | Label for the vibration toggle when vibration is **on**. |
| `vibrationOffButtonText` | both | Label for the vibration toggle when vibration is **off**. |
| `vibrationButtonAccessibilityHint` | iOS | VoiceOver hint for the vibration toggle button. |
| `vibrationButtonAccessibilityLabel` | iOS | VoiceOver label for the vibration toggle button. |
| `vibrationButtonContentDescription` | Android | TalkBack content description for the vibration toggle button. |

```typescript
const toolbarSettings = new BarcodeCountToolbarSettings();

toolbarSettings.vibrationOnButtonText = 'Vibration On';
toolbarSettings.vibrationOffButtonText = 'Vibration Off';
toolbarSettings.vibrationButtonAccessibilityHint = 'Toggles scan vibration'; // iOS VoiceOver
toolbarSettings.vibrationButtonAccessibilityLabel = 'Vibration';              // iOS VoiceOver
toolbarSettings.vibrationButtonContentDescription = 'Toggle vibration';       // Android TalkBack

view.setToolbarSettings(toolbarSettings);
```

#### Strap mode button

| Property | Platform | Description |
|----------|----------|-------------|
| `strapModeOnButtonText` | both | Label for the strap-mode toggle when strap mode is **on**. |
| `strapModeOffButtonText` | both | Label for the strap-mode toggle when strap mode is **off**. |
| `strapModeButtonAccessibilityHint` | iOS | VoiceOver hint for the strap-mode toggle button. |
| `strapModeButtonAccessibilityLabel` | iOS | VoiceOver label for the strap-mode toggle button. |
| `strapModeButtonContentDescription` | Android | TalkBack content description for the strap-mode toggle button. |

```typescript
const toolbarSettings = new BarcodeCountToolbarSettings();

toolbarSettings.strapModeOnButtonText = 'Strap Mode On';
toolbarSettings.strapModeOffButtonText = 'Strap Mode Off';
toolbarSettings.strapModeButtonAccessibilityHint = 'Toggles strap mode';    // iOS VoiceOver
toolbarSettings.strapModeButtonAccessibilityLabel = 'Strap Mode';            // iOS VoiceOver
toolbarSettings.strapModeButtonContentDescription = 'Toggle strap mode';     // Android TalkBack

view.setToolbarSettings(toolbarSettings);
```

#### Color scheme button

| Property | Platform | Description |
|----------|----------|-------------|
| `colorSchemeOnButtonText` | both | Label for the color-scheme toggle when the alternate color scheme is **on**. |
| `colorSchemeOffButtonText` | both | Label for the color-scheme toggle when the alternate color scheme is **off**. |
| `colorSchemeButtonAccessibilityHint` | iOS | VoiceOver hint for the color-scheme toggle button. |
| `colorSchemeButtonAccessibilityLabel` | iOS | VoiceOver label for the color-scheme toggle button. |
| `colorSchemeButtonContentDescription` | Android | TalkBack content description for the color-scheme toggle button. |

```typescript
const toolbarSettings = new BarcodeCountToolbarSettings();

toolbarSettings.colorSchemeOnButtonText = 'High Contrast On';
toolbarSettings.colorSchemeOffButtonText = 'High Contrast Off';
toolbarSettings.colorSchemeButtonAccessibilityHint = 'Toggles color scheme';  // iOS VoiceOver
toolbarSettings.colorSchemeButtonAccessibilityLabel = 'Color Scheme';          // iOS VoiceOver
toolbarSettings.colorSchemeButtonContentDescription = 'Toggle color scheme';   // Android TalkBack

view.setToolbarSettings(toolbarSettings);
```

#### All toolbar properties at once

```typescript
ref={view => {
  if (view) {
    const toolbarSettings = new BarcodeCountToolbarSettings();

    // Audio toggle labels
    toolbarSettings.audioOnButtonText = 'Sound On';
    toolbarSettings.audioOffButtonText = 'Sound Off';
    toolbarSettings.audioButtonAccessibilityLabel = 'Audio';
    toolbarSettings.audioButtonAccessibilityHint = 'Toggles scan audio feedback';
    toolbarSettings.audioButtonContentDescription = 'Toggle scan audio';

    // Vibration toggle labels
    toolbarSettings.vibrationOnButtonText = 'Vibration On';
    toolbarSettings.vibrationOffButtonText = 'Vibration Off';
    toolbarSettings.vibrationButtonAccessibilityLabel = 'Vibration';
    toolbarSettings.vibrationButtonAccessibilityHint = 'Toggles scan vibration feedback';
    toolbarSettings.vibrationButtonContentDescription = 'Toggle vibration';

    // Strap mode toggle labels
    toolbarSettings.strapModeOnButtonText = 'Strap Mode On';
    toolbarSettings.strapModeOffButtonText = 'Strap Mode Off';
    toolbarSettings.strapModeButtonAccessibilityLabel = 'Strap Mode';
    toolbarSettings.strapModeButtonAccessibilityHint = 'Enables scanning in strap mode';
    toolbarSettings.strapModeButtonContentDescription = 'Toggle strap mode';

    // Color scheme toggle labels
    toolbarSettings.colorSchemeOnButtonText = 'High Contrast On';
    toolbarSettings.colorSchemeOffButtonText = 'High Contrast Off';
    toolbarSettings.colorSchemeButtonAccessibilityLabel = 'Color Scheme';
    toolbarSettings.colorSchemeButtonAccessibilityHint = 'Toggles high-contrast color scheme';
    toolbarSettings.colorSchemeButtonContentDescription = 'Toggle color scheme';

    view.setToolbarSettings(toolbarSettings);

    view.listener = viewListenerRef.current;
    view.uiListener = viewUiListenerRef.current;
  }
}}
```

> **Note**: `BarcodeCountToolbarSettings` constructor is available from react-native=8.3. All individual string properties are present from react-native=6.17 but the class cannot be instantiated on earlier SDK versions. Accessibility hint/label properties apply only on iOS; content description properties apply only on Android. Leaving any property unset causes the SDK to use its built-in default string.
