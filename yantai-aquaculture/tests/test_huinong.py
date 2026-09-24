import pathlib
from aqua import db
from aqua.sources import huinong

FIXTURE = pathlib.Path(__file__).parent.parent / "fixtures" / "cnhnb_hangqing.html"


def test_parse_daily_page():
    text = FIXTURE.read_text(encoding="utf-8", errors="ignore")
    rec = huinong.parse(text, "生蚝")
    assert rec is not None
    assert rec["date"] == "2026-09-24"
    # 产地流通价 1.7~6.05 元/斤，中位数落在区间内
    assert rec["price_low"] <= rec["price"] <= rec["price_high"]
    assert 1.0 <= rec["price"] <= 8.0
    assert rec["source"] == "huinong"


def test_run_imports(tmp_path, monkeypatch):
    text = FIXTURE.read_text(encoding="utf-8", errors="ignore")
    monkeypatch.setattr(huinong.base, "get", lambda url: text)
    conn = db.connect(":memory:")
    n = huinong.run(conn)
    assert n >= 1
    rows = db.price_series(conn, "生蚝")
    assert rows[0]["date"] == "2026-09-24"
