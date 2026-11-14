"""Typed restoration/handoff for the frozen aligned48h F2/F3 procedures.

Historical inference and genuinely current admission are separate paths.
This adapter neither issues forecasts nor persists/releases website products.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path

from . import player_context_matchup as ctx
from .distribution_laws import prior
from .qb_aligned_freshness import AlignedFreshnessBundle, ALTERNATIVE
from .qb_context_profiles import query_validation, HISTORICAL_UNIVERSE
from .qb_opportunity_adapter import QBOpportunityAdapter, _read, _sha, _clock, _identity

VERSION='B-QB-ALIGNED-FRESHNESS-TYPED-ADAPTER-v1'
PROCEDURE='B-QB-ALIGNED-FRESHNESS-v1'


def _hash(value):
    return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None


def _timestamp(value):
    try:
        instant=datetime.fromisoformat(value)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError('Timezone required')
        return instant.timestamp()
    except (TypeError,ValueError):
        raise ValueError('Unknown model creation clock') from None


class QBAlignedFreshnessAdapter(QBOpportunityAdapter):
    def __init__(self,repository_root,protocol_path,feature_order_path,model_path,*,arm,
                 expected_protocol_sha256,expected_model_sha256):
        self.root=Path(repository_root)
        self.protocol=_read(protocol_path,expected_protocol_sha256)
        if self.protocol['id']!=PROCEDURE or arm not in ('F2','F3'):
            raise ValueError('Aligned procedure/arm contract')
        if self.protocol['alternative_policy']!=ALTERNATIVE:
            raise ValueError('Aligned information policy mismatch')
        self.arm=arm
        for path,expected in self.protocol['code_sha256'].items():
            if _sha(self.root/path)!=expected:
                raise ValueError('Executing dependency hash mismatch')
        orders=_read(feature_order_path,self.protocol['feature_order_sha256'])
        self.order=tuple(orders['orders'][arm])
        if len(self.order)!=len(set(self.order)):
            raise ValueError('Duplicate named features')
        self.model_record=_read(model_path,expected_model_sha256)
        self.model=self.model_record['model']
        match=re.fullmatch(r'(\d{4})-W(\d{2})-'+arm,self.model_record['slot'])
        if not match:
            raise ValueError('Fitted origin/arm identity mismatch')
        self.fit_season,self.fit_week=map(int,match.groups())
        self.fit_cutoff=self.model_record['fit_cutoff']
        self.model_created_at=_timestamp(self.model_record['actual_completed_utc'])
        if (not _clock(self.fit_cutoff) or self.model_record['information_policy']!=ALTERNATIVE
            or self.model_record['feature_order_sha256']!=self.protocol['feature_order_sha256']
            or self.model_record['feature_count']!=len(self.order)
            or len(self.model['design']['median'])!=len(self.order)):
            raise ValueError('Typed model feature/policy/cutoff contract')
        inputs=self.protocol['inputs'];source=self.protocol['opportunity_source']
        _read(self.root/inputs['path'],inputs['sha256'])
        original=ctx.load_inputs(self.root/inputs['path'])
        raw_source=_read(self.root/source['path'],source['sha256'])
        self.bundle=AlignedFreshnessBundle(original,raw_source,policy_id=ALTERNATIVE)
        if any(self.bundle.unresolved.values()):
            raise ValueError('Unresolved history availability; exact fitted source semantics unavailable')
        self.inputs=self.bundle.rows;self.history=self.bundle.history;self.opportunity=self.bundle.opportunity
        train=self.bundle.training_rows(self.fit_season,self.fit_cutoff)
        membership=hashlib.sha256(json.dumps([(r['game_id'],r['player_id']) for r in train]).encode()).hexdigest()
        if (len(train)!=self.model_record['training_rows']
            or membership!=self.model_record['training_membership_sha256']):
            raise ValueError('Aligned training/prior membership mismatch')
        if not train or max(r['available'] for r in train)!=self.model_record['latest_training_label']:
            raise ValueError('Aligned training label clock mismatch')
        self.prior=prior([r['official_completions'] for r in train],'pass_cmp')
        self.bindings=dict(procedure_id=PROCEDURE+':'+arm,protocol_sha256=expected_protocol_sha256,
            feature_order_sha256=self.protocol['feature_order_sha256'],model_sha256=expected_model_sha256,
            inputs_sha256=inputs['sha256'],opportunity_source_sha256=source['sha256'],
            model_slot=self.model_record['slot'],fit_season=self.fit_season,fit_week=self.fit_week,
            fit_cutoff=self.fit_cutoff,model_created_at=self.model_created_at,
            latest_training_label=self.model_record['latest_training_label'],
            prior_membership_sha256=membership,information_policy=ALTERNATIVE,feature_count=len(self.order),
            executing_dependency_sha256=dict(self.protocol['code_sha256']))

    def _unavailable(self,query,state,reason):
        out=super()._unavailable(query,state,reason)
        out['adapter_version']=VERSION
        return out

    def predict(self,*args,**kwargs):
        raise ValueError('Choose explicit historical or current admission mode')

    def predict_batch(self,*args,**kwargs):
        raise ValueError('Choose explicit historical or current batch admission mode')

    def _typed_inference(self,query,*,mode,line):
        features=self.bundle.direct_features(query,self.arm)
        if len(features)!=len(self.order):
            raise ValueError('Constructed named feature width mismatch')
        law=ctx.restored_forest_law(self.model,features,self.prior)
        threshold=None
        if line is not None:
            if not _clock(line):
                raise ValueError('Finite exact threshold required')
            over=1-law.cdf(line);under=law.cdf(math.ceil(line)-1);push=law.pmf(line)
            if min(over,under,push)<-1e-12 or abs(over+under+push-1)>1e-10:
                raise ValueError('Exact-line probability mass contract')
            threshold=dict(line=line,over=over,under=under,push=push,
                P1_mean='Over' if law.mean>line else 'Under' if law.mean<line else 'ABSTAIN',
                P1_lower_median='Over' if law.quantile(.5)>line else 'Under' if law.quantile(.5)<line else 'ABSTAIN',
                P2=dict(policy_id='P2',rule='LARGER_EXACT_LINE_SIDE_PROBABILITY_TIE_ABSTAINS',
                        side='Over' if over>under else 'Under' if under>over else 'ABSTAIN'),
                evidence='CALLER_EXACT_THRESHOLD_DIAGNOSTIC_NOT_QUALIFIED_OFFER_OR_ORIGINAL_SELECTION')
        d=self.history.describe(dict(query,kickoff=query.get('cutoff',query['kickoff'])))
        return dict(adapter_version=VERSION,status=mode,identity=_identity(query),bindings=self.bindings,
            target='pass_cmp',role='QB',feature_cutoff=query.get('cutoff',query['kickoff']),
            source_tier=self.protocol['source_tier'],mean=law.mean,mean_type='EXPECTED_MEAN',
            lower_median=law.quantile(.5),median_type='LOWER_MEDIAN',
            law=dict(kind='leaf_mixture',support=law.support.tolist(),weights=law.weights.tolist(),
                     prior=law.prior.parameters(),mixture=law.b),exact_threshold=threshold,
            own_prior_games=d['own_games'],own_history_state='OWN_HISTORY_SUPPORTED' if d['own_games'] else 'NO_OWN_HISTORY_LEAGUE_SUPPORTED',
            latest_consumed_sources=self.bundle.admitted_sources(query),
            fallback=dict(learned_model='RESTORED_TYPED_FOREST',earlier_label_prior_mixture=.05,
                          augmented_missing='FROZEN_ZERO_PLUS_INDICATOR',incumbent_fallback=False),
            probability_status='EXPERIMENTAL_COUNT_LAW_NOT_CALIBRATION_OR_EV',
            consumer_status='ORIGINAL_WEBSITE_SELECTION_READER_IS_MEAN_ONLY;MEDIAN_OR_P2_NEEDS_SEPARATE_VERSIONED_ADMISSION',
            inference_is_issuance=False,original_selection=False,release_qualification='NOT_DECIDED_BY_ADAPTER')

    def predict_historical(self,query,*,feature_names,line=None):
        self._order(feature_names)
        reason=query_validation(query,HISTORICAL_UNIVERSE)
        if reason:
            return self._unavailable(query,'UNAVAILABLE_HISTORICAL_QUERY',reason)
        if (query['season'],query['week'])!=(self.fit_season,self.fit_week):
            return self._unavailable(query,'UNAVAILABLE_HISTORICAL_MODEL','WEEKLY_REFIT_ORIGIN_MISMATCH')
        if self.fit_cutoff>query.get('cutoff',query['kickoff']):
            return self._unavailable(query,'UNAVAILABLE_HISTORICAL_MODEL','MODEL_FIT_AFTER_FEATURE_CUTOFF')
        return self._typed_inference(query,mode='HISTORICAL_RECONSTRUCTED_INFERENCE_NOT_ORIGINAL_ISSUANCE',line=line)

    def _roster_reason(self,query,receipt):
        reason=query_validation(query,'SUPPLIED_QUALIFIED_PREGAME_QUERY_UNIVERSE')
        if reason:return reason
        if not isinstance(receipt,dict):return 'MISSING_EVENT_ROSTER_ADMISSION_RECEIPT'
        fields=dict(player_id=query['player_id'],game_id=query['game_id'],team=query['team'],opponent=query['opponent'],
                    position='QB',season=query['season'],week=query['week'])
        if any(receipt.get(k)!=v for k,v in fields.items()):return 'EVENT_ROSTER_IDENTITY_OR_ROLE_MISMATCH'
        if (not isinstance(query.get('native_event_id'),str) or not query['native_event_id']
            or receipt.get('native_event_id')!=query['native_event_id']
            or receipt.get('admission')!='QUALIFIED_AS_OF_EVENT_DECISION'
            or not _hash(receipt.get('evidence_sha256')) or not _hash(receipt.get('source_sha256'))):
            return 'UNQUALIFIED_EVENT_ROSTER_ADMISSION'
        if receipt['source_sha256']!=query['query_evidence']['source_sha256']:
            return 'QUERY_AND_ROSTER_SOURCE_MISMATCH'
        clocks=('source_effective_at','observed_at','retained_at')
        if not all(_clock(receipt.get(k)) for k in clocks):return 'UNKNOWN_ROSTER_EFFECTIVE_CLOCK'
        cutoff=query.get('cutoff',query['kickoff'])
        if not receipt['source_effective_at']<=receipt['observed_at']<=receipt['retained_at']<=cutoff:
            return 'ROSTER_EFFECTIVE_OR_RETENTION_AFTER_CUTOFF'
        if receipt.get('effective_scope') not in ('MATCHED_EVENT_VERSION','REVIEWED_CARRY_FORWARD_AS_OF_CUTOFF'):
            return 'ROSTER_EFFECTIVE_SCOPE_UNREVIEWED'
        if receipt['effective_scope']=='REVIEWED_CARRY_FORWARD_AS_OF_CUTOFF' and not _hash(receipt.get('carry_forward_evidence_sha256')):
            return 'MISSING_REVIEWED_CARRY_FORWARD_EVIDENCE'
        # Neither actual future participation nor expected starter is required.
        return None

    def _event_reason(self,query,receipt,request_at):
        # Reuse the existing owner's event receipt. A future timestamp typed
        # into a query is not independently verified scheduled status.
        event=receipt.get('event_status_receipt')
        if not isinstance(event,dict):return 'MISSING_CURRENT_EVENT_STATUS_RECEIPT'
        expected=dict(game_id=query['game_id'],native_event_id=query['native_event_id'],season=query['season'],
                      week=query['week'],kickoff=query['kickoff'],state='pre',status_name='STATUS_SCHEDULED',completed=False)
        if any(event.get(k)!=v for k,v in expected.items()) or event.get('completed') is not False:
            return 'CURRENT_EVENT_IDENTITY_OR_STATUS_MISMATCH'
        if (not _hash(event.get('source_sha256')) or not _hash(event.get('expiry_policy_evidence_sha256'))
            or not all(_clock(event.get(k)) for k in ('registered_at','observed_at','expires_at'))):
            return 'UNKNOWN_CURRENT_EVENT_CLOCK_OR_BINDING'
        cutoff=query.get('cutoff',query['kickoff'])
        if not event['registered_at']<=event['observed_at']<=cutoff or event['expires_at']>query['kickoff']:
            return 'CURRENT_EVENT_CLOCK_CONFLICT'
        if not request_at<event['expires_at']:
            return 'REGISTERED_EVENT_STATUS_EXPIRED'
        return None

    def predict_current(self,query,*,feature_names,clock_contract,origin_contract,roster_receipt,request_at,line=None):
        self._order(feature_names)
        reason=self._roster_reason(query,roster_receipt)
        if reason:return self._unavailable(query,'UNAVAILABLE_CURRENT_QUERY',reason)
        cutoff=query.get('cutoff',query['kickoff'])
        if not _clock(request_at) or not cutoff<=request_at<query['kickoff']:
            return self._unavailable(query,'UNAVAILABLE_CURRENT_QUERY','REQUEST_NOT_BEFORE_FUTURE_KICKOFF')
        if (query['season'],query['week'])!=(self.fit_season,self.fit_week):
            return self._unavailable(query,'UNAVAILABLE_CURRENT_MODEL','WEEKLY_REFIT_ORIGIN_MISMATCH')
        if self.model_created_at>request_at or self.fit_cutoff>cutoff:
            return self._unavailable(query,'UNAVAILABLE_CURRENT_MODEL','MODEL_NOT_AVAILABLE_AT_REAL_QUERY_CUTOFF')
        required=dict(refit_rule='WEEKLY_BEFORE_FIRST_ELIGIBLE_GAME_H_RECENT',season=self.fit_season,week=self.fit_week,
                      fit_cutoff=self.fit_cutoff,model_sha256=self.bindings['model_sha256'],
                      protocol_sha256=self.bindings['protocol_sha256'],information_policy=ALTERNATIVE)
        if (not isinstance(origin_contract,dict) or any(origin_contract.get(k)!=v for k,v in required.items())
            or not _hash(origin_contract.get('evidence_sha256'))
            or not _clock(origin_contract.get('registered_at')) or origin_contract['registered_at']>self.fit_cutoff
            or not _clock(origin_contract.get('first_game_kickoff'))
            or not max(self.fit_cutoff,self.model_created_at)<=origin_contract['first_game_kickoff']<=query['kickoff']):
            return self._unavailable(query,'UNAVAILABLE_CURRENT_MODEL','UNQUALIFIED_REGISTERED_WEEKLY_REFIT_CONTRACT')
        reason=self._event_reason(query,roster_receipt,request_at)
        if reason:return self._unavailable(query,'UNAVAILABLE_CURRENT_QUERY',reason)
        clocks=('registered_at','source_received_at','source_cutoff','source_expires_at','model_expires_at')
        if (not isinstance(clock_contract,dict) or not all(_clock(clock_contract.get(k)) for k in clocks)
            or not isinstance(clock_contract.get('policy_id'),str) or not clock_contract['policy_id']
            or not _hash(clock_contract.get('evidence_sha256'))
            or clock_contract.get('inputs_sha256')!=self.bindings['inputs_sha256']
            or clock_contract.get('opportunity_source_sha256')!=self.bindings['opportunity_source_sha256']):
            return self._unavailable(query,'UNAVAILABLE_CURRENT_SOURCE','UNQUALIFIED_REGISTERED_SOURCE_VALIDITY')
        latest_consumed=max((r['available'] for source in (self.inputs,self.opportunity.team_rows,self.opportunity.qb_rows)
                             for r in source if r['available']<cutoff),default=self.model_record['latest_training_label'])
        if not (clock_contract['registered_at']<=cutoff and clock_contract['source_received_at']<=cutoff
                and max(self.model_record['latest_training_label'],latest_consumed)<=clock_contract['source_cutoff']<=cutoff
                and clock_contract['source_received_at']<clock_contract['source_expires_at']):
            return self._unavailable(query,'UNAVAILABLE_CURRENT_SOURCE','SOURCE_VALIDITY_CLOCK_CONFLICT')
        if request_at>=clock_contract['source_expires_at']:
            return self._unavailable(query,'UNAVAILABLE_CURRENT_SOURCE','REGISTERED_SOURCE_EXPIRED')
        if request_at>=clock_contract['model_expires_at']:
            return self._unavailable(query,'UNAVAILABLE_CURRENT_MODEL','REGISTERED_MODEL_EXPIRED')
        result=self._typed_inference(query,mode='CURRENT_ADAPTER_INFERENCE_NOT_CAPTURE_OR_RELEASE',line=line)
        result.update(real_request_at=request_at,clock_contract=dict(clock_contract),origin_contract=dict(origin_contract),
                      roster_admission_evidence_sha256=roster_receipt['evidence_sha256'])
        return result

    def predict_historical_batch(self,queries,*,feature_names,lines=None):
        self._order(feature_names)
        keys=[(q.get('game_id'),q.get('player_id')) for q in queries]
        if len(keys)!=len(set(keys)):raise ValueError('Duplicate query identity')
        lines=[None]*len(queries) if lines is None else lines
        if len(lines)!=len(queries):raise ValueError('Threshold/query width mismatch')
        return [self.predict_historical(q,feature_names=feature_names,line=line) for q,line in zip(queries,lines)]

    def predict_current_batch(self,queries,*,feature_names,clock_contract,origin_contract,roster_receipts,request_at,lines=None):
        self._order(feature_names)
        keys=[(q.get('game_id'),q.get('player_id')) for q in queries]
        if len(keys)!=len(set(keys)):raise ValueError('Duplicate query identity')
        lines=[None]*len(queries) if lines is None else lines
        if len(lines)!=len(queries) or len(roster_receipts)!=len(queries):raise ValueError('Receipt/threshold/query width mismatch')
        return [self.predict_current(q,feature_names=feature_names,clock_contract=clock_contract,origin_contract=origin_contract,
            roster_receipt=r,request_at=request_at,line=line) for q,r,line in zip(queries,roster_receipts,lines)]
