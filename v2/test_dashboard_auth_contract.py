import shutil
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH_MODULE = ROOT / "dashboard" / "auth.js"


class DashboardAuthMarkupParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.scripts = []
        self.forms = {}

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "script" and values.get("src"):
            self.scripts.append(values["src"])
        if tag == "form" and values.get("id"):
            self.forms[values["id"]] = values


class DashboardAuthContractTests(unittest.TestCase):
    def test_dashboard_auth_client_module_exists(self):
        self.assertTrue(AUTH_MODULE.is_file(), "dashboard/auth.js must provide the cookie-session client")

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for the dashboard auth-client contract test")
    def test_auth_client_sends_cookie_credentials_and_csrf_without_bearer_tokens(self):
        script = r"""
const assert = require('assert');
const { createClient, resolveApiBase } = require('./dashboard/auth.js');
(async () => {
  assert.strictEqual(resolveApiBase('https://attacker.example/api', { origin: 'https://jobbeeper.example' }), '/api');
  assert.strictEqual(resolveApiBase('/api/v2', { origin: 'https://jobbeeper.example' }), '/api/v2');
  const calls = [];
  const responses = [
    { ok: true, status: 200, json: async () => ({ user: { id: 7, email: 'admin@example.com', role: 'admin', status: 'active' } }) },
    { ok: true, status: 200, json: async () => ({ user: { id: 7, email: 'admin@example.com', role: 'admin', status: 'active' } }) },
    { ok: true, status: 200, json: async () => ({ config: {} }) },
    { ok: true, status: 200, json: async () => ({ user: { id: 8, email: 'user@example.com', role: 'user', status: 'active' } }) },
    { ok: true, status: 200, json: async () => ({ status: 'logged_out' }) },
    { ok: true, status: 200, json: async () => ({ user: { id: 7, email: 'admin@example.com', role: 'admin', status: 'active' } }) },
    { ok: true, status: 200, json: async () => ({ consented: true }) },
  ];
  const client = createClient({
    apiBase: '/api',
    documentRef: { cookie: 'theme=dark; job_beeper_csrf=csrf-123' },
    locationRef: { origin: 'https://jobbeeper.example' },
    fetchImpl: async (url, options) => { calls.push({ url, options }); return responses.shift(); },
  });
  await client.login('admin@example.com', 'example-password');
  assert.strictEqual(calls[0].url, '/api/auth/login');
  assert.strictEqual(calls[0].options.credentials, 'same-origin');
  assert.strictEqual(JSON.parse(calls[0].options.body).email, 'admin@example.com');
  const adminSeen = [];
  await client.bootstrap({ onAdmin: user => adminSeen.push(user.email) });
  assert.deepStrictEqual(adminSeen, ['admin@example.com']);
  assert.strictEqual(calls[1].url, '/api/auth/me');
  assert.strictEqual(calls[1].options.credentials, 'same-origin');
  await client.request('/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: '{}' });
  const update = calls[2].options;
  assert.strictEqual(update.credentials, 'same-origin');
  assert.strictEqual(update.headers['X-CSRF-Token'], 'csrf-123');
  assert.strictEqual(update.headers['X-Config-Token'], undefined);
  const userSeen = [];
  const adminCalled = [];
  await client.bootstrap({ onUser: user => userSeen.push(user.email), onAdmin: user => adminCalled.push(user.email) });
  assert.deepStrictEqual(userSeen, ['user@example.com']);
  assert.deepStrictEqual(adminCalled, []);
  await client.logout();
  assert.strictEqual(calls[4].url, '/api/auth/logout');
  assert.strictEqual(calls[4].options.method, 'POST');
  assert.strictEqual(calls[4].options.headers['X-CSRF-Token'], 'csrf-123');
  assert.strictEqual(calls[4].options.credentials, 'same-origin');
  const externalClient = createClient({ apiBase: 'https://attacker.example/api', locationRef: { origin: 'https://jobbeeper.example' }, documentRef: { cookie: '' }, fetchImpl: async (url, options) => { calls.push({ url, options }); return responses.shift(); } });
  await externalClient.login('victim@example.com', 'do-not-leak-this-password');
  assert.strictEqual(calls[5].url, '/api/auth/login');
  assert.strictEqual(calls[5].options.credentials, 'same-origin');
  await client.request('/integrations/google-alerts/gmail/consent', {
    method: 'POST', body: { accepted: true, disclosure_version: '2026-11-22-v2' },
  });
  assert.strictEqual(calls[6].url, '/api/integrations/google-alerts/gmail/consent');
  assert.strictEqual(calls[6].options.headers['Content-Type'], 'application/json');
  assert.strictEqual(calls[6].options.headers['X-CSRF-Token'], 'csrf-123');
  assert.deepStrictEqual(JSON.parse(calls[6].options.body), { accepted: true, disclosure_version: '2026-11-22-v2' });
  assert.strictEqual(client.formatErrorDetail([{ type: 'missing', loc: ['body', 'accepted'], msg: 'Field required' }]), 'accepted: Field required');
  assert.strictEqual(client.formatErrorDetail('Consent required.'), 'Consent required.');
  console.log('cookie auth client contract passed');
})().catch(error => { console.error(error); process.exit(1); });
"""
        result = subprocess.run(
            [shutil.which("node"), "-e", script],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("cookie auth client contract passed", result.stdout)

    def test_gmail_connect_requires_explicit_data_use_confirmation(self):
        parser = DashboardAuthMarkupParser()
        html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        parser.feed(html)
        self.assertIn("googleAlertsGmailDataUseConsent", parser.ids)
        self.assertIn("googleAlertsGmailDataUseDisclosure", parser.ids)
        consent_markup = html.split("id=\"googleAlertsGmailDataUseConsent\"", 1)[1].split(">", 1)[0]
        self.assertNotIn("checked", consent_markup, "Gmail data-use consent must be unchecked by default")
        self.assertIn("raw email bodies", html)
        self.assertIn("Telegram is a separate service", html)

        source = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        self.assertIn("connectButton.disabled = !dataUseConsent || !dataUseConsent.checked", source)
        self.assertIn("if (!consent || !consent.checked)", source)
        self.assertIn("GOOGLE_ALERTS_GMAIL_DISCLOSURE_VERSION = '2026-11-22-v2'", source)
        self.assertIn("authClient.request('/integrations/google-alerts/gmail/consent'", source)
        self.assertIn("method: 'POST'", source)
        self.assertIn("disclosure_version: GOOGLE_ALERTS_GMAIL_DISCLOSURE_VERSION", source)
        self.assertIn("googleAlertsGmailDataUseConsent').addEventListener('change'", source)

    def test_dashboard_has_login_and_user_holding_panels(self):
        parser = DashboardAuthMarkupParser()
        parser.feed((ROOT / "dashboard" / "index.html").read_text(encoding="utf-8"))
        self.assertTrue({"authGate", "authLoginForm", "authEmail", "authPassword", "authUserPanel", "authStatusMsg", "authUserLogoutBtn", "headerLogoutBtn", "accountLogoutBtn"}.issubset(parser.ids))
        self.assertEqual(parser.forms["authLoginForm"].get("method", "get").lower(), "post", "login form must never put credentials in the URL")
        html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("Configuration Token", html)
        self.assertNotIn("config_token", html)
        auth_index = next(i for i, src in enumerate(parser.scripts) if src.startswith("auth.js"))
        app_index = next(i for i, src in enumerate(parser.scripts) if src.startswith("app.js"))
        self.assertLess(auth_index, app_index, "auth client must load before the dashboard application")

    def test_members_use_the_existing_dashboard_shell_and_user_scoped_preferences(self):
        parser = DashboardAuthMarkupParser()
        parser.feed((ROOT / "dashboard" / "index.html").read_text(encoding="utf-8"))
        self.assertTrue({"jobsSection", "appliedSection", "preferencesSection", "sourcesSection", "accessSection", "userOnboardingNotice"}.issubset(parser.ids))
        self.assertNotIn("userWorkspace", parser.ids, "members must not be routed to a separate simplified dashboard")
        self.assertIn('class="app-shell"', (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8"))
        source = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        for required in (
            "initializeWorkspace(user)", "state.isAdmin ? '/config' : '/preferences'",
            "state.isAdmin ? collectPreferencesPayload() : collectUserPreferencesPayload()",
            "state.currentUser.id", "userOnboardingNotice",
            "if (!state.isAdmin && target.id === 'sourcesSection')",
            "if (!state.isAdmin) {\n      state.sourceStatus = [];\n      return;",
            "authClient.request('/source-status'",
        ):
            self.assertIn(required, source, f"shared dashboard must implement {required}")
        html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="navSources" hidden', html)
        self.assertIn('id="navIntelligenceGroup" hidden', html)
        self.assertIn('class="workspace-page admin-only-section"', html)
        self.assertIn('class="mobile-tab-btn admin-only-navigation"', html)
        self.assertIn("admin-only-setting", html)

    def test_admin_only_navigation_respects_hidden_attribute_against_author_display_rules(self):
        html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "dashboard" / "styles.css").read_text(encoding="utf-8")
        self.assertIn('class="nav-link-item admin-only-navigation"', html)
        self.assertIn('class="nav-group admin-only-navigation"', html)
        self.assertIn('id="navIntelligenceGroup" hidden', html)
        self.assertIn('class="mobile-tab-btn admin-only-navigation"', html)
        self.assertIn("[hidden] {\n  display: none !important;\n}", css)
        self.assertIn(".nav-link-item {\n  display: flex;", css)
        self.assertIn(".mobile-tab-btn {\n  display: flex;", css)

    def test_mobile_telemetry_header_uses_a_wrapping_grid_at_390px(self):
        css = (ROOT / "dashboard" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("@media (max-width: 560px)", css)
        self.assertIn("grid-template-columns: repeat(3, minmax(0, 1fr))", css)
        self.assertIn("overflow-wrap: anywhere", css)
        self.assertIn("flex-wrap: wrap", css)

    def test_preferences_save_uses_visible_tags_and_surfaces_backend_validation(self):
        source = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        for required in (
            "function readRenderedTags()",
            "chip.cloneNode(true)",
            "const rendered = readRenderedTags()",
            "if (input.value.trim()) addTag(input.value)",
            "if (!payload.target_roles?.length) missing.push('at least one target role')",
            "if (!payload.locations?.length && !payload.remote_only) missing.push('a target location or enable Remote only for worldwide remote jobs')",
            "const errorData = await response.json().catch(() => ({}))",
            "const detail = typeof errorData.detail === 'string' ? errorData.detail.trim() : ''",
            "showToast(message, 'error', 7000)",
            "saveStatusMessage",
        ):
            self.assertIn(required, source, f"preferences save must implement {required}")
        html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        self.assertIn("With no location selected, Remote only searches worldwide.", html)

    def test_dashboard_feed_polling_is_bounded_and_skips_hidden_tabs(self):
        source = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        self.assertIn("setInterval(refreshFeedIfVisible, 60000)", source)
        self.assertIn("document.visibilityState !== 'visible'", source)
        self.assertIn("addEventListener('visibilitychange'", source)
        self.assertNotIn("}, 10000);", source, "the feed must not poll every ten seconds")

    def test_dashboard_uses_server_pagination_and_filter_parameters(self):
        source = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        for required in (
            "page: String(state.feedPage)",
            "per_page: String(state.feedPageSize)",
            "params.set('search', searchQuery)",
            "status: state.isAdmin ? 'all' : 'matched'",
            "sort_by: sortParameters.sort_by",
            "sort_order: sortParameters.sort_order",
            "params.set('source', state.filters.source)",
            "params.set('min_score', String(state.filters.minScore))",
            "params.set('max_age_hours', String(state.filters.maxAge))",
            "params.set('alertable_only', 'true')",
            "params.set('remote_only', 'true')",
            "previousJobsPageBtn",
            "nextJobsPageBtn",
        ):
            self.assertIn(required, source, f"dashboard feed must implement {required}")
        self.assertIn('id="feedPagination"', (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8"))

    def test_job_cards_label_experience_provenance(self):
        source = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        self.assertIn("Employer-stated", source)
        self.assertIn("From description", source)
        self.assertIn("Text inference", source)
        self.assertIn("experience_provenance", source)
        self.assertIn("experience_confidence", source)
        self.assertIn("rule-based evidence strength", source)

    def test_admin_dashboard_initialization_is_gated_by_session_bootstrap(self):
        source = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        for required in ("JobBeeperAuth.resolveApiBase", "JobBeeperAuth.createClient", "authClient.bootstrap", "initializeWorkspace"):
            self.assertIn(required, source, f"dashboard must integrate {required}")
        for retired in ("SESSION_TOKEN_KEY", "sessionStorage", "X-Config-Token", "fetch(API"):
            self.assertNotIn(retired, source, f"dashboard must not use {retired}")


if __name__ == "__main__":
    unittest.main()
