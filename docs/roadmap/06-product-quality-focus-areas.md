# Product Quality Focus Areas

## The gap

All 7 current focus areas audit code **for engineers**: security vulnerabilities, dead code, stale docs, test gaps. These are valuable. But they miss an entire category of problems that live in the code and ship to users:

- The help section describes a feature that was renamed 3 months ago
- The onboarding flow has a dead end if the user skips step 2
- A button label says "Save" but the action is "Submit and close"
- The error message says "Something went wrong" instead of telling the user what to do
- The responsive layout breaks at 768px because someone hardcoded a pixel value
- The loading state shows a spinner forever on slow connections with no timeout or fallback
- Screen readers can't navigate the main menu

These aren't "bugs" in the traditional sense. The code works. The tests pass. But the product is broken. These issues typically get caught by QA teams, design reviews, or user complaints — all expensive, all late. An AI reviewing the actual templates, copy, styles, and routing logic can catch many of them at the code level, before they ship.

## What this changes about noxaudit

Today noxaudit's value proposition is: "keep your codebase healthy." Adding product quality focus areas shifts it to: "keep your **product** healthy." That's a larger market, a different buyer (product/design leads, not just engineering), and a stronger justification for the SaaS tier.

It also creates differentiation that's hard to replicate. Every SAST tool does security scanning. No tool does AI-powered UX copy review on a nightly schedule.

## The five frames

Every focus area answers one of five questions. These frames organize the 17 focus areas into concerns that map to real team priorities — and they're the toggle layer that lets teams turn entire categories on or off based on what matters right now.

| Frame | Question | Focus areas | Who cares |
|---|---|---|---|
| **Does it work?** | Can users complete their tasks without hitting errors? | `security`, `testing`, `error-states`, `user-flows`, `help-content` | Engineering, QA |
| **Does it feel right?** | Is the experience polished, consistent, and intuitive? | `ux-copy`, `ui-clarity`, `design-system`, `perf-ux` | Design, Product |
| **Can everyone use it?** | Does it work for all users, devices, languages, abilities? | `a11y`, `compatibility`, `i18n` | Product, Legal, Growth |
| **Does it last?** | Can the team keep shipping without the codebase fighting back? | `patterns`, `hygiene`, `docs`, `dependencies` | Engineering leads |
| **Can we prove it?** | Can we demonstrate quality to auditors, customers, and leadership? | `performance` + Phase 5 (compliance mapping, audit trail, policy-as-code) | Security, Compliance, Exec |

### How teams use frames

A team's priorities change over time. The frames let them express that:

**Early-stage startup (5 engineers, pre-product-market-fit)**:
```yaml
frames:
  does_it_work: true
  does_it_feel_right: false     # not yet — shipping fast
  can_everyone_use_it: false    # English-only, Chrome-only for now
  does_it_last: true            # tech debt kills startups
  can_we_prove_it: false        # no auditors yet
```

**Growth-stage product (20 engineers, expanding to EU)**:
```yaml
frames:
  does_it_work: true
  does_it_feel_right: true      # design team is growing, consistency matters
  can_everyone_use_it: true     # EU launch requires a11y + i18n + multi-device
  does_it_last: true
  can_we_prove_it: false        # not yet
```

**Enterprise product (50+ engineers, SOC 2 required)**:
```yaml
frames:
  does_it_work: true
  does_it_feel_right: true
  can_everyone_use_it: true
  does_it_last: true
  can_we_prove_it: true         # auditors are asking questions
```

Frames are the high-level switch. Within each frame, individual focus areas can still be toggled:

```yaml
frames:
  can_everyone_use_it:
    a11y: true
    compatibility: true
    i18n: false                 # not localizing yet, but want device coverage
```

### Frames in the dashboard

The SaaS dashboard (Phase 3.5) organizes around frames, not individual focus areas:

- **Health overview** shows 5 frame scores, not 17 focus area scores
- **Drill-down** from a frame to its focus areas to individual findings
- **Trend view** shows "Does it feel right?" trending up while "Does it last?" is trending down — tells a story a VP can act on
- **Onboarding** asks new users which frames matter to them, not which of 17 focus areas to enable

### Frames in the schedule

Frames map naturally to the combined audit schedule:

