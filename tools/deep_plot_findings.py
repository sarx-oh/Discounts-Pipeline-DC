"""Render aggregate study figures without private transaction identifiers."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
root=Path(__file__).resolve().parents[1];ev=root/'evidence/discount_deep_20261027';d=json.loads((ev/'full_population_results.json').read_text())
fig,ax=plt.subplots(1,2,figsize=(12,4.6));x=np.arange(4);labels=['>0','≥5','≥10','≥20']
for key,label,color in [('weighted_gross_rate_difference','Tip / gross','#2864a8'),('weighted_account_rate_difference','Tip / final account','#c16a1b')]:
 vals=[100*t['contrasts'][key]['estimate'] for t in d['tips']];ax[0].plot(x,vals,'o-',label=label,color=color)
ax[0].axhline(0,color='gray',lw=.8);ax[0].set_xticks(x,labels);ax[0].set(xlabel='Minimum final account (source currency units)',ylabel='Discounted minus nondiscounted (pp)',title='Tip-rate direction depends on the denominator');ax[0].legend(fontsize=9)
vals=[t['contrasts']['weighted_amount_difference']['estimate'] for t in d['tips']];lo=[v-t['contrasts']['weighted_amount_difference']['interval95'][0] for v,t in zip(vals,d['tips'])];hi=[t['contrasts']['weighted_amount_difference']['interval95'][1]-v for v,t in zip(vals,d['tips'])]
ax[1].errorbar(x,vals,yerr=[lo,hi],fmt='o-',capsize=4,color='#2864a8');ax[1].axhline(0,color='gray',lw=.8);ax[1].set_xticks(x,labels);ax[1].set(xlabel='Minimum final account (source currency units)',ylabel='Difference in recorded tip amount',title='Recorded amount remains lower')
for a in ax:a.grid(alpha=.2)
fig.suptitle('Within employee, location, week, channel and gross band',fontsize=13)
fig.text(.5,.01,'Card-only supported cells; cohort changes with each cutoff. Associations, not causal effects. Intervals use location/week weights.',ha='center',fontsize=8)
fig.tight_layout(rect=[0,.06,1,.94]);fig.savefig(root/'docs/figures/deep_tip_denominators.png',dpi=170);plt.close(fig)
