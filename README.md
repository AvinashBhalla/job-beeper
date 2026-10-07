# Personal job watcher

## Setup (about 10 minutes)
1. Create a PRIVATE GitHub repo and push all these files (keep the .github folder).
2. Telegram: message @BotFather -> /newbot -> copy the token.
   Message @userinfobot to get your chat id. Send your new bot one "hi".
3. Repo -> Settings -> Secrets and variables -> Actions -> add TG_TOKEN and TG_CHAT_ID.
   Optional: ADZUNA_APP_ID and ADZUNA_APP_KEY (developer.adzuna.com), then set adzuna.enabled=true.
4. Actions tab -> "check-sources" -> Run workflow (prune = true). This removes wrong company slugs.
5. Actions tab -> "job-watch" -> Run workflow. First run silently records existing jobs.
   After that you only get alerts for NEW matching jobs, every ~10 min.

## Adding companies
- Greenhouse: boards.greenhouse.io/<slug>   Lever: jobs.lever.co/<slug>   Ashby: jobs.ashbyhq.com/<slug>
- SmartRecruiters: jobs.smartrecruiters.com/<Company>   Workable: apply.workable.com/<slug>
- Workday: paste the careers URL, e.g. https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite
  plus a "search" text.
New sources are recorded silently on their first run, so adding a company will not flood you.
