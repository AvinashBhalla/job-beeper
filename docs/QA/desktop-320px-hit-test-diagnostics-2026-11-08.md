# JobBeeper — 320px Hit-Test Diagnostics

**Date:** 2026-11-08 (Asia/Calcutta)  
**Target:** `http://localhost:18005/dashboard/`  
**Candidate:** `integration/pr46-v2-rebase-20261108`  
**Code commit:** `cf778c1f1da33c773f820cafea991fb084c58da8`

## Method

Read-only investigation in separate synthetic member and administrator browser contexts. For each viewport, Jobs was loaded, `#jobsListContainer.scrollTo(0, 99999)` was issued, and the last connected `.btn-action-applied` with text `Mark Applied` was sampled twice approximately 32ms apart. Coordinates are viewport CSS pixels. The target remained connected in all cases.

## Measurements

| Role | Viewport | Container scroll top / max | Target rect (left, top, right, bottom) | Center | Stable? |
|---|---:|---:|---|---|---|
| Member | 320×740 | 685.60 / 686 | (161.04, 259.75, 271.20, 283.35) | (216.12, 271.55) | Yes |
| Member | 375×812 | 399.20 / 399 | (216.24, 513.83, 326.40, 537.43) | (271.32, 525.63) | Yes |
| Admin | 320×740 | 616 / 616 | (161.04, 360.40, 271.20, 384.00) | (216.12, 372.20) | Yes |
| Admin | 375×812 | 344.80 / 345 | (216.24, 513.83, 326.40, 537.43) | (271.32, 525.63) | Yes |

The target button was connected. `#jobsListContainer` was `position: static`, `overflow: auto`, `pointer-events: auto`, `transform: none`; the button was `position: static`, `pointer-events: auto`, `opacity: 1`, `visibility: visible`, `transform: none`, `z-index: auto`.

## Hit-test results

### Member 320×740

At center `(216.12, 271.55)`, `elementsFromPoint()` returned `BUTTON#trigger_sortFilter.custom-dropdown-trigger` (“Newest First”), then `DIV#wrap_sortFilter.custom-dropdown-wrap`, `DIV#sortFilterMount.dropdown-mount-cell`, `.search-controls-row`, `.feed-filter-toolbar`, `.feed-master-pane`, `.feed-split-layout`, `SECTION#jobsSection`, `.workspace-views-container`, `MAIN.app-main`, `.app-shell`, `BODY.auth-ready`, `HTML`. The intended button was absent from the stack.

Inset corners produced the same overlap: top-left hit `#wrap_sortFilter`; top-right hit `#trigger_sortFilter`; both bottom corners hit `.feed-filter-toolbar`. The intended button rectangle is physically underneath the filter toolbar region. Geometry: `#jobsListContainer` top 381.60/bottom 740; `.feed-filter-toolbar` top 140.20/bottom 325.80; target top 259.75/bottom 283.35.

### Admin 320×740

At center `(216.12, 372.20)`, the topmost element was `.feed-status-strip` (top 325.80/bottom 381.60), followed by `.feed-master-pane`, `.feed-split-layout`, `SECTION#jobsSection`, `.workspace-views-container`, `MAIN`, `.app-shell`, `BODY`, `HTML`. The target button was absent from the stack. Top inset hit `#feedCountText`; top-right hit `#feedAutoRefreshText`; bottom inset points hit the target button itself. This is a partial overlap with the status strip at the button center.

### Member and admin 375×812

At center `(271.32, 525.63)`, the stack was `SPAN` “Mark Applied”, then the intended `.btn-action-secondary.btn-action-applied`, `.opportunity-actions-col`, `.opportunity-row`, `#jobsListContainer`, and its normal ancestors. All four inset corners hit the intended button. The filter toolbar ended at y=308.80 and status strip at y=345.10, above the target y=513.83–537.43.

The mobile navigation was not involved: it was fixed at top 684/bottom 740 (320px) or top 756/bottom 812 (375px), z-index 99. Target controls were above the navigation.

## Root-cause verdict

**Actual element overlap — confirmed.** At 320px, the responsive layout leaves the final job action row's viewport rectangle overlapping preceding feed controls (`.feed-filter-toolbar` for member; `.feed-status-strip` at the admin center point). Those elements are painted/hit-tested above the button. Stale DOM, incorrect coordinate conversion, target pointer-events and navigation-bar occlusion were ruled out: the target is connected, coordinates are viewport-relative, geometry is stable, and target pointer-events are `auto`.

Per the owner's priority, this known UI defect is deferred in the current work phase. No code or configuration changes were made during this diagnostic.