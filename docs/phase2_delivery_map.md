# Phase 2 delivery map

This map follows the supplied “Phase 2: Pipeline Presentation” and “Basic Databricks GitHub Repository Template” PDFs. It maps deliverables to evidence; it is not a promised grade. The presentation must explain the work clearly rather than assuming the audience has read the repository.

| Required deliverable | Where to inspect | Delivery boundary |
|---|---|---|
| 1. Complete GitHub repository | [README](../README.md), [setup](setup.md), [code guide](code_guide.md), `resources/`, `src/transformations/`, configuration, tests and evidence | The ZIP is ready-to-publish source. Actual GitHub publication and evaluator access must still be verified by the team. A ZIP or workspace folder alone is not a published GitHub repository. |
| 2. Pipeline job | [Job definition](../resources/jobs/incremental_job.json), [operations](operacion.md), [recorded results](resultado_job.md) | Four ordered tasks; explicit/manual trigger and recovery. Synthetic validation is not production scheduling. |
| 3. Pipeline overview | [Architecture](arquitectura.md), [table dictionary](tablas.md) | Explain the original JSON/catalog inputs, Bronze records, Silver child tables and Gold outputs. |
| 4. Transformations and tables | `src/transformations/`, [code guide](code_guide.md), [table dictionary](tablas.md) | Explain array separation, whole-ticket corrections, decimal amounts, discount semantics and aggregation before joins. |
| 5. Data quality checks | [Quality controls](calidad.md), audit notebook, contract tests and Job evidence | Explain missing/incomplete records, duplicates, types, references and reconciliation; distinguish flagged records from blocking failures. |
| 6. Technical best practices | [Technical decisions](decisiones_tecnicas.md) | Streaming, materialized views, liquid clustering and expectations are explicitly evaluated. Do not claim unimplemented features. |
| 7. Analysis and business value | [Discount findings](deep_discount_findings.md), aggregate analysis evidence, [prototype results](detection_prototype_results.md) | Connect findings to named final tables and denominators. The standalone detector is an optional extension, not a replacement for explaining the pipeline. |

## Presentation coverage

Use the guide’s recommended sequence: objective → source data and architecture → transformations → data quality → final analysis → conclusion. Place the Job dependencies/trigger/recovery explanation alongside architecture and quality; include the relevant engineering decisions briefly where they explain a choice. The presentation should demonstrate a complete flow, justified processing, tested completeness/consistency/validity/uniqueness/accuracy where appropriate, and evidence-based analysis with readable visuals.

For five minutes, focus on the processes needed to understand why the output is trustworthy. A repository walkthrough is not necessary on a main slide, but the actual repository URL and supporting documentation must be delivered. Do not spend the core pipeline presentation on model comparisons or imply that synthetic fixtures are the real training data.

## Remaining external steps

Publish the extracted `Applebees_Fase2/` contents as the repository root and verify evaluator access. Present the validated workflow with genuine screenshots and formal charts. Business policy confirmation, measured review benefit, distributed review storage and production performance are future work; they must not be presented as achieved outcomes.
