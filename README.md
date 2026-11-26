# FormPulse football feed

This repository publishes a rolling, credential-free fixture JSON for the free FormPulse Android app. It uses API-Sports Football v3, includes no club logos, and accepts no user data. A scheduled GitHub Actions job refreshes a 14-day window every eight hours. Previously observed settled results are retained for up to 30 days so delayed prediction history can resolve without extra API calls. Actual availability and freshness are recorded in `generated_at_utc`.

The API credential is stored only as a repository Actions secret. Do not commit a credential or enable an untrusted workflow trigger.
