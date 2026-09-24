from aqua import db
from aqua.web import build


def test_build_generates_index_with_data(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.upsert_price(conn, {"species": "白虾", "date": "2026-08-15",
                           "price": 22.0, "price_low": None,
                           "price_high": None, "source": "test",
                           "market": "海阳", "unit": "元/斤"})
    conn.commit()
    out = tmp_path / "site"
    build.build(str(tmp_path / "t.db"), str(out))
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "白虾" in html
    assert "虾蟹类" in html       # 大类与品种都在 tab 里
    assert "echarts.min.js" in html
    assert '"price": 22.0' in html


def test_build_generates_forecast(tmp_path):
    conn = db.connect(str(tmp_path / "t2.db"))
    conn.commit()
    out = tmp_path / "site2"
    build.build(str(tmp_path / "t2.db"), str(out))
    html = (out / "forecast.html").read_text(encoding="utf-8")
    assert "历史统计" in html
    assert "不构成预测保证" in html


def test_build_generates_news(tmp_path):
    conn = db.connect(str(tmp_path / "t3.db"))
    db.upsert_news(conn, {"date": "2026-09-20", "category": "病害",
                          "title": "某地白斑病抬头", "summary": "摘要",
                          "url": "", "source": "人工周选"})
    conn.commit()
    out = tmp_path / "site3"
    build.build(str(tmp_path / "t3.db"), str(out))
    html = (out / "news.html").read_text(encoding="utf-8")
    assert "某地白斑病抬头" in html


def test_build_generates_cost(tmp_path):
    conn = db.connect(str(tmp_path / "t4.db"))
    conn.commit()
    out = tmp_path / "site4"
    build.build(str(tmp_path / "t4.db"), str(out))
    html = (out / "cost.html").read_text(encoding="utf-8")
    assert "保本价" in html
    assert "miao_price" in html      # COST_DEFAULTS 已内嵌
