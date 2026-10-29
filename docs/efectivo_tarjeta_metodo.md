# Cash and card analysis method

## Question and scope

Do discount frequency and intensity differ between cash-only and card-only tickets, and how does the difference change in comparable contexts?

This descriptive analysis uses the isolated original dataset: 2,142,846 tickets, 127 locations and 115 dates, April 28–August 20, 2026. It does not use synthetic fixtures, train models or interpret differences as fraud or causality. Later model exploration is documented separately.

Pinned sources under `workspace.applebees_test_0eef22876f8b`: Gold `ticket_metrics` version 9, Silver `payments` version 9 and `discounts` version 1. Versions are checked before and after. JSON is not reingested.

## Payment classification

The primary rule uses `IsCreditCard=true` for card and `UPPER(TRIM(PayCatName))='CASH'` for cash. Conflicts are checked, and pure families are compared with the existing model. All payment records are considered, never just the first.

Mixed cash/card, combinations with other instruments, other-only and no-payment tickets remain separate. Gift cards, delivery platforms and other labels are not automatically mapped to card. Sensitivity analysis treats only OLO-VISA/MASTERCARD/DISCOVER/AMEX as card; the primary classification and source tables remain unchanged.

CASH with zero amount does not prove a cash collection. Nonpositive accounts and tickets without positive payment amounts are reported. Negative records are described by label, not automatically classified as refunds. Cash tips are not compared with card tips: recorded zero cash gratuity does not prove no cash tip occurred.

## Metrics and cohorts

- Frequency: tickets with any positive discount application divided by all tickets in the group. Preserve `has_discount`; report positive applications coexisting with nonpositive net discount.
- Intensity: sum of discounts divided by sum of GrossPrice for the same reconciled cohort with valid denominators. Do not average ticket percentages or daily rates. Do not multiply line amounts by quantity or subtract item discounts twice.
- `all`: complete descriptive population, including incomplete tickets and anomalies in frequency denominators.
- `positive`: positive reconciled account, some positive payment, no negative or null payment amounts. Primary positive-sales comparison.
- `strict`: positive cohort without mismatched or unassessable lines. A sensitivity check, not deletion.

Nonpositive accounts remain visible separately. Exclusion from positive-sales comparisons does not establish invalidity; full discounts and other operational semantics may explain them.

## Contextual comparison

Compare channel, channel+location, then channel+location+date. Both payment families must occur in each cell. Sensitivity minimums are 1, 5 and 20 tickets per method; the primary minimum is 5, a descriptive stability criterion, not business policy.

Frequency uses the same combined-ticket weight for both methods in each cell. Intensity uses combined gross amounts and requires minimum counts of valid-denominator tickets. Standardized values weight cell-specific rates with those common weights; they differ from unadjusted aggregate ratios.

Report ticket/cell coverage and results by channel. Common-support results do not automatically represent excluded channels, locations or dates. Changes in thresholds or cohorts change the population and are not causal effects. Discount-type ticket counts can overlap and must not be summed as exclusive groups.

## Isolation and reproduction

`profile_payments.py` profiles labels, signs and cohorts. `cash_card_analysis.py` takes `input_versions`, `output_path` and `output_schema`; guards restrict sources to the known sandbox and outputs to a fresh `workspace.applebees_test_0eef22876f8b_analysis_<12 hex>` schema.

Outputs contain daily location/channel/payment aggregates and standardized comparisons, not copied transaction detail. Existing destinations are rejected. New executions require fresh output schemas and report paths. The 25 original table versions are checked; the orchestrator compares dashboard definitions before/after without packaging those definitions.

`cash_card_sensitivity.py` independently reconstructs the main comparison and tests positive-payment-only classification, four OLO labels, both combined, exclusion of EMP 50 labels and exclusion of labels beginning `EMP `. These assess association robustness, not promotion eligibility or permitted combinations.

Local verification checks daily/global equality, independent estimate reproduction, source versions, three successful runs, code hashes and dashboard protection. It exports aggregates and plots only. Use `run_cash_card_analysis.py` and `report_cash_card.py` as described in the README. Analytical tasks explicitly disable serverless auto-optimization to prevent retrying resource creation. This analysis is tied to the original snapshot and checks its count; new deliveries require a revised analytical configuration.
