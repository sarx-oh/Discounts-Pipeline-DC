-- Read-only profile. The runner pins each sandbox source to a Delta version.
WITH d AS (SELECT * FROM {{discounts}}),
e AS (SELECT * FROM {{dim_employees}}),
m AS (SELECT * FROM {{ticket_metrics}}),
labels AS (
 SELECT DiscountId, DiscountName, discount_scope, COUNT(*) records,
 COUNT_IF(Amount>0) positive_records, SUM(Amount) amount,
 COUNT_IF(EmployeeId IS NULL OR EmployeeId<=0) unknown_employee_records,
 COUNT_IF(ManagerId IS NULL OR ManagerId<=0) unknown_manager_records
 FROM d GROUP BY DiscountId,DiscountName,discount_scope
), coverage AS (
 SELECT COUNT(*) records, COUNT_IF(d.Amount>0) positive_records,
 COUNT_IF(d.EmployeeId>0 AND e.Id IS NULL) positive_employee_id_missing_catalog,
 COUNT_IF(d.ManagerId>0 AND manager.Id IS NULL) positive_manager_id_missing_catalog,
 COUNT_IF(e.Deleted) deleted_employee_records,
 COUNT_IF(d.EmployeeId=d.ManagerId AND d.EmployeeId>0) same_employee_manager_records
 FROM d LEFT JOIN e ON d.EmployeeId=e.Id LEFT JOIN e manager ON d.ManagerId=manager.Id
), ticket_coverage AS (
 SELECT COUNT(*) tickets, COUNT_IF(has_discount=1) discounted_tickets,
 COUNT_IF(payment_employee_id>0) single_payment_employee_tickets,
 COUNT_IF(payment_employees>1) multiple_payment_employee_tickets,
 COUNT_IF(unknown_payment_employee_records>0) unknown_payment_employee_tickets,
 COUNT_IF(payment_employee_id>0 AND has_discount=1) attributed_discounted_tickets,
 COUNT_IF(reconciled AND account_candidate>0) positive_reconciled_tickets
 FROM m
), employees AS (
 SELECT COUNT(*) rows, COUNT(DISTINCT Id) distinct_ids,
 COUNT_IF(Id IS NULL) null_ids, COUNT_IF(Deleted) deleted_rows FROM e
)
SELECT 'labels' section,to_json(collect_list(struct(*))) payload FROM labels
UNION ALL SELECT 'discount_role_coverage',to_json(collect_list(struct(*))) FROM coverage
UNION ALL SELECT 'ticket_coverage',to_json(collect_list(struct(*))) FROM ticket_coverage
UNION ALL SELECT 'employee_catalog',to_json(collect_list(struct(*))) FROM employees
