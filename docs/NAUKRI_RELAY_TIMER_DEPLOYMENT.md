# Naukri relay systemd deployment

The relay publisher lives in the public repository `AvinashBhalla/job-beeper-naukri-relay`. The private JobBeeper VM dispatches its existing `naukri-relay.yml` workflow; the app then consumes the published JSON snapshot.

## Units

- `job-radar-naukri-relay.service`: one-shot `gh workflow run` for the public relay workflow, using the existing Ubuntu user's GitHub CLI configuration.
- `job-radar-naukri-relay.timer`: a wall-clock ten-minute calendar timer with `Persistent=true`.

The timer uses `OnCalendar=*-*-* *:0/10:00` instead of a repeat interval based only on `OnUnitActiveSec`. systemd documents `Persistent=true` as catch-up behavior for calendar timers; it has no effect for monotonic-only timers. The calendar trigger continues on the next ten-minute boundary after boot, and a missed event while the timer is inactive is caught once when it is activated. This is intended to avoid leaving the timer loaded in `active/elapsed` with no future trigger after a reboot.

## Install only with an approved production change

The files in this directory are a reviewed template, not automatically installed by the application or CI.

Before applying them:
1. Verify the current service's GitHub CLI authentication works as user `ubuntu`.
2. Save copies of both current unit files and any drop-ins.
3. Install both files to `/etc/systemd/system/`.
4. Run `systemd-analyze verify /etc/systemd/system/job-radar-naukri-relay.service /etc/systemd/system/job-radar-naukri-relay.timer`.
5. Run `systemctl daemon-reload`, enable/start the timer, then verify `systemctl list-timers --all` shows a future next trigger.
6. Observe at least two scheduled dispatches and check the public relay workflow, feed timestamp and app's Naukri `source_runs`.

Do not run the oneshot manually as a timer verification substitute. The acceptance condition is a future timer trigger plus successful workflow, fresh feed and successful app ingestion. Roll back the two saved unit files and reload systemd if the timer fails to schedule.

Current production was observed to have the older unit:
- `OnBootSec=1min`
- `OnUnitActiveSec=5min`
- `Persistent=true`

After the 18 November 2026 reboot, this timer was found in `active/elapsed` with no future trigger. A one-time start of the existing service restored its ten-minute next trigger and subsequent runs. The exact underlying systemd state transition was not independently proven, so this template is a preventive hardening proposal, not a claim that a specific systemd defect has been isolated.

## Validation

Run the offline unit contract tests with:

```bash
python -m unittest v2.test_naukri_relay_timer -v
```

Validate the actual unit syntax on a host with systemd installed:

```bash
systemd-analyze verify deploy/systemd/job-radar-naukri-relay.service deploy/systemd/job-radar-naukri-relay.timer
systemd-analyze calendar '*-*-* *:0/10:00'
```


### Validation record — 18 November 2026

The production-host independent test run used a temporary shallow checkout of this PR and a disposable Python virtual environment. Results:
- Timer contract tests: **7 passed**.
- Full V2 suite: **546 passed**, 0 failures, 368.112 seconds.
- `systemd-analyze calendar '*-*-* *:0/5:00'` parsed the expression and returned the next five-minute boundary.
- `systemd-analyze verify` completed, with two unrelated host-level warnings: permission denied while reading `/run/systemd/system/netplan-ovs-cleanup.service`, and the host's installed `snapd.service` has an unrecognized `RestartMode` key. Neither warning referred to the proposed units.
- The temporary checkout and venv were removed after validation.

GitHub Actions did not start this PR's workflow. The check annotation reports an account billing/spending-limit block before any test process was started. This is not a test result; independent local validation above is evidence only from the production-host environment.

The production timer was not replaced. Its existing `active/waiting` schedule and successful Naukri ingestion remain under the current Health Watch.


## Cost and cadence decision — 18 November 2026

The owner paused the relay after observing frequent GitHub Actions activity. The configured public publisher repository, `AvinashBhalla/job-beeper-naukri-relay`, is public and uses the standard `ubuntu-latest` hosted runner. GitHub's billing documentation states that standard GitHub-hosted runner usage in public repositories is free and unlimited. The billing block observed on private-repository V2 CI is a separate account-level restriction; successful public relay workflows continued after that private CI block appeared.

The previous five-minute cadence produced up to 288 workflow runs/day. Observed recent workflow durations were approximately 2m–2m30s. This is substantial workflow activity and Naukri query traffic, even though the standard public runner is not billed. For a future opt-in restart, this template now proposes a ten-minute cadence (up to 144 runs/day, 50% fewer runs) while retaining the app's existing 15-minute feed freshness guard. This is a conservative initial compromise; if observed relay duration or feed freshness causes stale rejections, stop and review before widening the guard.

**Current owner decision:** relay intentionally paused at approximately 09:03 UTC on 18 November 2026. Production timer was disabled/inactive/dead at verification. Do not enable it merely by installing this template. Restart requires a separate explicit owner decision. The app's other sources continue to run independently.

Official billing references:
- https://docs.github.com/en/actions/concepts/billing-and-usage
- https://docs.github.com/en/actions/reference/runners/github-hosted-runners
