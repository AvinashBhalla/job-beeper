# QA-001 Source Health Navigation — CSS Root Cause and Fix

Date: 2026-11-08
Candidate: `integration/pr46-v2-rebase-20261108`

## Confirmed root cause

The desktop sidebar navigation (`.nav-link-item`) and mobile bottom navigation (`.mobile-tab-btn`) both declare `display: flex`. Their Source Health links are marked with the HTML `hidden` attribute and the role bootstrap correctly sets `element.hidden = !state.isAdmin`. However, the author-level component display declarations can override the browser's user-agent `[hidden] { display: none }` rule. This explains why the DOM/JavaScript role gate was present while the member still saw both links.

## Fix

`dashboard/styles.css` now declares a global `[hidden] { display: none !important; }` rule before component styles. This makes the semantic hidden state authoritative for every component, including admin-only sidebar and mobile navigation, while allowing JavaScript to unhide elements for administrator sessions.

A dashboard contract regression test asserts:
- both Source Health navigation variants are admin-only and retain the `hidden` attribute in markup;
- `.nav-link-item` and `.mobile-tab-btn` still use flex layout;
- the stylesheet explicitly enforces the hidden state with `display: none !important`.

## Verification status

- Focused dashboard auth contract: 11 tests passed after the fix.
- `git diff --check`: passed.
- Browser retest on candidate port 18005: pending after updated candidate server is refreshed.
- Required manual result: member desktop and mobile Source Health links absent; admin desktop and mobile links present; direct member `#sources` navigation remains redirected to Jobs.

Do not close QA-001 until that browser retest is recorded.
