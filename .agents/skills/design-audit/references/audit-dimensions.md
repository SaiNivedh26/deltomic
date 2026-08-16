# Audit Dimensions

Detailed scoring criteria for each of the 15 audit dimensions. For every screen, score each dimension as **Pass**, **Needs Work**, or **Fail**.

---

## 1. Visual Hierarchy
**Definition:** The arrangement of elements that guides the eye in order of importance.

**What to look for:**
- Is there a single, unmissable primary action per screen?
- Do headings, body text, and secondary elements have clear size/weight differentiation?
- Does the eye flow naturally top-to-bottom, left-to-right (or per locale)?
- Are competing elements fighting for attention?

**Pass:** One clear focal point, obvious reading order, no ambiguity about what to do next.
**Fail:** Multiple elements compete for attention, user has to scan to find the primary action.

---

## 2. Spacing & Rhythm
**Definition:** The consistent use of space between and around elements to create visual rhythm.

**What to look for:**
- Are gaps between related items smaller than gaps between unrelated items?
- Is the spacing scale consistent (e.g., 4/8/12/16/24/32/48)?
- Do sections have clear visual separation?
- Is there breathing room around content, or does it feel cramped?

**Pass:** Spacing follows a predictable scale, related items are grouped, sections breathe.
**Fail:** Inconsistent gaps, cramped content, no clear grouping.

---

## 3. Typography
**Definition:** The use of typefaces, sizes, weights, and line heights to communicate hierarchy and ensure readability.

**What to look for:**
- Is the type scale limited (3-5 distinct sizes)?
- Are font weights used to signal hierarchy, not decoration?
- Are line heights comfortable for reading (1.4-1.6 for body)?
- Is text legible at all viewport sizes?

**Pass:** Clear type scale, weights map to hierarchy, comfortable reading experience.
**Fail:** Too many sizes, decorative weight usage, poor readability.

---

## 4. Color
**Definition:** The intentional use of color to communicate meaning, state, and hierarchy.

**What to look for:**
- Is the palette limited and consistent (1 primary, 1-2 accents, neutrals)?
- Do colors have semantic meaning (success, error, warning, info)?
- Are contrast ratios WCAG AA compliant (4.5:1 text, 3:1 large text)?
- Is color used to reinforce hierarchy, not replace it?

**Pass:** Consistent palette, semantic color usage, sufficient contrast, color supports (not replaces) hierarchy.
**Fail:** Too many colors, arbitrary usage, poor contrast, color as sole differentiator.

---

## 5. Alignment & Grid
**Definition:** The placement of elements on a consistent spatial grid.

**What to look for:**
- Do elements align to a grid system?
- Are left edges consistent across stacked elements?
- Is optical alignment considered (icons vs. text, rounded vs. square)?
- Are there any rogue elements that break the grid?

**Pass:** Every element sits on the grid, edges align, optical corrections applied.
**Fail:** Misaligned elements, inconsistent margins, no grid awareness.

---

## 6. Components
**Definition:** The reuse and consistency of UI components across screens.

**What to look for:**
- Is the same component used for the same purpose everywhere?
- Do components have consistent APIs (props, variants, sizes)?
- Are there one-off components that should be standardized?
- Do components handle all states (default, hover, active, disabled, loading, error)?

**Pass:** Consistent component usage, full state coverage, no unnecessary one-offs.
**Fail:** Same purpose served by different components, missing states, proliferating variants.

---

## 7. Iconography
**Definition:** The style, sizing, and usage of icons throughout the app.

**What to look for:**
- Are all icons from the same family/style (outline, filled, duo-tone)?
- Are icon sizes consistent (typically 20/24px)?
- Do icons have sufficient touch targets (44x44pt minimum)?
- Are icons meaningful or decorative? (Decorative icons add noise.)

**Pass:** Consistent icon style, appropriate sizes, adequate touch targets, every icon earns its place.
**Fail:** Mixed icon styles, inconsistent sizing, tiny touch targets, decorative clutter.

---

