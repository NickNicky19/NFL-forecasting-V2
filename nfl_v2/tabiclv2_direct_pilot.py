"""One proposed, unexecuted TabICLv2 completion-direction configuration.

No model import, download, load or fit occurs on import. A separate assigned
execution allocation and runtime/source admission are required before calling
the experiment. Do not serialize estimators, training contexts or KV caches.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import numpy as np

VERSION='B-TABICLV2-CMP-DIRECT-PILOT-v1'
CHECKPOINT='tabicl-classifier-v2-20260212.ckpt'
CHECKPOINT_SHA256='bdc7dbd5e4ff21f8f0456fcf90c6b7cdf72dbea960f2d05b19bec19f9b3d4ed0'
CHECKPOINT_BYTES=110368038
LIBRARY_COMMIT='a626a1b67049b0b1748ebe8c92f7df40aaebd334'
TABICL_CONFIG=dict(n_estimators=8,norm_methods=['none'],feat_shuffle_method='latin',
 class_shuffle_method='shift',outlier_threshold=4.,softmax_temperature=.9,
 average_logits=True,support_many_classes=False,batch_size=8,kv_cache=False,
 allow_auto_download=False,checkpoint_version=CHECKPOINT,device='cpu',
 use_amp=False,use_fa3=False,offload_mode=False,random_state=42,n_jobs=2,verbose=False)
LOGISTIC_CONFIG=dict(C=1.,solver='lbfgs',max_iter=1000,tol=1e-6,
 class_weight=None,random_state=42)

def fit_common_transform(x):
 """Earlier training matrix only; query values/labels cannot set parameters."""
 x=np.asarray(x,float)
 if x.ndim!=2 or not len(x):raise ValueError('Earlier training rows required')
 if np.isinf(x).any():raise ValueError('Infinity is invalid, not a missing observation')
 finite=np.isfinite(x);med=np.zeros(x.shape[1])
 for j in range(x.shape[1]):
  values=x[finite[:,j],j]
  if len(values):med[j]=np.median(values)
 filled=np.where(finite,x,med);mean=filled.mean(axis=0);scale=filled.std(axis=0)
 scale=np.where(scale>1e-12,scale,1.)
 return dict(median=med.tolist(),mean=mean.tolist(),scale=scale.tolist(),
             all_missing=(~finite.any(axis=0)).tolist(),clip_z=4.,missing_indicators='ALL_COLUMNS')

def transform(x,state):
 x=np.asarray(x,float);med=np.asarray(state['median']);mean=np.asarray(state['mean']);scale=np.asarray(state['scale'])
 if x.ndim!=2 or x.shape[1]!=len(med):raise ValueError('Frozen feature order/width')
 if np.isinf(x).any():raise ValueError('Infinity is invalid, not a missing observation')
 finite=np.isfinite(x);filled=np.where(finite,x,med)
 return np.column_stack((np.clip((filled-mean)/scale,-4.,4.),(~finite).astype(float)))

def positive_probability(estimator,x):
 """One query per call prevents access to later-query feature batches."""
 classes=np.asarray(estimator.classes_);where=np.flatnonzero(classes==1)
 if len(classes)!=2 or len(where)!=1 or set(classes.tolist())!={0,1}:raise ValueError('Over-positive binary event orientation')
 out=[]
 for row in np.asarray(x,float):
  p=np.asarray(estimator.predict_proba(row[None,:]),float)
  if p.shape!=(1,2)or not np.isfinite(p).all()or np.any(p<0)or np.any(p>1)or abs(p.sum()-1)>1e-6:
   raise ValueError('Invalid direct-event probabilities; no clipping or invented confidence')
  out.append(float(p[0,where[0]]))
 return np.asarray(out)

def execute_origin(x_train,y_train,x_query,checkpoint_path,*,allocation,runtime_admission):
 """Future controller supplies measured guards; this function never grants them.

 No fallback loader, remote code, fine-tuning, warm-start, pickle or model cache
 is used. Empty/one-class startup is handled by the registered parent outside
 this function, so technical failure cannot masquerade as an abstention.
 """
 if allocation.get('status')!='ASSIGNED' or allocation.get('experiment')!=VERSION:
  raise RuntimeError('B_TABICLV2_EXECUTION_ALLOCATION_NOT_ASSIGNED')
 if runtime_admission.get('state')!='PASS_PINNED_SAFE_RUNTIME_SOURCE_RETENTION':
  raise RuntimeError('Pinned runtime/source/retention qualification required before NFL inference')
 path=Path(checkpoint_path)
 if path.stat().st_size!=CHECKPOINT_BYTES or hashlib.sha256(path.read_bytes()).hexdigest()!=CHECKPOINT_SHA256:
  raise ValueError('Exact pinned model bytes required; do not substitute another checkpoint')
 raw_y=np.asarray(y_train,float)
 if raw_y.ndim!=1 or not len(raw_y) or not np.isfinite(raw_y).all() or set(raw_y.tolist())!={0.,1.}:
  raise ValueError('Exact binary labels and explicit registered startup required')
 if len(raw_y)!=len(x_train):raise ValueError('Training design/label row alignment')
 y=raw_y.astype(int)
 # Only after external allocation/admission. Official pinned classifier uses
 # torch.load(...weights_only=True); no estimator.save/load path is called.
 import torch
 from tabicl import TabICLClassifier
 from sklearn.linear_model import LogisticRegression
 torch.set_num_threads(2)
 torch.use_deterministic_algorithms(True)
 state=fit_common_transform(x_train);train=transform(x_train,state);query=transform(x_query,state)
 ordinary=LogisticRegression(**LOGISTIC_CONFIG).fit(train,y)
 candidate=TabICLClassifier(model_path=str(path),**TABICL_CONFIG).fit(train,y)
 return dict(ordinary_p_over=positive_probability(ordinary,query),
             candidate_p_over=positive_probability(candidate,query),
             transform=state,ordinary_coef=ordinary.coef_.tolist(),
             ordinary_intercept=ordinary.intercept_.tolist(),
             model_point=None,probability_type='HALF_POINT_OVER_BERNOULLI',
             side_rule='OVER_IF_P_OVER_GT_HALF;UNDER_IF_LT;EQUAL_ABSTAIN',
             save_estimator=False,save_training_context=False,save_kv_cache=False)
