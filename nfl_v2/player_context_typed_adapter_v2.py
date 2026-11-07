"""Source-bound portable consumer: coefficient order is explicit, never JSON order."""
import copy

from .player_context_matchup import CompletionModel, VERSION

ADAPTER_VERSION = 'B-QB-CONTEXT-TYPED-ADAPTER-v2'
LEVEL_ORDER = ('team', 'opponent', 'player_id')


def restore_completion(payload, *, producer_version):
    if producer_version != VERSION:
        raise ValueError('Exact supported producer recipe required')
    expected = ('team', 'opponent', 'player_id') if payload.get('personalized') else ('team', 'opponent')
    if set(payload.get('levels', {})) != set(expected):
        raise ValueError('Coefficient group contract')
    # The v1 producer fits in this fixed field order. JSON mappings may reorder
    # object keys; keep coefficient-vector semantics from the bound producer.
    ordered = copy.deepcopy(payload)
    ordered['levels'] = {key: ordered['levels'][key] for key in expected}
    return CompletionModel.restore(ordered)


def schema_binding():
    return dict(adapter_version=ADAPTER_VERSION, producer_version=VERSION,
                base_columns=29, coefficient_level_order=list(LEVEL_ORDER),
                unknown_level='Zero learned categorical deviation; registered shared fallback remains separate.',
                numeric_outputs='Expected count, lower median and exact count-law parameters are distinct products.',
                scope='Output-preserving consumer correction for the exact v1 producer; no model refit or new five-week evidence claim.')