```
Mon: Does it work?        → security + testing + error-states + user-flows + help-content
Tue: Does it feel right?  → ux-copy + ui-clarity + design-system + perf-ux
Wed: Can everyone use it? → a11y + compatibility + i18n
Thu: Does it last?        → patterns + hygiene + docs + dependencies
Fri: Can we prove it?     → performance + (compliance checks when Phase 5 ships)
```

Five frames, five days. Weekends off. If a frame is disabled, that day is skipped (saves cost) or replaced with a deeper run of an enabled frame.

### Frames in pricing

The free/paid boundary maps cleanly to frames:

| Frame | Free | Pro | Team+ |
|---|---|---|---|
| **Does it work?** | `security`, `testing` | + `error-states`, `user-flows`, `help-content` | All |
| **Does it feel right?** | — | All 4 | All 4 + custom |
| **Can everyone use it?** | `a11y` | + `compatibility`, `i18n` | All |
| **Does it last?** | All 4 | All 4 | All 4 |
| **Can we prove it?** | `performance` | `performance` | All (Phase 5) |

Free users get the two frames every engineer needs: "Does it work?" (core safety) and "Does it last?" (maintainability). Plus `a11y` because accessibility shouldn't be paywalled. Pro unlocks the product quality frames. Team unlocks everything plus customization.

## Proposed focus areas

### 1. UX Copy & Microcopy (`ux-copy`)

**What the AI reviews**: Every piece of user-facing text in the codebase — button labels, error messages, empty states, tooltips, confirmation dialogs, placeholder text, notification content, onboarding copy.

**What it flags**:

| Severity | Example |
|---|---|
| Critical | Error message exposes internal state ("NullPointerException in UserService.java:47") |
| High | Destructive action has no confirmation ("Delete" button with no "Are you sure?") |
| High | Error message is unhelpful ("Something went wrong" with no guidance) |
| Medium | Inconsistent terminology (some buttons say "Save," others say "Submit," others say "Confirm" for equivalent actions) |
| Medium | Empty state provides no guidance (blank page with no "Get started by..." prompt) |
| Low | Placeholder text is still in the codebase ("Lorem ipsum," "TODO: write copy") |
| Low | Tone inconsistency (formal in one area, casual in another) |

**File patterns**: Templates, components with rendered text, i18n/l10n files, error handler responses, notification templates, email templates.

**Why this matters**: Bad microcopy is the #1 source of support tickets that aren't actual bugs. Users get confused, can't complete actions, and blame the product. Fixing copy is also the cheapest fix possible — high-value findings with trivial remediation. Perfect auto-fix candidate.

**Considerations**:
- Needs to understand the difference between developer-facing strings (log messages) and user-facing strings (UI text). The prompt must be explicit about this boundary.
- i18n complicates things — the AI needs to review the source language strings, not the translation keys. If the codebase uses i18n, the prompt should focus on the default locale files.
- Tone guidelines vary by product. The prompt should either detect the dominant tone or accept a configured tone profile ("professional," "casual," "technical").

---

### 2. User Flow Coherence (`user-flows`)

**What the AI reviews**: Routing definitions, navigation components, page templates, form sequences, onboarding steps, wizard/stepper implementations, redirect logic, auth guards.

**What it flags**:

| Severity | Example |
|---|---|
| Critical | Route exists in navigation but the page component is missing or returns 404 |
| Critical | Form submit handler navigates to a route that doesn't exist |
| High | Multi-step flow has no way to go back from step 3 to step 2 |
| High | Auth-protected page has no redirect to login — user sees a blank page or error |
| High | Success action navigates to a page with no context ("Payment complete!" → lands on homepage with no confirmation) |
| Medium | Navigation item is visible but the feature behind it is disabled/incomplete |
| Medium | Dead-end page — no clear next action, no navigation back |
| Medium | Inconsistent flow patterns (some forms redirect after submit, others show inline confirmation) |
| Low | Orphan routes — defined in the router but unreachable from any navigation element |

**File patterns**: Route definitions, navigation/sidebar/header components, page-level components, form handlers, middleware/guards, redirect logic.

**Why this matters**: Broken or confusing flows are invisible in unit tests and code review. They emerge from the interaction between routing, components, and state — exactly the kind of cross-file semantic analysis that AI is good at. Users who hit a dead end don't file a bug; they leave.

