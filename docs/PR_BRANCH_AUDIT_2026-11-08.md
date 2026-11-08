## 2026-11-08 — Current PR #46 preference-save and QA status

- Preferences-save defensive fix and tests are now in the feature branch working tree; full V2 suite passed 281 tests locally. The patch has not yet been pushed/CI-validated.
- Separate local-browser QA server is running on 127.0.0.1:8004, fresh synthetic DB, all collectors and notifications off, Google and Telegram credentials blank; use SSH tunnel port 18004. The original feature test service remains on 8002 and Google OAuth is enabled there.
- Do not claim the original empty-role payload root cause is confirmed; the prior failed request body wasn't captured. Browser QA must verify the new tag extraction/payload and saved data persistence.
- See docs/LOCAL_BROWSER_QA_2026-11-08.md.