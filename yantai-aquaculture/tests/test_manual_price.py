from aqua import db
from aqua.sources import manual_price


def test_run_imports_and_normalizes(tmp_path):
    f = tmp_path / "price_manual.json"
    f.write_text(
        '[{"name": "南美白对虾", "date": "2026-09-20", "price": 26.0,'
        ' "unit": "元/斤", "market": "中山批发", "source": "人工周录"},'
        ' {"name": "梭子蟹", "date": "2026-09-21", "price": 55.0,'
        ' "unit": "元/公斤", "market": "无锡", "source": "人工周录"}]',
        encoding="utf-8")
    conn = db.connect(":memory:")
    n = manual_price.run(conn, path=str(f))
    assert n == 2
    rows = db.price_series(conn, "白虾")
    assert rows[0]["price"] == 26.0
    crab = db.price_series(conn, "梭子蟹")
    assert crab[0]["price"] == 27.5  # 公斤价减半