**Considerations**:
- This requires sending related files together — the router, the navigation component, and the page components. The focus area's file gathering needs to be smarter than simple glob patterns.
- Framework-specific knowledge matters enormously here. React Router, Next.js App Router, Vue Router, and SvelteKit all define routes differently. Language/framework-aware prompts (Phase 2) are important for this focus area.
- Dynamic routes (e.g., `/users/:id`) can't be fully validated statically. The prompt should flag suspicions but acknowledge limits.

---

### 3. Accessibility (`a11y`)

**What the AI reviews**: HTML templates/JSX, component markup, CSS/styling, form elements, interactive elements, media elements, ARIA attributes, focus management, color values.

**What it flags**:

| Severity | Example |
|---|---|
| Critical | Form inputs with no associated label (no `<label>`, no `aria-label`, no `aria-labelledby`) |
| Critical | Interactive element not keyboard-accessible (`onClick` on a `<div>` with no `role`, `tabIndex`, or keyboard handler) |
| Critical | Image conveying information has no alt text (or `alt=""` on a meaningful image) |
| High | Color contrast below WCAG AA ratio (4.5:1 for text, 3:1 for large text) |
| High | Focus trap — modal or dialog with no way to escape via keyboard |
| High | Page has no heading hierarchy (no `<h1>`, or headings skip levels) |
| Medium | ARIA role used incorrectly (`role="button"` on an element that doesn't handle Enter/Space) |
| Medium | Touch target too small (< 44x44px for interactive elements on mobile) |
| Medium | Animation with no `prefers-reduced-motion` check |
| Low | Redundant ARIA (e.g., `role="button"` on a `<button>` element) |
| Low | Tab order doesn't follow visual order |

**File patterns**: JSX/TSX, HTML templates, Vue SFC `<template>` blocks, Svelte components, CSS/SCSS files, Tailwind class usage.

**Why this matters**: Accessibility is both a legal requirement (ADA, EAA, WCAG) and a product quality issue. Automated tools like axe-core catch some issues but miss many that require semantic understanding (is this image decorative or informational? does this div behave like a button?). AI can make judgments that rule-based tools can't. Also, a11y is increasingly a procurement requirement for enterprise sales (Phase 5 tie-in).

**Considerations**:
- This overlaps partially with rule-based linting tools (eslint-plugin-jsx-a11y, axe-core). The prompt should focus on semantic issues those tools miss, not duplicate them. Position as "catches what axe-core can't."
- Color contrast checking requires parsing actual color values from CSS/Tailwind. The AI can do this but may be unreliable — consider combining AI review with a deterministic contrast checker.
- This focus area has the strongest compliance angle. Map findings to WCAG 2.1 success criteria (1.1.1 Non-text Content, 2.1.1 Keyboard, etc.) for Phase 5 compliance framework integration.

---

### 4. Cross-Browser & Responsive (`compatibility`)

**What the AI reviews**: CSS files, Tailwind/utility classes, media queries, JavaScript using browser APIs, polyfills, viewport meta tags, responsive breakpoints, CSS features with limited browser support.

**What it flags**:

| Severity | Example |
|---|---|
| High | CSS feature used without fallback and not supported in target browsers (`container queries` without fallback, `has()` selector in a Safari-required app) |
| High | Hardcoded pixel widths on containers that should be fluid (`width: 1200px` instead of `max-width`) |
| High | `window.innerWidth` used for layout decisions instead of CSS media queries |
| Medium | Missing `viewport` meta tag or incorrect viewport settings |
| Medium | `hover`-dependent interactions with no touch alternative (dropdown menus that only open on hover) |
| Medium | Fixed positioning without accounting for mobile browser chrome (bottom nav hidden behind iOS Safari's address bar) |
| Medium | Z-index wars — arbitrary large values (`z-index: 9999`) suggesting stacking context issues |
| Low | CSS custom properties used without fallback for older browsers (if browser support matrix requires it) |
| Low | `@media` breakpoints inconsistent across the codebase (some use 768px, others 769px for "tablet") |

**File patterns**: CSS/SCSS/Less files, Tailwind config, PostCSS config, JavaScript with DOM/BOM API usage, browserslist config, polyfill imports.

**Why this matters**: "It works on my machine" is the oldest bug. Developers test on Chrome on a MacBook. Users are on Safari on an iPhone, or Firefox on a 1366x768 Windows laptop. These issues are expensive to find (require multi-device testing) and cheap to fix (CSS changes). The AI can flag likely problems by understanding browser support data and identifying patterns that typically break on specific platforms.

**Considerations**:
- Browser support is a moving target. The prompt needs to reference the project's stated browser support (browserslist, or configured). Without that, default to "last 2 versions of major browsers."
- This focus area is most valuable for web applications with consumer audiences. A developer tool or internal app may intentionally support only modern Chrome. The prompt should respect configured scope.
- False positive risk is higher here than in other focus areas — a CSS feature might be fine if the project uses a transpiler/polyfill. The prompt should check for PostCSS/Autoprefixer/Babel config before flagging.

---

### 5. Help & In-App Content Accuracy (`help-content`)

**What the AI reviews**: Help pages, FAQ content, tooltips, feature descriptions, settings labels and descriptions, changelog/release notes vs. actual features, marketing copy in the app (pricing pages, feature comparison tables), onboarding tours/walkthroughs.

**What it flags**:

| Severity | Example |
|---|---|
| Critical | Help article references a feature/button/menu that no longer exists |
| Critical | Settings page describes a behavior that doesn't match the code ("Enabling this will send a daily email" but the email feature was removed) |
| High | Feature comparison table lists capabilities that aren't implemented |
| High | Keyboard shortcut listed in help but not registered in the application |
| Medium | Tooltip describes old behavior ("Click to save draft" but the button now auto-saves) |
| Medium | Help content references UI elements by wrong name ("Click the Settings gear" but it's now labeled "Preferences") |
| Medium | Changelog entry describes a feature that was reverted or modified before release |
| Low | Help screenshots (referenced by path) point to files that don't exist |
| Low | Inconsistent feature naming between help content and actual UI |

**File patterns**: Help/FAQ page components, tooltip content, settings page components and their descriptions, feature flag definitions, keyboard shortcut registrations, changelog/release notes, marketing page components.

**Why this matters**: This is the example the user gave ("your help section doesn't reflect features correctly"), and it's one of the most common product quality failures. Help content is written once and rarely updated when features change. The AI can cross-reference help text against actual component/route/feature implementations and find the drift. This is essentially the `docs` focus area but pointed at user-facing content instead of developer-facing docs.

**Considerations**:
- This has strong overlap with the existing `docs` focus area. The distinction: `docs` reviews developer-facing documentation (README, API docs, code comments). `help-content` reviews user-facing content (help pages, tooltips, settings descriptions). The prompts must be explicit about this boundary.
- Cross-referencing requires the AI to see both the help content and the actual feature code. File gathering needs to include both help pages and the feature components they describe.
- Auto-fix is highly viable here — updating a tooltip or settings description is a low-risk text change.

---

### 6. Error & Edge State Handling (`error-states`)

**What the AI reviews**: Error boundaries, catch blocks with user-facing output, loading states, empty states, timeout handling, offline behavior, form validation messages, rate limit responses, 404/500 pages.

**What it flags**:

| Severity | Example |
|---|---|
| Critical | Unhandled promise rejection that crashes the page with no recovery |
| Critical | API error response displayed raw to the user (stack trace, internal error codes) |
| High | Loading state with no timeout — spinner shows forever if the API never responds |
| High | Form validation message is technical ("regex pattern mismatch") instead of helpful ("Please enter a valid email address") |
| High | Empty state gives no guidance (blank table with no "No items yet. Create your first..." message) |
| Medium | Network error shows generic message with no retry option |
| Medium | Partial failure not communicated (batch operation where 3/10 items fail silently) |
| Medium | Optimistic update with no rollback on failure (UI shows success, then nothing happens) |
| Low | Different error message styles across the app (some use toasts, some use inline, some use modals) |
| Low | Console.error visible in production (not user-facing but indicates unhandled cases) |

**File patterns**: Error boundary components, API call wrappers, form validation logic, loading/skeleton components, empty state components, error pages (404, 500), toast/notification systems.

**Why this matters**: The happy path always works. It's the error, loading, empty, and edge states that expose product quality. These are the states that make users trust or distrust an application. Most code reviews focus on the happy path. Most tests assert the happy path. The AI can systematically audit every error path and ask "what does the user actually see here?"

**Considerations**:
- This overlaps with `security` (error messages leaking internal state) and `patterns` (inconsistent error handling). The distinction: `security` asks "is this dangerous?", `patterns` asks "is this consistent?", `error-states` asks "is this a good user experience?"
- Framework-specific: React error boundaries, Vue error handlers, SvelteKit error pages, Next.js error.tsx — each framework has its own patterns.
- Auto-fix potential is high for the copy aspects (improving error messages) but low for structural aspects (adding error boundaries, implementing retry logic).

### 7. UI Clarity & Visual Hierarchy (`ui-clarity`)

**What the AI reviews**: Page-level component composition, button/CTA density, heading structure, whitespace and spacing patterns, information density, visual weight distribution, competing calls-to-action, form length and complexity.

**What it flags**:

| Severity | Example |
|---|---|
| High | Page has multiple primary-styled CTAs competing for attention (3 buttons all styled as primary on the same view) |
| High | Critical action (delete, submit payment) has same visual weight as secondary actions — no clear hierarchy |
| High | Form has 15+ fields on a single page with no sections, steps, or progressive disclosure |
| Medium | Dense data table with no visual grouping, no row highlighting, no sticky headers — wall of text |
| Medium | Modal spawns another modal — user has lost spatial context |
| Medium | Sidebar navigation has 20+ items with no grouping or collapsible sections |
| Medium | Page mixes multiple card styles, spacing scales, or visual containers inconsistently |
| Low | Action buttons are far from the content they act on (delete button at the top, item list at the bottom) |
| Low | Success and error states use the same visual style — user can't tell them apart at a glance |

**File patterns**: Page-level components, layout components, navigation components, form components, data table/list components, modal/dialog components, CSS/Tailwind class usage for spacing and color.

**Why this matters**: "This page is really busy" is a real product problem that no linter catches. Developers add features incrementally — each one reasonable in isolation — until the page has 6 CTAs, 3 sidebars, and no clear focus. The AI can look at a component's rendered structure and identify competing visual elements, missing hierarchy, and overcrowded interfaces. This is the kind of review a designer does in a design critique but that happens too rarely on fast-moving teams.

**Considerations**:
- This is the most subjective focus area. "Too busy" depends on context — a dashboard is denser than an onboarding flow. The prompt should establish baseline expectations per page type (form, dashboard, settings, landing page).
- The AI is reviewing code structure, not rendered pixels. It can count buttons, check heading levels, and analyze component nesting — but can't truly "see" the layout. This means it catches structural clutter (too many CTAs, no heading hierarchy) better than visual clutter (colors fighting, poor whitespace).
- False positives will be higher here. Severity should skew toward medium/low. Position findings as "design review suggestions" not "bugs."
- This pairs naturally with `patterns` — if `patterns` finds "3 different card components," `ui-clarity` finds "page X uses all 3 card styles at once."

---

### 8. Internationalization Readiness (`i18n`)

**What the AI reviews**: String handling in templates and components, date/time/number formatting, currency display, pluralization logic, text direction assumptions, locale-sensitive sorting, hardcoded strings vs. i18n function usage, translation file completeness.

**What it flags**:

| Severity | Example |
|---|---|
| Critical | User-facing string hardcoded in component instead of using i18n function (`<h1>Welcome back</h1>` instead of `<h1>{t('welcome.back')}</h1>`) |
| Critical | String concatenation used to build sentences (`"You have " + count + " items"`) — breaks in languages with different word order |
| High | Date displayed with `toLocaleDateString()` but hardcoded to `en-US` format, or formatted manually (`MM/DD/YYYY`) instead of using locale-aware formatting |
| High | Currency symbol hardcoded (`$`) instead of using locale-aware currency formatting |
| High | Pluralization done with ternary (`count === 1 ? "item" : "items"`) instead of i18n pluralization rules (which vary dramatically by language) |
| Medium | Translation file has keys present in the default locale but missing in other locales |
| Medium | UI layout assumes LTR text direction — icons, alignment, and padding hardcoded for left-to-right |
| Medium | Text truncation with CSS (`text-overflow: ellipsis`) applied to elements that will contain translated text (which may be 2-3x longer in German or Finnish) |
| Low | Sort order uses default JS string comparison instead of `Intl.Collator` |
| Low | Phone number or address field assumes a single country format |

**File patterns**: Component files with rendered text, i18n/l10n configuration, translation files (JSON, YAML, PO), date/time utilities, currency/number formatting code, form components with validation.

**Why this matters**: i18n is one of those things that's 10x cheaper to do right from the start than to retrofit. Even if a product only supports English today, hardcoded strings and manual date formatting create massive technical debt when the team decides to localize. The AI can flag "you're not i18n-ready" early, before it becomes a quarter-long migration project. For products already localized, it catches the drift — new strings added without translation keys, new date formatting that bypasses the locale system.

**Considerations**:
- The i18n focus area should be aware of whether the project uses an i18n framework (react-intl, next-intl, i18next, vue-i18n, etc.). If it does, the prompt focuses on "strings that bypass the framework." If it doesn't, the prompt focuses on "readiness for future localization."
- Severity depends on whether the product currently supports multiple languages. For an English-only product, hardcoded strings are medium (technical debt). For a localized product, they're critical (user-visible bug in other locales).
- This could be configured with target locales to make findings more specific: "German translations are 40% longer on average — these 12 fixed-width containers will overflow."
- Auto-fix potential is medium — the AI can wrap hardcoded strings in `t()` calls and generate translation keys, but the actual translations need human review (or a separate translation service integration).

---

### 9. Design System Consistency (`design-system`)

**What the AI reviews**: Component usage across the application, design token usage, color values, spacing values, typography scale, icon usage, shared component library adherence.

**What it flags**:

| Severity | Example |
|---|---|
| High | Custom modal/dialog implementation when a shared component exists in the design system |
| High | Raw color hex values in components instead of design tokens/CSS variables (`#3b82f6` instead of `var(--color-primary)`) |
| High | Inline styles overriding design system patterns (`style={{ marginTop: 37 }}` — magic number, not a token) |
| Medium | 4 different button components across the codebase (Button, Btn, ActionButton, CustomButton) with overlapping functionality |
| Medium | Spacing values inconsistent — mix of `p-3`, `p-4`, `padding: 14px`, `padding: 1rem` across similar contexts |
| Medium | Typography doesn't follow the scale — arbitrary `font-size: 15px` that doesn't match any defined step |
| Medium | Icon library inconsistent — mixing Heroicons, Lucide, and custom SVGs for similar concepts |
| Low | Component prop interface differs from design system convention (some use `variant`, others use `type`, others use `kind` for the same concept) |
| Low | Color opacity applied manually (`rgba(59, 130, 246, 0.5)`) instead of using opacity token or Tailwind's `/50` syntax |

**File patterns**: All component files, CSS/SCSS/Tailwind files, theme configuration, design token definitions, shared component library, icon imports.

**Why this matters**: Every growing codebase develops "design system drift" — the component library has a `<Modal>` but three teams built their own. The design tokens define a spacing scale but half the app uses arbitrary pixel values. This isn't a code smell (the code works) and it isn't a visual bug (each individual screen looks fine) — it's a consistency tax that compounds over time. Inconsistent UI means inconsistent UX. The AI can detect "you have a system, and you're not following it" by comparing actual component usage against the available shared components.

**Considerations**:
- This focus area is most valuable for teams that have a design system (or are trying to build one). For small projects without a shared component library, many findings won't be actionable.
- The AI needs to understand what the design system is. Detection approach: look for a `components/ui/` or `components/shared/` directory, a theme config file, CSS custom property definitions, or a Tailwind config. The prompt should identify the system first, then audit adherence.
- Overlaps with `patterns` (which also finds "inconsistent approaches"). The distinction: `patterns` is about code architecture (inconsistent error handling, mixed data access patterns). `design-system` is about visual/UI architecture (inconsistent components, color values, spacing).
- Auto-fix is viable for the mechanical stuff — replacing hex values with tokens, swapping a custom component for the shared one if the API is compatible. Not viable for consolidating 4 button components into 1.

---

### 10. Performance UX (`perf-ux`)

**What the AI reviews**: Loading state implementations, skeleton screens, optimistic updates, pagination/virtualization of long lists, image optimization, lazy loading, perceived performance patterns, animation performance.

**What it flags**:

| Severity | Example |
|---|---|
| High | List renders 500+ items without virtualization — DOM will be slow, scroll will jank |
| High | Full-page loading spinner instead of skeleton/placeholder — perceived performance is terrible even if actual load time is acceptable |
| High | Large image served without responsive `srcset` or lazy loading — kills mobile performance and data budgets |
| Medium | No optimistic update on common actions (like/favorite/toggle) — UI feels sluggish waiting for server round-trip |
| Medium | Skeleton screen layout doesn't match actual content layout — jarring content shift when data loads |
| Medium | Animation uses `left`/`top` instead of `transform` — triggers layout recalculation, will jank on low-end devices |
| Medium | No loading indicator at all for async operations — user clicks a button and nothing happens for 2 seconds |
| Low | Prefetching or preloading not used for predictable navigation (user will obviously click "next" but the next page isn't prefetched) |
| Low | `will-change` applied too broadly (causes memory overhead) or not at all on animated elements |

**File patterns**: List/table components, image components, loading/skeleton components, API call wrappers, animation CSS/JS, lazy-loaded route/component definitions, intersection observer usage.

**Why this matters**: This is distinct from the existing `performance` focus area. `performance` audits backend/code performance (N+1 queries, missing indexes, blocking I/O). `perf-ux` audits what the user *perceives* — does the app feel fast? The same 200ms API response can feel instant (skeleton screen + optimistic update) or sluggish (full-page spinner + wait for response). This focus area bridges the gap between engineering performance and user-perceived performance.

**Considerations**:
- Overlaps with `performance` (the existing engineering-focused area) and `compatibility` (mobile performance). The boundaries: `performance` = "is the code fast?", `perf-ux` = "does the app feel fast?", `compatibility` = "does it work on all devices?"
- This requires some understanding of rendering behavior. The AI can reason about DOM size (500 list items = large DOM) and animation properties (transform vs. left/top) but can't measure actual frame rates.
- Auto-fix potential is low-medium. Adding `loading="lazy"` to images: yes. Implementing virtualization for a list: needs human design decisions.

## How these interact with existing focus areas

```
                    Engineer-facing          User-facing
                    (existing)               (new)
                    ─────────────            ──────────────
Code quality:       patterns                 user-flows
                    hygiene                  design-system

Presentation:                                ui-clarity
                                             compatibility

Content:            docs                     help-content
                                             ux-copy

Globalization:                               i18n

Safety:             security                 a11y
                    testing                  error-states

Performance:        performance              perf-ux

Infrastructure:     dependencies
```

The new focus areas don't replace the existing ones — they mirror them from the user's perspective. `patterns` asks "is the code consistent?" while `user-flows` asks "is the product coherent?" `docs` asks "are the READMEs accurate?" while `help-content` asks "are the tooltips accurate?" `security` asks "can an attacker exploit this?" while `a11y` asks "can a screen reader user navigate this?" `performance` asks "is the code fast?" while `perf-ux` asks "does the app feel fast?"

## Scheduling implications

The five frames replace the old "which focus areas on which day" question with something cleaner: one frame per day, five days a week.

**Frame-based schedule (recommended)**:

```
Mon: Does it work?        → security + testing + error-states + user-flows + help-content
Tue: Does it feel right?  → ux-copy + ui-clarity + design-system + perf-ux
Wed: Can everyone use it? → a11y + compatibility + i18n
Thu: Does it last?        → patterns + hygiene + docs + dependencies
Fri: Can we prove it?     → performance + compliance (Phase 5)
```

If a frame is disabled, that day is skipped or replaced with a deeper run of an enabled frame. The combined audit feature dedupes files across focus areas within a frame, keeping token costs manageable.

**Alternative: Frequency-tiered schedule**

For teams that want critical frames more often:

```
Weekly:    Does it work?, Does it last?
Biweekly:  Does it feel right?, Can everyone use it?
Monthly:   Can we prove it?
```

This reduces cost while ensuring the highest-impact frames run frequently. A startup might run only "Does it work?" and "Does it last?" — two audits per week, minimal cost, maximum safety.

## Auto-fix suitability

| Focus Area | Auto-fix potential | Why |
|---|---|---|
| **ux-copy** | High | Text changes are low-risk, easy to verify |
| **help-content** | High | Updating descriptions and tooltips is mechanical |
| **i18n** | Medium-High | Wrapping strings in `t()` calls and generating keys is mechanical; actual translations need human/service |
| **error-states** | Medium | Improving error messages: yes. Adding error boundaries: needs review |
| **a11y** | Medium | Adding alt text, ARIA labels: yes. Restructuring heading hierarchy: needs review |
| **design-system** | Medium | Swapping raw hex for tokens: yes. Consolidating 4 button components: no |
| **perf-ux** | Low-Medium | Adding `loading="lazy"`: yes. Implementing virtualization: no |
| **compatibility** | Low-Medium | Adding CSS fallbacks: yes. Restructuring layouts: needs review |
| **ui-clarity** | Low | Can suggest restructuring, but "too busy" fixes require design decisions |
| **user-flows** | Low | Fixing dead routes is structural; can suggest but shouldn't auto-apply |

`ux-copy` and `help-content` are the strongest auto-fix candidates — they're text changes with low blast radius. `i18n` is close behind — wrapping strings in translation functions is mechanical even if the translations themselves need human input. These make excellent candidates for the free tier auto-fix (alongside `hygiene` and `docs`), which expands the value of the free product and creates a stronger upgrade path.

## Impact on the SaaS dashboard

The dashboard (Phase 3.5) gets more interesting with product quality data:

- **Health score** can now reflect product quality, not just code quality. A repo with clean code but terrible error messages and broken help content shouldn't score 95. Two sub-scores: "Code Health" and "Product Health" with an overall composite.
- **Trends by category** (engineer-facing vs. user-facing) lets teams see if they're improving code but neglecting product, or vice versa.
- **Different audiences** care about different focus areas. An engineering manager looks at security/patterns/testing. A product manager looks at ux-copy/user-flows/error-states. A design lead looks at a11y/compatibility/design-system/ui-clarity. The dashboard can offer role-based default views.
- **The "product health" angle** is a distinct selling point for the SaaS tier. Free users get code audits. Paid users get product audits. This is a cleaner upsell than gating auto-fix by focus area.
- **i18n dashboard** is its own value center — translation coverage percentage, untranslated strings by locale, strings added without keys this week. This alone could justify the Pro tier for any internationalized product.

## Revised pricing consideration

If product quality focus areas become the paid differentiator:

| | Free | Pro | Team |
|---|---|---|---|
| **Engineer focus areas** (7) | All | All | All |
| **Product focus areas** (10) | a11y + i18n (readiness only) | All 10 | All 10 + custom |
| **Auto-fix** | Hygiene + docs + a11y | + ux-copy, help-content, error-states, i18n | All |

This makes the free/paid boundary about **audience** (engineer vs. product team) rather than about **capability** (with/without auto-fix). A solo developer gets full engineering audits for free. A team that cares about product quality pays. That's a cleaner story.

a11y stays free because accessibility shouldn't be paywalled — it's both good ethics and good marketing ("we don't charge you to make your product accessible"). i18n readiness (flagging hardcoded strings) is free; i18n completeness (translation coverage, missing keys by locale) is paid.

## Dependencies

```
Phase 1 (OSS Foundation) must ship first
  │
  ├── Language/framework-aware prompts (Phase 2) ──── strongly benefits user-flows,
  │                                                    compatibility, a11y
  │
  ├── Custom focus areas (Phase 2) ──────────────── product focus areas should use
  │                                                  the same mechanism
  │
  └── Cross-file analysis (Phase 2) ────────────── required for user-flows,
                                                    help-content
```

Product focus areas should land **mid-Phase 2** — after the custom focus area mechanism exists (so they're built on the same foundation) and after language-aware prompts (so they can produce framework-specific findings).

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Too many focus areas overwhelm users | Confusion, config fatigue | Group into categories (engineer / product), sane defaults, don't require configuring all 17 |
| Product focus areas produce vague findings | Users dismiss them as noise | Invest in prompt quality; these prompts are harder to write than code-focused ones because "good UX" is more subjective than "has a SQL injection" |
| AI hallucinates UI issues that don't exist | Trust erosion | Higher confidence threshold for product findings; always include file/line references so users can verify immediately |
| "We already have QA for this" | Low adoption in teams with existing QA processes | Position as augmenting QA, not replacing it — catches issues before QA, reduces QA cycle time, covers things QA doesn't check every sprint |
| Accessibility findings trigger legal anxiety | Users are scared to see a list of a11y violations | Frame positively ("here's what to improve") not punitively ("you're non-compliant"). Include severity so teams can prioritize, not panic |
