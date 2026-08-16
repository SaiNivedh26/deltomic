# Design Rules

Expanded reference for the 8 design rules. Each rule includes the principle, self-test questions, and common violations.

---

## 1. Simplicity Is Architecture

**Principle:** Every element must justify its existence. If it can be removed without losing meaning, it must be removed. Simplicity is not minimalism for aesthetics — it is the elimination of everything that doesn't serve the user.

**Self-test questions:**
- Can I remove this element and the screen still works?
- Is this element solving a real user problem or a designer's anxiety?
- Would a first-time user understand this screen in 3 seconds?

**Common violations:**
- Decorative dividers between already-spaced sections
- Labels on self-evident icons (trash can icon + "Delete" text)
- Multiple CTAs competing on the same screen
- Tooltips explaining things that should be obvious from context

---

## 2. Consistency Is Non-Negotiable

**Principle:** The same component must look and behave identically everywhere it appears. Inconsistency signals sloppiness. It erodes trust. Users should never have to re-learn a pattern.

**Self-test questions:**
- If I screenshot this component from two different screens, would they be pixel-identical?
- Are there two different components serving the same purpose anywhere in the app?
- Does every instance of this pattern use the same tokens (color, spacing, radius, shadow)?

**Common violations:**
- Buttons with different padding, radius, or font weight across screens
- Cards with inconsistent shadow, border, or spacing
- Navigation patterns that change between sections
- Inconsistent use of title case vs. sentence case

---

## 3. Hierarchy Drives Everything

**Principle:** Every screen has one primary action. Make it unmissable. Everything else is secondary or tertiary. The user should never wonder "what do I do here?"

**Self-test questions:**
- If I squint at this screen, can I still identify the primary action?
- Are secondary actions visually subordinate (smaller, lighter, less prominent)?
- Does the visual weight distribution match the importance distribution?

**Common violations:**
- Two equally-prominent buttons side by side
- Secondary actions styled as primary (solid fill, high contrast)
- Important actions buried below the fold
- Headers that are visually heavier than the primary CTA

---

## 4. Alignment Is Precision

**Principle:** Every element sits on a grid. No exceptions. Misalignment is the most visible sign of carelessness. If one element is 2px off, the entire screen feels wrong — even if the user can't articulate why.

**Self-test questions:**
- If I draw vertical lines through element edges, do they align across the screen?
- Are optical corrections applied (e.g., play button triangle shifted right)?
- Is the baseline grid consistent across text elements?

**Common violations:**
- Text and icons with different left margins
- Cards with inconsistent internal padding
- Form labels misaligned with input fields
- Asymmetric spacing in symmetric layouts

---

## 5. Whitespace Is a Feature

**Principle:** Space is not empty. It is structure. Whitespace creates grouping, hierarchy, and breathing room. Cramped designs feel cheap. Generous space feels premium.

**Self-test questions:**
- Is the space between elements intentional and consistent?
- Does the spacing communicate grouping (related items close, unrelated items far)?
- Does the screen feel like it has room to breathe?

**Common violations:**
- Content pushed to edges with no margin
- Inconsistent spacing between list items
- No visual separation between sections
- Dense forms with no grouping space

---

## 6. Design the Feeling

**Principle:** Premium apps feel calm, confident, and quiet. They don't shout. They don't try too hard. Every interaction should feel like the app knows what it's doing. The feeling is the brand.

**Self-test questions:**
- Does this screen feel calm or chaotic?
- Would I feel confident entering my credit card on this screen?
- Does the app feel like it was designed by someone who cares deeply?

**Common violations:**
- Aggressive colors and bold text everywhere
- Too many exclamation marks or urgent language
- Busy backgrounds competing with content
- Gratuitous animations that feel playful but not professional

---

## 7. Responsive Is the Real Design

**Principle:** Mobile is the starting point. The smallest screen forces the hardest decisions — what truly matters, what order, what size. If it works on mobile, scaling up is easy. The reverse is not true.

**Self-test questions:**
- Was this screen designed mobile-first?
- Does the content hierarchy hold at 375px wide?
- Are touch targets at least 44x44pt on mobile?

**Common violations:**
- Desktop-first designs that crumble on mobile
- Horizontal scrolling on mobile
- Text too small to read without zooming
- Touch targets that require precision tapping

---

## 8. No Cosmetic Fixes Without Structural Thinking

**Principle:** Every change must have a design reason. "It looks nicer" is not a reason. A color change must improve hierarchy, contrast, or semantic meaning. A spacing change must improve grouping or rhythm. Changes without reasons create entropy.

**Self-test questions:**
- Can I articulate the design problem this change solves?
- Does this change improve hierarchy, consistency, readability, or usability?
- Am I changing this because it's wrong, or because I have a personal preference?

**Common violations:**
- Changing colors because "I like blue better"
- Adding rounded corners to everything
- Swapping fonts for aesthetic preference
- Adding shadows or gradients without hierarchy justification
