# Current release status

The table below records the earlier preparation audit. It is retained as historical evidence. The current release additionally includes deeper analysis and an independent Databricks detector, with 31 contract tests plus three local workspace-export checks. Operational deployment and human-review validation remain pending. See [release notes](release_notes.md) and [release scope](alcance_entrega.md).

# Preparation delivery audit

The completed scope is technical and analytical preparation through comparison of solution options. Final selection and deployment remain team decisions. Unresolved business meanings are documented rather than replaced with assumptions of misconduct.

| Requirement | Verified evidence | Result |
|---|---|---|
| New loads, corrections and duplicate-free repetition | `evidence/incremental_job.json`, Job 372187525837578 | Five scenarios pass, including expected failure and recovery |
| Safe destinations and original protection | Destination guard, 16 local tests, successful-run audits and dashboard comparison | PASS |
| Delivered executable source matches tested Job | `evidence/documentation_cleanup.json`; executable cells compared with validated bundle | All four notebooks match; complete-file hashes changed because Markdown cells were translated |
| No 11 GB reingestion | Synthetic fixtures and pinned Delta reads | Satisfied |
| Complete review base | `evidence/discount_review/base_validation.json` | Five version-0 tables; keys verified |
| Independent integrity | `base_independent.json` | Zero differences in tickets, cases and weekly totals |
| Evolution, types, payments, channels, locations and employees | Weekly/context/dynamics queries and aggregates | Executed; coverage limitations documented |
| Roles and coverage | `roles.json` | Measured; authorization not inferred |
| Employee Fifty and Employee Meal | `combinations.json`, candidate registry | Co-occurrence measured; unresolved mappings explicit |
| Contextual anomalies and comparable behavior | Leave-employee-out peers and weekly changes | Exploratory results, not compliance labels |
| Temporal variables and evaluation | Deterministic sample, disjoint dates, identical pinned sources, training-only preprocessing | Verified |
| Regularization, regression and clustering | Comparison and diagnostics evidence | Executed; predicts discounts, not abuse |
| Operational follow-up design | Empty decision log, local contract and tests | Prepared, not deployed as an application |
| Reproduction | Nine regenerated requests matched executed requests | Verified |
| Options and recommendation | Solution report | Three options pending selection |
| Portable delivery | ZIP file hashes, syntax and local links | Revalidate whenever documentation or code changes |

Employee SQL required a window-syntax correction. Sample extraction was split by period to respect INLINE limits. The first full-base run failed because Spark Connect rejected a write mode; corrected code ran in a different fresh schema. Failed-attempt evidence stays outside the ZIP.

The release does not establish production performance, abuse-detection precision or recoverable economic impact. Those require solution selection and business-reviewed samples, including cases without alerts. The Phase 2 guide asks for a Databricks job or workflow; a declarative pipeline is not stated as the only accepted execution design.
