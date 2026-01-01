from termdash.sources.base import DataPoint


def test_data_point_defaults():
    point = DataPoint(title="Test", value="42")
    assert point.status == "ok"
    assert point.detail == ""
    assert point.updated_at is not None
