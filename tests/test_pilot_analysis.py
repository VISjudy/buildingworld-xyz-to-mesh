import pytest
from harness.pilot_analysis import paired


def row(name, cd=1.0, status='evaluated', topology=True):
    return dict(id=name, stratum='real_zurich', status=status, CD=cd, ECD=cd,
                NC=.8, p95=cd, topology_pass=topology)


def test_recovery_does_not_change_common_success_denominator():
    result = paired([row('a'), row('b', status='failed')], [row('a'), row('b', cd=100)])
    group = result['by_source']['real_zurich']
    assert group['recovered'] == 1 and group['common_success'] == 1
    assert group['paired_mean_delta']['CD'] == 0
    assert result['decision'] == 'eligible_pilot_candidate'


def test_failing_difficult_case_cannot_manufacture_acceptance():
    result = paired([row('a'), row('b', cd=100)], [row('a', cd=.5), row('b', status='failed')])
    assert result['decision'] == 'not_promoted'


def test_recovered_invalid_topology_is_not_accepted():
    result = paired([row('a'), row('b', status='failed')], [row('a'), row('b', topology=False)])
    assert result['decision'] == 'not_promoted'


def test_pair_identity_is_required():
    with pytest.raises(ValueError, match='identical'):
        paired([row('a')], [row('b')])
