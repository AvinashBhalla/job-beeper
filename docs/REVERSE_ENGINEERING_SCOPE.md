# JobBeeper product-contract discovery and implementation readiness

**Review date:** 2026-11-08  
**Scope:** Public, user-visible JobBeeper product behavior and our own JobBeeper codebase. This is not a reverse-engineering of private backend internals.

## Public product contract observed

The official public homepage (https://jobbeeper.com/) currently describes:

- Monitoring across 11 sources, with named examples including LinkedIn, Naukri, Workday, Greenhouse, Lever, Ashby and company career pages.
- User preferences based on job roles, locations, experience range and companies.
- Delivery channels including Telegram, browser and app notifications.
- Free browsing of available jobs and application tracking; paid plans add instant alerts.
- A user remains responsible for opening the original posting and applying; the product says it does not apply automatically.
- Account details include name, email and phone. Google sign-in receives name, email and profile photo, according to the public privacy explanation.

This describes the visible product promise, not its internal architecture, API contracts or data model. Source availability and detection time vary by source.

## What is already sufficient to build

We do not need to reverse-engineer the original service's private backend. Our own repository already provides the foundation and control of implementation:

- A V2 ingestion pipeline with source registry, normalization, canonicalization/deduplication, matching, persistence and dashboard APIs.
- Collector implementations for LinkedIn, Naukri relay, Greenhouse and Ashby; Instahyre remains parked/disabled pending its HTTP 400/schema issue. Configured/allowed employer boards and each environment's source switches must continue to be treated separately.
- Structured source-run observability and Naukri relay freshness work in draft PR #47, not deployed.
- A separate user/OAuth/resume/Telegram feature branch in draft PR #46. Live Google OAuth and resume parser smoke tests were confirmed by the owner on isolated feature port 8002.
- Existing per-user settings and matching foundation, but a preferences-save validation error was observed and is not yet diagnosed.

This is enough to keep building our ingestion reliability, user onboarding and product workflows without waiting for a full competitor teardown.

## Product gaps and known observations

The following are explicit, user-visible gaps to prioritize deliberately rather than silently assuming parity:

1. Email/password self-service signup is not currently exposed in the tested login UI; only the Google sign-in action was visible. Email signup, email verification and password reset remain backlog.
2. Google consent currently says "n8nApp". Update Google Auth Platform Branding before a wider beta.
3. The owner's preferences-save request returned a role-validation detail even though a target-role chip was visible; the frontend did not surface the error. The payload and HTTP status were not captured, so root cause remains unknown.
4. Workday, Lever and the rest of the advertised source catalog are not yet implemented/validated in this code path. A public homepage source list is not proof of a supported or reliable adapter in our application.
5. Browser/app notification delivery, plan entitlements, application-tracker workflows and exact public/private job-feed timing need their own acceptance tests before claiming feature parity.

See `docs/GOOGLE_OAUTH_SETUP.md` for the OAuth UAT and saved UI backlog.

## Recommended reverse-engineering boundary

Use targeted black-box discovery only where a product decision or acceptance test depends on it:

- Capture the public signup/login alternatives and the exact required account fields.
- Record preferences fields, validation rules and save behavior with redacted request/response data.
- Walk through job search, filters, job details, saving a job and application tracking.
- Verify notification channel setup, opt-in/opt-out, timing language and plan gating.
- Record source names and timestamp labels shown to users, while distinguishing marketing claims from observed reliability.

Do not spend time reproducing private backend implementation details or relying on undocumented/private endpoints. Implement our own service contracts, security model and adapter boundaries. The goal is equivalent user outcomes, not cloning their internals.

## Decision

**We are in a good position to build.** Continue with ingestion reliability and freshness first, then close the three already-observed onboarding/preferences UI gaps and add the remaining product surfaces incrementally. Do another targeted product walkthrough only when it supplies concrete acceptance criteria for the next feature; a broad reverse-engineering phase is not a blocker.
