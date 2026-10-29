-- Item-line repetition is descriptive; menu prices and promotion rules can explain it.
WITH joined AS (
 SELECT d.DiscountId,d.DiscountName,d.discount_scope,d.Amount,i.ItemId,i.ItemName,i.GrossPrice,
 ROUND(100*try_divide(d.Amount,i.GrossPrice),1) line_discount_pct
 FROM {{discounts}} d JOIN {{items_sold}} i USING(CheckId,LocationId,BusinessDate,item_pos)
 WHERE d.discount_scope='item' AND d.Amount>0
), products AS (
 SELECT DiscountId,DiscountName,ItemId,ItemName,COUNT(*) events,SUM(Amount) amount,
 COUNT_IF(GrossPrice<=0 OR GrossPrice IS NULL) invalid_gross_lines
 FROM joined GROUP BY ALL
), ranked AS (
 SELECT *,SUM(events) OVER(PARTITION BY DiscountId) type_events,
 ROW_NUMBER() OVER(PARTITION BY DiscountId ORDER BY events DESC,ItemId,ItemName) rank
 FROM products
), percentages AS (
 SELECT DiscountId,DiscountName,line_discount_pct,COUNT(*) events
 FROM joined WHERE GrossPrice>0 GROUP BY ALL
), modal AS (
 SELECT DiscountId,DiscountName,SUM(events) events,
 max_by(line_discount_pct,struct(events,line_discount_pct)) modal_line_pct,
 MAX(events)/SUM(events) modal_pct_share FROM percentages GROUP BY ALL HAVING SUM(events)>=100
)
SELECT 'top_products_per_type' section,to_json(collect_list(struct(*))) payload FROM ranked WHERE rank<=3 AND type_events>=100
UNION ALL SELECT 'modal_line_percentage',to_json(collect_list(struct(*))) FROM modal
