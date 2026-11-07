"""Versioned cumulative resource wrapper; frozen A/B engine remains unchanged."""
import json,math,resource,signal,time
from pathlib import Path
from . import availability_wave as wave

def cumulative_preflight(ab,planned_c,amendment):
    if ab['actual_fit_calls']!=0:raise ValueError('AB unexpectedly fitted')
    if ab['output_views']+planned_c>amendment['max_cumulative_forecast_rows']:raise ValueError('CUMULATIVE_FORECAST_BUDGET')
    wall=amendment['max_cumulative_active_wall_seconds']-ab['resource']['wall_seconds']
    cpu=amendment['max_cumulative_active_cpu_seconds']-ab['resource']['cpu_seconds']
    if wall<=0 or cpu<=0:raise ValueError('CUMULATIVE_TIME_EXHAUSTED')
    return wall,cpu

def run(source_root,public,private):
    public,private=Path(public),Path(private);amendment=json.loads((public/'C-RESOURCE-AMENDMENT.json').read_text());ab=json.loads((public/'AB-RUN_RECEIPT.json').read_text());protocol=json.loads((public/'FROZEN_PROTOCOL.json').read_text())
    if wave.sha(__file__)!=amendment['wrapper_code_sha256'] or wave.sha(public/'AB-RUN_RECEIPT.json')!=amendment['AB_receipt_sha256'] or wave.sha(public/'FROZEN_PROTOCOL.json')!=amendment['original_protocol_sha256']:raise ValueError('guard amendment changed')
    remaining_wall,remaining_cpu=cumulative_preflight(ab,amendment['planned_C_output_views'],amendment)
    if amendment['max_fit_calls']!=protocol['budget']['max_fit_calls']:raise ValueError('fit budget change forbidden')
    def timeout(signum,frame):raise RuntimeError('CUMULATIVE_ACTIVE_WALL_BUDGET')
    signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,remaining_wall)
    consumed_cpu=time.process_time();limit=math.ceil(consumed_cpu+remaining_cpu);resource.setrlimit(resource.RLIMIT_CPU,(limit,limit+1))
    result=wave.run(source_root,public,private,refits=True);signal.setitimer(signal.ITIMER_REAL,0)
    if result['output_views']+ab['output_views']>amendment['max_cumulative_forecast_rows']:raise ValueError('actual cumulative rows')
    if result['resource']['wall_seconds']+ab['resource']['wall_seconds']>amendment['max_cumulative_active_wall_seconds']:raise ValueError('actual cumulative wall')
    if result['resource']['cpu_seconds']+ab['resource']['cpu_seconds']>amendment['max_cumulative_active_cpu_seconds']:raise ValueError('actual cumulative CPU')
    wave.save_json(public/'CUMULATIVE_RESOURCE_RECEIPT.json',dict(state='PASS_WITH_REGISTERED_C_AMENDMENT',actual_completed_at=wave.now(),amendment_sha256=wave.sha(public/'C-RESOURCE-AMENDMENT.json'),actual_cumulative_forecast_views=ab['output_views']+result['output_views'],actual_cumulative_active_wall_seconds=ab['resource']['wall_seconds']+result['resource']['wall_seconds'],actual_cumulative_active_cpu_seconds=ab['resource']['cpu_seconds']+result['resource']['cpu_seconds'],actual_cumulative_fit_calls=result['actual_fit_calls'],coordination_wait='excluded from active process resource budget; real wall timestamps retained, no backdating'))
    return result
