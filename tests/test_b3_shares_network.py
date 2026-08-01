from decifra.b3.shares import _pick_number, fetch_b3_share_detail


def test_pick_number_br_format():
    assert _pick_number({"totalShares": "1.234.567"}, ("totalShares",)) == 1234567.0


def test_fetch_b3_share_detail_no_ids_empty():
    assert fetch_b3_share_detail() == {}
