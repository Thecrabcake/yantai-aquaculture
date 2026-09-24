import json
from aqua import db, newsman


def test_run_imports_and_dedups(tmp_path):
    f = tmp_path / "news_manual.json"
    f.write_text(json.dumps([
        {"date": "2026-09-20", "category": "病害", "title": "某地白斑病",
         "summary": "内容摘要", "url": "https://example.com/1",
         "source": "人工周选"},
    ], ensure_ascii=False), encoding="utf-8")
    conn = db.connect(":memory:")
    assert newsman.run(conn, path=str(f)) == 1
    assert newsman.run(conn, path=str(f)) == 0  # 重复运行不再入库
    assert db.news_list(conn)[0]["category"] == "病害"
