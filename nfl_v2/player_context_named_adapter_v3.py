"""Opt-in named-input guard for B's frozen E0--E3 leaf artifacts.

The raw numerical adapter retains its declared positional contract. This wrapper
adds explicit schema/model bindings for a consumer; it changes no saved forecast.
No pickle, source collection, selection policy or production activation occurs.
Origin/query/source-time qualification remains the caller's separate bound
contract; this is an input/model/prior guard, not a complete live forecaster.
"""
import gzip, hashlib, json
import numpy as np
from .player_context_matchup import VERSION, restored_forest_law
from .distribution_laws import Law

ADAPTER_VERSION='B-QB-NAMED-LEAF-ADAPTER-v3'

class NamedLeafAdapter:
    def __init__(self, *, schema_bytes, expected_schema_sha256, receipt_bytes,
                 expected_receipt_sha256, arm, fallback_prior,
                 expected_prior_sha256, producer_version):
        if producer_version!=VERSION or arm not in('E0','E1','E2','E3'):
            raise ValueError('Unsupported declared producer/arm')
        if hashlib.sha256(schema_bytes).hexdigest()!=expected_schema_sha256:
            raise ValueError('Feature schema hash mismatch')
        if hashlib.sha256(receipt_bytes).hexdigest()!=expected_receipt_sha256:
            raise ValueError('Model receipt hash mismatch')
        # This exact count recipe uses the fitted geometric prior. Generic
        # mixture parameter summaries do not include their empirical support.
        if type(fallback_prior)is not Law or fallback_prior.kind!='geometric':
            raise ValueError('Exact frozen geometric count-prior contract required')
        prior_bytes=json.dumps(fallback_prior.parameters(),sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        if hashlib.sha256(prior_bytes).hexdigest()!=expected_prior_sha256:
            raise ValueError('Fitted fallback/prior parameter hash mismatch')
        schema=json.loads(schema_bytes);body=gzip.decompress(receipt_bytes)if receipt_bytes[:2]==b'\x1f\x8b'else receipt_bytes
        receipt=json.loads(body)
        if not receipt['slot'].endswith('-'+arm):raise ValueError('Receipt arm mismatch')
        self.names=tuple(schema['orders'][arm]);self.model=receipt['model'];self.prior=fallback_prior
        if len(set(self.names))!=len(self.names)or len(self.model['design']['median'])!=len(self.names):
            raise ValueError('Feature schema/model width mismatch')

    def predict_one(self, *, feature_names, feature_values):
        if tuple(feature_names)!=self.names:raise ValueError('Feature name/order mismatch')
        if len(feature_values)!=len(self.names):raise ValueError('Feature width mismatch')
        # Explicit unknown values are retained for the fitted imputer. Infinity
        # is a malformed input, not a missing-data shortcut.
        values=np.asarray([np.nan if x is None else x for x in feature_values],dtype=float)
        if np.isinf(values).any():raise ValueError('Infinite input')
        return restored_forest_law(self.model,values,self.prior)

    def predict_batch(self, records):
        ids=[r['query_id']for r in records]
        if any(not isinstance(x,str)or not x for x in ids)or len(set(ids))!=len(ids):
            raise ValueError('Unique nonempty query identities required')
        return [dict(query_id=r['query_id'],law=self.predict_one(feature_names=r['feature_names'],feature_values=r['feature_values']))for r in records]
