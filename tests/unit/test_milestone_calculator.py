from app.core.utils.milestone_calculator import parse_milestone_key, get_applicable_milestones


def test_parse_milestone_key():
    assert parse_milestone_key(15) == "15m"
    assert parse_milestone_key(60) == "1h"
    assert parse_milestone_key(120) == "2h"
    assert parse_milestone_key(1440) == "1d"
    assert parse_milestone_key(2880) == "2d"


def test_get_applicable_milestones():
    config = [15, 60, 1440]
    # Còn 10 phút -> chạm cả 3 mốc (15m, 60m, 1440m)
    res = get_applicable_milestones(10 * 60, config)
    assert len(res) == 3

    # Còn 30 phút -> chỉ chạm mốc 60m và 1440m
    res2 = get_applicable_milestones(30 * 60, config)
    assert len(res2) == 2
    assert (15, "15m") not in res2
