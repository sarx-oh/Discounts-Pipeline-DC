"""Exploratory interaction sensitivity, after initial replication was inspected.

Not part of the locked residue-19 confirmation; no result is used to select a model.
"""
import argparse,json
from pathlib import Path
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OrdinalEncoder,StandardScaler,OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from deep_enriched_models import load,model
from compare_discount_models import NUM,CAT,class_metrics
from deep_temporal_models import losses
from deep_model_diagnostics import crossed_interval
p=argparse.ArgumentParser();p.add_argument('workdir',type=Path);a=p.parse_args();d,sources=load(a.workdir)
d['channel_payment']=d.channel_name+'|'+d.payment_bits
d['tip_card']=d.log_tip*(d.payment_bits=='010');d['tip_instore']=d.log_tip*(d.channel_name=='In-Store')
num=NUM+['category_count','dominant_category_share','log_tip','tip_zero','tip_observed'];cat=CAT+['payment_bits','dominant_category']
def boosted():
 pre=ColumnTransformer([('n',make_pipeline(SimpleImputer(strategy='median'),StandardScaler()),num),('c',OrdinalEncoder(handle_unknown='use_encoded_value',unknown_value=np.nan),cat)])
 return make_pipeline(pre,HistGradientBoostingClassifier(max_iter=150,max_leaf_nodes=15,min_samples_leaf=50,l2_regularization=10,learning_rate=.08,categorical_features=[False]*len(num)+[True]*len(cat),early_stopping=False,random_state=721))
def interactions():
 pre=ColumnTransformer([('n',make_pipeline(SimpleImputer(strategy='median'),StandardScaler()),num+['tip_card','tip_instore']),('c',OneHotEncoder(handle_unknown='ignore'),cat+['channel_payment'])])
 return make_pipeline(pre,LogisticRegression(C=.1,max_iter=1500))
r={'status':'PASS','scope':'Post-replication exploratory interaction sensitivity on original residue 0 only','sources':sources,'folds':[]}
for end,stop in [('2026-05-31','2026-06-30'),('2026-06-30','2026-07-25'),('2026-07-25','2026-08-20')]:
 tr=d[d.BusinessDate<=end];te=d[(d.BusinessDate>end)&(d.BusinessDate<=stop)].reset_index(drop=True);y=te.has_discount.to_numpy();f={'evaluation_end':stop,'models':{}}
 for name,m in [('additive',model(enriched=True,tips=True)),('explicit_interactions',interactions()),('boosted_interactions',boosted())]:
  m.fit(tr,tr.has_discount);pred=m.predict_proba(te)[:,1];f['models'][name]=class_metrics(y,pred)
  if name=='additive':base=pred
  else:f['models'][name]['gain_over_additive']=crossed_interval(losses(y,base)-losses(y,pred),te)
  print(stop,name,f['models'][name]['log_loss'],flush=True)
 r['folds'].append(f)
(a.workdir/'interaction_results.json').write_text(json.dumps(r,indent=2,allow_nan=False))
