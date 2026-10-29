-- Private supporting receipts for a fixed pilot; never a new training sample.
WITH m AS (
 SELECT *,sha2(concat_ws(':',CAST(CheckId AS STRING),CAST(LocationId AS STRING),CAST(BusinessDate AS STRING)),256) ticket_key
 FROM {{ticket_metrics}} WHERE sha2(concat_ws(':',CAST(CheckId AS STRING),CAST(LocationId AS STRING),CAST(BusinessDate AS STRING)),256) IN ({{ticket_filter}})
), i AS (
 SELECT CheckId,LocationId,BusinessDate,sort_array(collect_list(struct(item_pos,ItemId,ItemName,Quantity,GrossPrice,SoldPrice))) lines
 FROM {{items_sold}} JOIN m USING(CheckId,LocationId,BusinessDate) GROUP BY CheckId,LocationId,BusinessDate
), d AS (
 SELECT CheckId,LocationId,BusinessDate,sort_array(collect_list(struct(discount_scope,item_pos,discount_pos,DiscountId,DiscountName,Amount,EmployeeId,ManagerId))) discounts
 FROM {{discounts}} JOIN m USING(CheckId,LocationId,BusinessDate) GROUP BY CheckId,LocationId,BusinessDate
), p AS (
 SELECT CheckId,LocationId,BusinessDate,sort_array(collect_list(struct(payment_pos,PayCatName,Amount,Gratuity,EmployeeId))) payments
 FROM {{payments}} JOIN m USING(CheckId,LocationId,BusinessDate) GROUP BY CheckId,LocationId,BusinessDate
)
SELECT m.ticket_key,m.CheckId,m.LocationId,m.BusinessDate,m.channel_name,m.payment_family,
 CAST(m.grossprice_sum_unvalidated AS DOUBLE) gross,CAST(m.discount_total_raw AS DOUBLE) discount_amount,
 CAST(m.account_candidate AS DOUBLE) final_account,CAST(m.gratuity_raw AS DOUBLE) gratuity_raw,
 to_json(i.lines) lines_json,to_json(d.discounts) discounts_json,to_json(p.payments) payments_json
FROM m LEFT JOIN i USING(CheckId,LocationId,BusinessDate)
LEFT JOIN d USING(CheckId,LocationId,BusinessDate) LEFT JOIN p USING(CheckId,LocationId,BusinessDate)
