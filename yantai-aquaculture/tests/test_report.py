from aqua import db
from aqua.web import report


def test_generate_report(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.upsert_price(conn, {"species": "白虾", "date": "2026-09-01",
                           "price": 22.0, "price_low": None,
                           "price_high": None, "source": "test",
                           "market": "海阳", "unit": "元/斤"})
    db.upsert_news(conn, {"date": "2026-09-20", "category": "病害",
                          "title": "测试", "summary": "", "url": "",
                          "source": "test"})
    conn.commit()
    path = report.generate(str(tmp_path / "t.db"), "2026-09", str(tmp_path))
    html = open(path, encoding="utf-8").read()
    assert "2026年9月" in html and "白虾" in html and "测试" in html
