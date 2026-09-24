import sqlite3
from aqua import db


def test_connect_creates_tables():
    conn = db.connect(":memory:")
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"price", "import_stat", "news"} <= names


def test_upsert_price_and_dedup():
    conn = db.connect(":memory:")
    rec = {"species": "白虾", "date": "2026-09-01", "price": 22.5,
           "price_low": None, "price_high": None, "source": "test",
           "market": "海阳", "unit": "元/斤"}
    db.upsert_price(conn, rec)
    db.upsert_price(conn, {**rec, "price": 23.0})  # 同键应覆盖
    rows = db.price_series(conn, "白虾")
    assert len(rows) == 1
    assert rows[0]["price"] == 23.0


def test_upsert_import_and_news():
    conn = db.connect(":memory:")
    db.upsert_import(conn, {"ym": "2026-08", "product": "冻虾",
                            "volume_ton": 58000.0, "source": "test"})
    db.upsert_news(conn, {"date": "2026-09-20", "category": "病害",
                          "title": "测试新闻", "summary": "", "url": "",
                          "source": "test"})
    assert db.import_by_month(conn, "冻虾")[0]["volume_ton"] == 58000.0
    assert db.news_list(conn)[0]["title"] == "测试新闻"
