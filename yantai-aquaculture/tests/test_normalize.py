import pytest
from aqua import normalize


def test_to_species_maps_aliases():
    assert normalize.to_species("南美白对虾") == "白虾"
    assert normalize.to_species("口虾蛄") == "皮皮虾"
    assert normalize.to_species("三疣梭子蟹") == "梭子蟹"
    assert normalize.to_species("牡蛎") == "生蚝"


def test_to_species_unknown_raises():
    with pytest.raises(ValueError):
        normalize.to_species("三文鱼")


def test_to_iso_date_formats():
    assert normalize.to_iso_date("2026-09-25") == "2026-09-25"
    assert normalize.to_iso_date("2026/9/5") == "2026-09-05"
    assert normalize.to_iso_date("2026-09") == "2026-09"


def test_to_yuan_per_jin():
    assert normalize.to_yuan_per_jin(44.0, "元/公斤") == 22.0
    assert normalize.to_yuan_per_jin(22.0, "元/斤") == 22.0
    assert normalize.to_yuan_per_jin(44.0, "元/kg") == 22.0


def test_normalize_record():
    raw = {"name": "南美白对虾", "date": "2026/8/15", "price": 40.0,
           "unit": "元/公斤", "source": "moa", "market": "全国均价"}
    rec = normalize.normalize_record(raw)
    assert rec["species"] == "白虾"
    assert rec["date"] == "2026-08-15"
    assert rec["price"] == 20.0
    assert rec["price_low"] is None and rec["price_high"] is None
