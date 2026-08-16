# Post-Implementation Protocol

After each approved phase is implemented, follow this checklist to maintain project health and document decisions.

---

## Update Checklist

### 1. Update `progress.txt`
Add an entry for the completed phase:
```
## Design Phase [N] Complete — [Date]
- Changes: [summary of what was changed]
- Screens affected: [list]
- Tokens modified: [list any design system changes]
```

### 2. Update `LESSONS.md`
Document design decisions and rationale:
```
## [Date] — Design Audit Phase [N]
### Decisions Made
- [Decision]: [Why this choice was made]
### Patterns Established
- [New pattern]: [When to use it]
### Mistakes Avoided
- [What was considered but rejected]: [Why]
```

### 3. Update `DESIGN_SYSTEM.md`
If any tokens, components, or patterns changed:
- Add new tokens with values and usage context
- Deprecate removed tokens with migration notes
- Document new component variants
- Update color palette if colors changed

### 4. Flag Remaining Phases
Remind the user which phases are still pending:
```
Remaining phases:
- Phase [N]: [brief description] — awaiting approval
```

### 5. Before/After Comparison
For each changed screen, present:
```
### [Screen Name]
**Before:** [description of previous state or screenshot reference]
**After:** [description of new state or screenshot reference]
**Why:** [design rationale — which rule or dimension this addresses]
```

---

## Quality Gate

Before marking a phase complete, verify:
- [ ] All changes match the approved plan exactly (no scope creep)
- [ ] Design system files are updated if tokens changed
- [ ] No functionality was broken (run the app, check interactions)
- [ ] Accessibility was maintained or improved
- [ ] The changes feel cohesive with the rest of the app
