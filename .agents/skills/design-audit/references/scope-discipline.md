# Scope Discipline

Expanded boundaries, decision tree for gray areas, and assumption escalation protocol.

---

## What to Touch (Visual Only)

- Layout and spatial arrangement of elements
- Spacing values (padding, margin, gap)
- Typography (font size, weight, line height, letter spacing)
- Color values (fills, borders, text color, backgrounds)
- Border radius, shadows, opacity
- Component visual styling and variants
- Icon selection and sizing
- Animation/transition properties (duration, easing, delay)
- Accessibility attributes (aria labels, contrast, focus indicators)
- Responsive breakpoint behavior

## What NOT to Touch

- State management logic (useState, useReducer, context)
- API calls, data fetching, caching
- Business logic, validation rules
- Navigation logic (route definitions, guards, redirects)
- Event handlers (beyond attaching onPress to existing functionality)
- Data models, types, interfaces (unless adding a visual-only prop)
- Backend code, database schemas, migrations
- Feature additions, removals, or behavioral changes
- Authentication, authorization logic
- Third-party service integrations

---

## Gray Area Decision Tree

When a change sits between visual and functional:

```
Is this change purely visual (styling, layout, spacing)?
├── YES → Proceed
└── NO → Does this change affect what the user can DO?
    ├── YES → STOP. Out of scope. Flag to user.
    └── NO → Does this change affect data flow or state?
        ├── YES → STOP. Out of scope. Flag to user.
        └── NO → Does this change require adding new props or state?
            ├── YES (visual-only prop like `variant`) → Proceed with note
            └── YES (functional prop) → STOP. Flag to user.
```

**Examples of gray areas:**
- Adding a `disabled` visual style → OK (visual) but don't add disable *logic*
- Reordering form fields → OK (layout) but verify it doesn't break tab order or validation
- Hiding an element at mobile breakpoint → Flag it. User may rely on it.
- Adding a loading skeleton → OK (visual) but don't change the data fetching pattern
- Changing a button from "Submit" to "Continue" → Flag it. Text change may affect meaning.

---

## Functionality Protection Checklist

Before implementing any visual change, verify:
- [ ] All interactive elements still respond to touch/click
- [ ] All navigation paths still work
- [ ] All form submissions still function
- [ ] All conditional rendering still triggers correctly
- [ ] All animations/transitions that affect layout still complete
- [ ] All accessibility features still work (screen reader, focus, labels)

---

## Assumption Escalation Protocol

**When to escalate:**
- You encounter a UI pattern with no documentation
- A design change could be interpreted as a behavior change
- You're unsure if a visual element has functional significance
- The existing design seems intentionally different from the system (could be a conscious choice)
- You find what looks like a bug but might be a feature

**How to escalate:**
> "I noticed [specific observation with file/component reference]. Before I design for this, I want to confirm: [specific yes/no question]?"

**Examples:**
> "I noticed the checkout button uses `opacity: 0.5` instead of the standard disabled style. Before I change it to match the design system, I want to confirm: is this intentional, perhaps indicating a different state?"

> "I noticed the card component in `MenuSection` has different spacing than the one in `CartSection`. Before I unify them, I want to confirm: are these intentionally different for content density reasons?"