## 8. Motion & Transitions
**Definition:** The purposeful use of animation to communicate state changes and spatial relationships.

**What to look for:**
- Do transitions communicate spatial relationships (where things come from/go)?
- Are durations appropriate (150-300ms for micro, 300-500ms for page)?
- Is easing natural (ease-out for entrances, ease-in for exits)?
- Is motion reduced when the user requests it (prefers-reduced-motion)?

**Pass:** Purposeful motion, appropriate timing, natural easing, respects user preferences.
**Fail:** Gratuitous animation, jarring timing, linear easing, ignores reduced motion.

---

## 9. Empty States
**Definition:** What the user sees when there is no data to display.

**What to look for:**
- Is there a clear message explaining why it's empty?
- Is there a call-to-action to resolve the empty state?
- Does it feel designed, not like an afterthought?
- Does it maintain the visual quality of the rest of the app?

**Pass:** Clear explanation, actionable CTA, designed with care, consistent quality.
**Fail:** Blank screen, generic "No data" text, no guidance, feels broken.

---

## 10. Loading States
**Definition:** What the user sees while data is being fetched or processed.

**What to look for:**
- Are skeleton screens used instead of spinners where possible?
- Is loading progressive (showing content as it arrives)?
- Does the loading state match the layout of the loaded state?
- Is perceived performance optimized (instant feedback, optimistic UI)?

**Pass:** Skeleton screens, progressive loading, layout-matched, fast perceived performance.
**Fail:** Full-screen spinners, no feedback, layout shift on load, slow perceived performance.

---

## 11. Error States
**Definition:** What the user sees when something goes wrong.

**What to look for:**
- Is the error message clear and human-readable (not a stack trace)?
- Is there a recovery path (retry, go back, contact support)?
- Does the tone match the app's voice (calm, helpful, not alarming)?
- Are inline errors preferred over modal/toast errors?

**Pass:** Clear message, obvious recovery, calm tone, inline where possible.
**Fail:** Technical jargon, no recovery path, alarming tone, disruptive modals.

---

## 12. Dark Mode / Theming
**Definition:** The adaptation of the UI for dark mode and other theme variants.

**What to look for:**
- Are colors mapped semantically (not just inverted)?
- Do elevated surfaces get lighter in dark mode (elevation = brightness)?
- Are shadows replaced with borders or subtle brightness shifts?
- Is contrast maintained across all themes?

**Pass:** Semantic color mapping, proper elevation, adapted shadows, consistent contrast.
**Fail:** Simple inversion, flat dark surfaces, invisible shadows, broken contrast.

---

## 13. Density
**Definition:** The amount of information presented per viewport.

**What to look for:**
- Is the information density appropriate for the use case (dashboard vs. reader)?
- Are touch targets at least 44x44pt?
- Is there a clear visual hierarchy even in dense views?
- Can users scan quickly to find what they need?

**Pass:** Appropriate density, adequate touch targets, clear hierarchy, scannable.
**Fail:** Too dense or too sparse, tiny touch targets, no hierarchy in dense views.

---

## 14. Responsiveness
**Definition:** How the UI adapts across viewport sizes and orientations.

**What to look for:**
- Is mobile the starting point (mobile-first)?
- Do breakpoints make sense for the content (not arbitrary)?
- Does content reflow naturally (no horizontal scroll)?
- Are touch targets and text sizes appropriate at each breakpoint?

**Pass:** Mobile-first, content-driven breakpoints, natural reflow, appropriate sizing.
**Fail:** Desktop-first, arbitrary breakpoints, horizontal scroll, tiny mobile targets.

---

## 15. Accessibility
**Definition:** The usability of the app for users with disabilities.

**What to look for:**
- Are contrast ratios WCAG AA compliant?
- Do interactive elements have accessible labels?
- Is focus order logical and complete?
- Is the app usable with reduced motion, increased text size, and screen readers?

**Pass:** Compliant contrast, labeled elements, logical focus, works with assistive tech.
**Fail:** Poor contrast, unlabeled buttons, broken focus order, inaccessible to assistive tech.
