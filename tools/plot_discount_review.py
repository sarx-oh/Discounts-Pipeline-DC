"""Standalone figures from aggregate evidence, without individual employee data."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
root=Path(__file__).resolve().parents[1]
data=json.loads((root/'evidence/discount_review/weekly.json').read_text())
rows=json.loads(next(r['payload'] for r in data['rows'] if r['section']=='weekly'))
df=pd.DataFrame(rows)
df=df[(df.channel_name=='In-Store')&df.payment_family.isin(['SOLO_EFECTIVO','SOLO_TARJETA'])].copy()
fig,axes=plt.subplots(1,2,figsize=(12,4.5))
for family,label,color in [('SOLO_EFECTIVO','Cash','#cb6a27'),('SOLO_TARJETA','Card','#28689b')]:
 d=df[df.payment_family==family].sort_values('week');dates=pd.to_datetime(d.week)
 axes[0].plot(dates,100*d.discounted_positive/d.positive_tickets,label=label,color=color,marker='o',markersize=3)
 axes[1].plot(dates,100*d.intensity_numerator/d.intensity_denominator,label=label,color=color,marker='o',markersize=3)
for ax,title in zip(axes,['Tickets with discounts (%)','Discount / gross amount (%)']):
 ax.set_title(title);ax.grid(alpha=.2);ax.set_ylim(bottom=0);ax.tick_params(axis='x',rotation=30);ax.legend(frameon=False)
fig.suptitle('Weekly discount patterns in In-Store',fontsize=14)
fig.text(.5,.01,'Positive reconciled sales. Descriptive rates; first and last weeks are partial.',ha='center',fontsize=9)
fig.tight_layout(rect=[0,.05,1,.94]);out=root/'docs/figures/descuentos_evolucion.png';fig.savefig(out,dpi=160);print(out)
