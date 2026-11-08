# JobBeeper public product reverse-engineering checkpoint — 2026-11-08

## Public reference evidence

Public reference: https://jobbeeper.com/ (current public landing-page search snapshot, 8 November 2026). This is marketing/public-page evidence, not an authenticated member workflow.

Observed claims and public surfaces:
- Monitors LinkedIn, Naukri, Workday and company career pages; examples include Greenhouse, Lever and Ashby, plus other sources.
- Landing page reports 11 sources, coverage snapshot 4 November 2026, 89,849 career pages/job boards watched, 79,424 companies tracked, three alert channels and a six-hour subscriber head start. These are marketing/coverage claims, not independently verified telemetry.
- Free accounts can browse and track applications; paid plans add instant alerts by Telegram, browser and app.
- Preferences mentioned publicly include roles, locations, experience and companies; remote jobs, blocked companies and pausing alerts are also mentioned.
- Product flow: choose jobs/preferences, connect paid alert channels, open original posting and apply manually. Public wording says the product does not apply automatically.
- Matches go to subscribers before selected jobs are shared publicly. The website says private preferences and alerts are not shown on the public listing.
- Public job detail examples show title/company/location, experience where available, work mode, source, posting/listing timing, description and direct employer apply link; some apply actions are gated behind sign-in. Examples: https://jobbeeper.com/j/6740037-assistant-project-manager-flexiple and https://jobbeeper.com/j/28718936-full-stack-developer-flexiple.
- Public browse routes exist by role, e.g. https://jobbeeper.com/browse/role/data and `/browse/role/{slug}`.

## What still needs reverse engineering

Landing-page copy does not prove the underlying behavior. Unknowns include authenticated onboarding/preferences, company include/exclude semantics, remote/work-mode logic, pause/resume alerts, pricing/entitlements, trial/renewal, saved searches, resume upload/grading, job tracker/notes/follow-ups, exact sorting/filter/pagination, mobile app delivery, and precise subscriber-to-public sharing rules.

Use `docs/QA/NEXT_DESKTOP_TEST_PROMPTS_2026-11-08.md` Prompt 2 for the public browser walkthrough. Do not sign up or pay. Prompt 3 covers local app security and tenant-isolation gaps.

Do not implement a six-hour release delay from a marketing claim alone. First distinguish observed behavior and separate timestamps for employer posting, first discovery, subscriber alert and public visibility.

## Sources

- https://jobbeeper.com/
- https://jobbeeper.com/browse/role/data
- https://jobbeeper.com/j/6740037-assistant-project-manager-flexiple
- https://jobbeeper.com/j/28718936-full-stack-developer-flexiple

Research checkpoint only. No reference-site account/payment action, code change or runtime change occurred.


## Follow-up public page inspection — 2026-11-08

Additional public browse route inspection confirms `/browse/role/{slug}` exposes a location filter plus a search field described as searching title, company or location, with up to 200 displayed public results. This is a public browse interaction, not proof of authenticated preference or saved-search behavior.

Public job detail inspection shows employer description content can include employer-hosted application instructions, recruitment privacy notices and EEO wording. This is consistent with rendering employer-provided descriptions and preserving the original apply route; it does not prove JobBeeper itself collects or submits an application.

Landing-page claims remain marketing/public evidence: free browsing and application tracking; paid instant alerts across Telegram, browser and app; preferences for roles/locations/experience/companies; private subscriber delivery before selected public sharing; a claimed six-hour head start. Do not implement an exact delay or entitlement rule until Desktop Prompt 2 verifies routes, plan details and actual page behavior. No signup, account action, payment or application was performed.