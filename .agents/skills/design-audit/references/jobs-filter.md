# Jobs Filter

The kill-or-elevate checklist. Apply each question to every audit finding. Tally the results to decide if an element should be removed (killed) or prioritized (elevated).

---

## The 10 Questions

### Kill Questions (Does this element deserve to exist?)

1. **"Would a user need to be told this exists?"**
   If yes → the element is not self-evident. Redesign it until it's obvious, or kill it.

2. **"Can this be removed without losing meaning?"**
   If yes → remove it. No exceptions. Every remaining element is stronger for it.

3. **"Say no to 1,000 things."**
   Is this a good idea competing with a great one? Cut good to keep great. Less but better.

4. **"Is this here because we need it, or because we can?"**
   If "because we can" → kill it. Technical capability is not a design reason.

5. **"Does this create cognitive load?"**
   If the user has to parse, decode, or decide what this means → simplify or kill.

### Elevate Questions (Does this element deserve prominence?)

6. **"Does this feel inevitable, like no other design was possible?"**
   If no → it's not done. Keep refining until it feels like it was always meant to be this way.

7. **"Is this detail as refined as the details users will never see?"**
   The back of the fence must be painted too. Craft quality signals trustworthiness.

8. **"Does this serve the user's actual task right now?"**
   If it serves the user's current intent → elevate it. Make it unmissable.

9. **"Would removing this make someone's day harder?"**
   If yes → this element is essential. Give it the visual weight it deserves.

10. **"Does this reinforce the feeling of the app?"**
    If it contributes to calm, confidence, and clarity → elevate it. Premium is a feeling.

---

## How to Score

For each audit finding (an element, pattern, or screen area):

1. Ask all 10 questions
2. Tally:
   - **Kill signals**: How many of questions 1-5 suggest removal?
   - **Elevate signals**: How many of questions 6-10 suggest prominence?

### Decision Matrix

| Kill signals | Elevate signals | Action |
|-------------|----------------|--------|
| 3+ | 0-2 | **Remove** the element entirely |
| 0-2 | 3+ | **Elevate** — give it more visual weight, better placement |
| 3+ | 3+ | **Redesign** — the concept is valuable but the execution is wrong |
| 0-2 | 0-2 | **Keep as-is** — functional but not remarkable; revisit in Phase 3 |

---

## Application Examples

**Example: Decorative divider line between cards**
- Q1: Would a user need to be told? → N/A (decorative)
- Q2: Can it be removed? → Yes, spacing alone creates separation
- Q3: Good vs. great? → Good at best
- Q4: Need vs. can? → Because we can
- Q5: Cognitive load? → Minimal but adds visual noise
- Result: 4 kill signals → **Remove**

**Example: Primary checkout button**
- Q8: Serves current task? → Yes, directly
- Q9: Removal makes day harder? → Yes, can't complete purchase
- Q10: Reinforces feeling? → Should, if styled properly
- Result: 3 elevate signals → **Elevate** (ensure it's the unmissable primary action)
