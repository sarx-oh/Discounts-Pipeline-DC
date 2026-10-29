# Release scope

| Agreed preparation block | Implementation and evidence |
|---|---|
| Portable source repository | Layered code, configuration, resources, tests, documentation and ZIP hashes; no GitHub remote |
| New files and corrections | File manifest, complete-ticket MERGE, child/aggregate reconstruction and dynamic controls; original regression retained |
| Traceable thresholds | Immutable snapshots keyed by input versions, code and configuration, plus usage history |
| Job and failure handling | Four ALL_SUCCESS tasks, one writer, explicit failure and recovery; see evidence/incremental_job.json |
| Technical documentation | Architecture, table dictionary, quality, runbook and consideration of streaming, materialized views, liquid clustering and expectations |

The final release is exported from the maintained Databricks source tree. The validation Job uses synthetic inputs. It does not publish to GitHub, promote tables to the existing dashboard or turn the synthetic Job into production ingestion. The dashboard is protected, not deployed by this package.

Analysis covers discount evolution, employee activity, discount incompatibilities, review candidates and temporal comparisons of regularized logistic regression, Ridge and clustering. A full analytical base was created in a new schema. See [solution options](descuentos_soluciones.md).

A retrospective detection prototype is implemented as an independent Databricks notebook and included, with source, tests, configuration and aggregate evidence. It is not part of the four-task Job. Operational deployment, policy confirmation and actual human review remain pending, as does manual repository publication. Ambiguous policy mappings remain explicit. The Phase 2 guide permits a Databricks job or workflow and asks teams to explain use or evaluation of the listed engineering technologies. Catalog IDs alone do not establish operational meaning.
