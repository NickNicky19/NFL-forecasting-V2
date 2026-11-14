"""Hash-bound typed adapter for the frozen B opportunity-profile experiment.

Inference is not issuance, capture, admission or deployment. Current query
membership and expiry come from separately retained owner contracts.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
from pathlib import Path

from . import player_context_matchup as ctx
from . import qb_opportunity_increment as inc
from .distribution_laws import prior
from .passing_opportunity_profiles import OpportunityHistory, SOURCE_TIER

VERSION='B-QB-OPPORTUNITY-TYPED-ADAPTER-v1'


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read(path, expected):
    data=Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest()!=expected:
        raise ValueError('Artifact hash mismatch')
    return json.loads(gzip.decompress(data) if str(path).endswith('.gz') else data)


def _clock(value):
    return not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value)


def _identity(query):
    return {k:query.get(k) for k in ('game_id','player_id','team','opponent','season','week','kickoff')}


class QBOpportunityAdapter:
    """Restore explicit JSON arrays and the exact earlier fitted prior.

    `expected_protocol_sha256` and `expected_model_sha256` are trusted caller
    bindings, never inferred from arbitrary uploaded model bytes. The named
    feature order is checked even when a supplied vector has the same width.
    """
    def __init__(self, repository_root, protocol_path, feature_order_path, model_path, *, arm,
                 expected_protocol_sha256, expected_model_sha256):
        self.root=Path(repository_root)
        self.protocol=_read(protocol_path,expected_protocol_sha256)
        if self.protocol['id']!=inc.VERSION or arm not in inc.ARMS:
            raise ValueError('Procedure/arm contract')
        self.arm=arm
        for name,expected in self.protocol['code_sha256'].items():
            if _sha(self.root/name)!=expected:
                raise ValueError('Executing dependency hash mismatch')
        orders=_read(feature_order_path,self.protocol['feature_order_sha256'])
        self.order=tuple(orders['orders'][arm])
        if len(set(self.order))!=len(self.order):
            raise ValueError('Duplicate feature names')
        self.model_record=_read(model_path,expected_model_sha256)
        self.model=self.model_record['model']
        slot=self.model_record['slot']
        expected_suffix='E3' if arm=='R0' else arm
        match=re.fullmatch(r'(\d{4})-W(\d{2})-'+expected_suffix,slot)
        if not match:
            raise ValueError('Fitted model/arm identity mismatch')
        self.fit_season=int(match.group(1))
        self.fit_cutoff=self.model_record['fit_cutoff']
        if not _clock(self.fit_cutoff) or len(self.model['design']['median'])!=len(self.order):
            raise ValueError('Typed fitted feature width/cutoff')
        if self.model_record.get('feature_count',len(self.order))!=len(self.order):
            raise ValueError('Saved feature count mismatch')
        bound_inputs=self.protocol['inputs']; bound_source=self.protocol['source']
        _read(self.root/bound_inputs['path'],bound_inputs['sha256'])
        # The frozen fit loader validates count semantics and sorts by game
        # time/identity before membership hashing. Preserve that exact order.
        self.inputs=ctx.load_inputs(self.root/bound_inputs['path'])
        source=_read(self.root/bound_source['path'],bound_source['sha256'])
        self.history=ctx.ContextHistory(self.inputs,8,20)
        self.opportunity=OpportunityHistory(source['team_games'],source['QB_games'])
        train=[r for r in self.inputs if r['physical_participation'] and r['target_parity']
               and r['season']>=self.fit_season-1 and r['available']<self.fit_cutoff]
        membership=hashlib.sha256(json.dumps([(r['game_id'],r['player_id']) for r in train]).encode()).hexdigest()
        recorded_membership=self.model_record.get('training_membership_sha256')
        if (len(train)!=self.model_record['training_rows']
            or (recorded_membership is not None and membership!=recorded_membership)
            or (recorded_membership is None and arm!='R0')):
            raise ValueError('Earlier training/prior membership mismatch')
        if not train or max(r['available'] for r in train)!=self.model_record['latest_training_label']:
            raise ValueError('Earlier training clock mismatch')
        self.prior=prior([r['official_completions'] for r in train],'pass_cmp')
        self.bindings=dict(procedure_id=inc.VERSION+':'+arm,protocol_sha256=expected_protocol_sha256,
            feature_order_sha256=self.protocol['feature_order_sha256'],model_sha256=expected_model_sha256,
            source_sha256=bound_source['sha256'],inputs_sha256=bound_inputs['sha256'],model_slot=slot,
            fit_cutoff=self.fit_cutoff,latest_training_label=self.model_record['latest_training_label'],
            prior_membership_sha256=membership,feature_count=len(self.order),
            prior_membership_evidence='MATCHES_ORIGINAL_RETAINED_HASH' if recorded_membership is not None
                else 'RECONSTRUCTED_R0_MEMBERSHIP; original artifact retains rowcount/latest clock, not original membership hash')

    @property
    def expected_feature_order(self):
        return list(self.order)

    def _order(self, names):
        if tuple(names)!=self.order:
            raise ValueError('Named feature order mismatch')

    def _unavailable(self, query, state, reason):
        return dict(adapter_version=VERSION,status=state,reason=reason,identity=_identity(query),
                    bindings=self.bindings,inference_is_issuance=False)

    def predict(self, query, *, feature_names, clock_contract, request_at, line=None):
        self._order(feature_names)
        profile=self.opportunity.build_current(query)
        if profile.get('status')=='UNAVAILABLE_PROFILE':
            return self._unavailable(query,'UNAVAILABLE_QUERY',profile['reason'])
        if query['team'] not in self.opportunity_teams or query['opponent'] not in self.opportunity_teams:
            return self._unavailable(query,'UNAVAILABLE_QUERY','UNSUPPORTED_CANONICAL_TEAM')
        cutoff=query.get('cutoff',query['kickoff'])
        # This contract is supplied by the existing owner, not synthesized from
        # source age or from which expiry would permit a prediction.
        required=('registered_at','source_received_at','source_expires_at','model_expires_at')
        if (not isinstance(clock_contract,dict) or not all(_clock(clock_contract.get(k)) for k in required)
            or not isinstance(clock_contract.get('policy_id'),str) or not clock_contract['policy_id']
            or re.fullmatch('[0-9a-f]{64}',str(clock_contract.get('evidence_sha256',''))) is None
            or not _clock(request_at)):
            return self._unavailable(query,'UNAVAILABLE_SOURCE','UNQUALIFIED_REGISTERED_CLOCK_CONTRACT')
        if clock_contract['registered_at']>cutoff or clock_contract['source_received_at']>cutoff:
            return self._unavailable(query,'UNAVAILABLE_SOURCE','CLOCK_CONTRACT_AFTER_QUERY_CUTOFF')
        if request_at<cutoff or clock_contract['source_expires_at']<clock_contract['source_received_at']:
            return self._unavailable(query,'UNAVAILABLE_SOURCE','INVALID_REQUEST_OR_SOURCE_CLOCK')
        if request_at>=clock_contract['source_expires_at']:
            return self._unavailable(query,'UNAVAILABLE_SOURCE','REGISTERED_SOURCE_EXPIRED')
        if request_at>=clock_contract['model_expires_at']:
            return self._unavailable(query,'UNAVAILABLE_MODEL','REGISTERED_MODEL_EXPIRED')
        if self.fit_cutoff>cutoff:
            return self._unavailable(query,'UNAVAILABLE_MODEL','MODEL_FITTED_AFTER_QUERY_CUTOFF')
        # Both old E3 and new profiles receive the same explicit feature cutoff;
        # target kickoff, eventual participation and target outcomes are unread.
        work=dict(query,kickoff=cutoff)
        features=inc.direct_features(work,self.history,self.opportunity,self.arm)
        if len(features)!=len(self.order):
            raise ValueError('Constructed feature width mismatch')
        law=ctx.restored_forest_law(self.model,features,self.prior)
        d=self.history.describe(work)
        threshold=None
        if line is not None:
            if not _clock(line):
                raise ValueError('Nonfinite exact threshold')
            push=law.pmf(line); under=law.cdf(math.ceil(line)-1); over=1-law.cdf(line)
            threshold=dict(line=line,over=over,under=under,push=push,
                mean_direction='Over' if law.mean>line else 'Under' if law.mean<line else 'ABSTAIN',
                median_direction='Over' if law.quantile(.5)>line else 'Under' if law.quantile(.5)<line else 'ABSTAIN',
                probability_direction='Over' if over>under else 'Under' if under>over else 'ABSTAIN',
                evidence='EXACT_THRESHOLD_DIAGNOSTIC_NOT_ORIGINAL_SELECTION_OR_QUALIFIED_OFFER')
        return dict(adapter_version=VERSION,status='READY_ADAPTER_INFERENCE',identity=_identity(query),
            feature_cutoff=cutoff,request_at=request_at,clock_contract=dict(clock_contract),bindings=self.bindings,
            target='pass_cmp',role='QB',source_tier=SOURCE_TIER,
            mean=law.mean,lower_median=law.quantile(.5),
            law=dict(kind='leaf_mixture',support=law.support.tolist(),weights=law.weights.tolist(),
                     prior=law.prior.parameters(),mixture=law.b),exact_threshold=threshold,
            own_history_state='OWN_HISTORY_SUPPORTED' if d['own_games'] else 'UNSEEN_OR_NO_ELIGIBLE_OWN_HISTORY_LEAGUE_SUPPORTED',
            own_prior_games=d['own_games'],last_prior_game=d['last_prior_game'],
            latest_source_available=d['latest_source_available'],
            profile_latest_sources={k:profile[k]['latest_source_available_at'] for k in ('own','offense','defense')},
            fallback=dict(learned_model='RESTORED_TYPED_FOREST',earlier_label_prior_mixture=.05,
                          new_missing_feature_policy='FROZEN_ZERO_PLUS_EXPLICIT_INDICATOR',incumbent_fallback=False),
            inference_is_issuance=False,original_selection=False,release_qualification='NOT_DECIDED_BY_ADAPTER')

    @property
    def opportunity_teams(self):
        from .passing_opportunity_profiles import TEAMS
        return TEAMS

    def predict_batch(self, queries, *, feature_names, clock_contract, request_at, lines=None):
        self._order(feature_names)
        keys=[(q.get('game_id'),q.get('player_id')) for q in queries]
        if len(keys)!=len(set(keys)):
            raise ValueError('Duplicate query identity')
        if lines is None:
            lines=[None]*len(queries)
        if len(lines)!=len(queries):
            raise ValueError('Threshold/query width mismatch')
        return [self.predict(q,feature_names=feature_names,clock_contract=clock_contract,
                             request_at=request_at,line=line) for q,line in zip(queries,lines)]
