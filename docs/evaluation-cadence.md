# Evaluation Cadence

Harness runs should keep evaluation cadence explicit so quick checks and deeper
validation do not get mixed together. A run can be tagged as smoke, regression,
or reference depending on how much evidence it needs to collect before the
result is useful.

- Smoke runs verify that the CLI, Docker image, and sample task load correctly.
- Regression runs compare current behavior against tracked fixtures.
- Reference runs mirror the upstream harness shape and should be used before
  publishing compatibility claims.

Keeping these labels in docs makes it easier to triage failures without reading
the full run log first.
