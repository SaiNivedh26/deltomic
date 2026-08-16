# Apple Liquid Glass Design Notes

Design-focused guidance for making Liquid Glass interfaces feel native, intentional, and legible.

Use this file alongside the design rules in `SKILL.md` section 4.

## Primary Sources

- WWDC session: [Design with Liquid Glass](https://developer.apple.com/videos/play/wwdc2025/280/)
- Apple examples: [New Design Gallery](https://developer.apple.com/design/new-design-gallery/)

## Core Principles

1. Use glass for interaction chrome, not content.
2. Build hierarchy with spacing and grouping before adding visual treatment.
3. Keep content edge-to-edge so glass has meaningful background variation.
4. Start from system controls/materials and customize sparingly.
5. Put brand color into content layers, not persistent navigation bars.
6. Verify contrast in light, dark, clear, and tinted appearances.
7. Prefer one dominant glass layer per region; avoid stacked blur stacks.

## Composition Patterns

### Grouped Action Cluster

- Place related actions in one rounded glass group.
- Keep unrelated actions in separate clusters with clear spacing.
- Use one visual emphasis level inside each cluster.

### Floating Search + Filter

- Keep search in system-native placement (tab role or header search).
- Use a compact glass filter pill row beneath, not another full-width bar.
- Collapse controls on scroll to prioritize content.

### Media-Style Bottom Accessory

- Reserve tab-bar accessory for persistent context (now playing, active order, timer).
- Keep accessory concise and scannable; route detail interactions into sheet/detail screen.

## Motion Rules

- Use native interactive glass behavior when possible instead of custom opacity animations.
- Keep transitions short and purposeful; avoid decorative continuous motion.
- Maintain stable layout during animation to preserve touch confidence.

## Color and Contrast

- Test with high-saturation imagery and low-contrast photography behind glass.
- Ensure icon/text contrast remains readable when users switch between clear and tinted styles.
- Avoid pure black backgrounds behind glass where refraction becomes visually flat.

## Accessibility Checklist

- Respect Reduce Transparency with non-glass fallback.
- Preserve touch target size and spacing.
- Avoid encoding meaning only via translucency or tint.
- Re-check readability with larger text and dynamic type scaling.

## Common Anti-Patterns

- Full-screen glass overlays for content.
- Multiple competing glass layers in one region.
- Heavy custom shadows/borders that fight native material behavior.
- Glass applied without runtime guards/fallbacks on unsupported platforms.
