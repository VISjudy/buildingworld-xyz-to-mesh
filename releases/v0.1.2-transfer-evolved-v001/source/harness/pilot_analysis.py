"""Paired pilot summaries: retain failed attempts and never compare changing survivor sets."""
import numpy as np


def summarize(rows):
    result = {}
    for source in sorted({r['stratum'] for r in rows}):
        part = [r for r in rows if r['stratum'] == source]
        ok = [r for r in part if r['status'] == 'evaluated']
        result[source] = {'attempted': len(part), 'success': len(ok), 'failures': len(part) - len(ok),
            'topology_pass': sum(r['topology_pass'] for r in ok),
            'mean_success_only_not_used_for_paired_claim': {
                k: float(np.mean([r[k] for r in ok])) if ok else None for k in ['CD', 'ECD', 'NC', 'p95']}}
    return result


def paired(baseline, candidate):
    b, c = [{r['id']: r for r in rows} for rows in [baseline, candidate]]
    if b.keys() != c.keys():
        raise ValueError('Paired comparison requires identical attempted IDs')
    result = {}
    for source in sorted({r['stratum'] for r in baseline}):
        ids = [k for k, r in b.items() if r['stratum'] == source]
        common = [k for k in ids if b[k]['status'] == c[k]['status'] == 'evaluated']
        result[source] = {'attempted': len(ids), 'common_success': len(common),
            'recovered': sum(b[k]['status'] != 'evaluated' and c[k]['status'] == 'evaluated' for k in ids),
            'new_failures': sum(b[k]['status'] == 'evaluated' and c[k]['status'] != 'evaluated' for k in ids),
            'baseline_failures': sum(b[k]['status'] != 'evaluated' for k in ids),
            'candidate_failures': sum(c[k]['status'] != 'evaluated' for k in ids),
            'new_topology_failures_on_common': sum(b[k]['topology_pass'] and not c[k]['topology_pass'] for k in common),
            'recovered_with_topology_failure': sum(b[k]['status'] != 'evaluated' and c[k]['status'] == 'evaluated' and not c[k]['topology_pass'] for k in ids),
            'paired_mean_delta': {metric: float(np.mean([c[k][metric] - b[k][metric] for k in common]))
                                  if common else None for metric in ['CD', 'ECD', 'NC', 'p95']}}
    eligible = all(r['new_failures'] == r['new_topology_failures_on_common'] == r['recovered_with_topology_failure'] == 0
                   and r['paired_mean_delta']['CD'] is not None
                   and r['paired_mean_delta']['CD'] <= 1e-9 and r['paired_mean_delta']['ECD'] <= 1e-9
                   for r in result.values())
    improved = any(r['recovered'] or (r['paired_mean_delta']['CD'] is not None and
                      (r['paired_mean_delta']['CD'] < -1e-9 or r['paired_mean_delta']['ECD'] < -1e-9)) for r in result.values())
    return {'by_source': result, 'decision': 'eligible_pilot_candidate' if eligible and improved else 'not_promoted',
            'scope': 'paired development evidence, not official score or generalization proof'}
