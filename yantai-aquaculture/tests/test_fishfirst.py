import pathlib
from aqua import db
from aqua.sources import fishfirst

FIXTURE = pathlib.Path(__file__).parent.parent / "fixtures" / "ff_126587.html"


def test_parse_article_white_shrimp():
    text = FIXTURE.read_text(encoding="utf-8", errors="ignore")
    rec = fishfirst.parse_article(text, "最高跌4元/斤！对虾全线跌价，元旦")
    assert rec is not None
    assert rec["species"] == "白虾"
    assert rec["date"] == "2024-12-19"
    # 正文报价在 15~23 元/斤区间，中位数应落在区间内
    assert rec["price_low"] <= rec["price"] <= rec["price_high"]
    assert 10 <= rec["price"] <= 25
    assert rec["source"] == "fishfirst"


def test_parse_article_rejects_feed_title():
    text = FIXTURE.read_text(encoding="utf-8", errors="ignore")
    # 饲料涨价类标题不含品种，应返回 None
    assert fishfirst.parse_article(text, "水产料涨200元/吨！新一轮涨价潮") is None


def test_run_imports(tmp_path, monkeypatch):
    text = FIXTURE.read_text(encoding="utf-8", errors="ignore")
    monkeypatch.setattr(fishfirst, "_fetch_list",
                        lambda: [("http://x/article-1.html",
                                  "对虾全线跌价")])
    monkeypatch.setattr(fishfirst.base, "get", lambda url: text)
    conn = db.connect(":memory:")
    n = fishfirst.run(conn)
    assert n == 1
    rows = db.price_series(conn, "白虾")
    assert rows[0]["date"] == "2024-12-19"
