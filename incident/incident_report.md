# Incident report: injected failures on the Expense API

**Type:** simulated incident (fault injection), reproducible with `scripts/traffic.py` (seed 42)
**Environment:** local Docker Compose stack (API, Postgres, Prometheus, Grafana)

## Summary
For 3 minutes, about 42% of requests to the API returned HTTP 500 and some others took around 800 ms. The error-rate and p95 latency panels on the Grafana dashboard showed it, and the HighErrorRate alert was firing from 19:20:26, about 1 min 22 s after the fault began. The fault phase ended at 19:22:04, and the alert stopped firing after 19:23:00.

## Timeline (from incident/timeline.txt and the Prometheus alert graph)
| Time | Event |
|---|---|
| 19:17:04 | Run started, baseline traffic |
| 19:19:04 | Fault phase started |
| 19:19:30 | HighErrorRate first seen Pending (26 s after the fault began) |
| 19:20:26 | HighErrorRate first seen Firing (1 min 22 s after the fault began) |
| 19:22:04 | Fault phase ended, recovery started |
| 19:23:00 | HighErrorRate last seen Firing (56 s after the fault ended) |
| 19:24:04 | Run ended |

Alert times come from the Prometheus graph (14 s resolution), so they are accurate to about 14 s.

## Impact
- Fault phase: 428 requests, 178 returned HTTP 500 (41.6%).
- Baseline: 578 requests, all 200. Recovery: 579 requests, all 200.
- Error rate on the dashboard: 0% before the fault, about 37-43% during it (peak about 43%), back to 0% after.
- p95 latency during the fault: about 0.9 s, consistent with the 800 ms delay injected on part of the requests.
- Throughput fell from about 4.8 to about 2.4 requests per second. The traffic script sends requests one at a time, so the slow responses held it up.
- Affected endpoint: /debug/fault. The requests-by-route panel showed traffic shifting to it.

## Detection
- Alert: HighErrorRate (5xx share above 5% for 1 minute) was first Pending at 19:19:30 and first Firing at 19:20:26, 1 min 22 s after the fault began. It was last seen Firing at 19:23:00.
- /health stayed up throughout, because it does not touch the database.

## Investigation
1. The error-rate and p95 panels both moved when the fault phase began.
2. The requests-by-route panel showed traffic shifting to /debug/fault, which pointed at that endpoint.
3. <A log line confirming it, with its request ID. If the logs were lost when the container was recreated, say that here instead.>

## Notes on the graphs
- The short p95 spike at about 19:16 is my manual check of the fault route before the run. It is not part of the incident.
- The error rate dips right after 19:22 because the fault phase ended while the one-minute rate window was still catching up.
- The alert kept firing for about 56 s after the fault ended, for the same reason.

## Root cause
The fault-injection endpoint was switched on (FAULT_INJECTION_ENABLED=true) and the traffic script called it on purpose, so it returned HTTP 500 errors and 800 ms delays by design.

## Resolution
The fault phase ended and normal traffic continued. Error rate returned to 0%, latency returned to baseline, and the alert stopped firing. In a real incident the fix would be reverting the faulty change or switching off the flag.

## Prevention
- The fault route is not registered unless FAULT_INJECTION_ENABLED=true, and the default is false.
- <One change you would really make to the alert. For example: the alert took 1 min 22 s to fire, so shorten `for: 1m` to `30s`, accepting more false alarms.>

## What I'd add next
- Alertmanager for notifications
- A p95 latency alert
- Authentication on /metrics

## Evidence
- `incident/timeline.txt`
- `incident/screenshots/`