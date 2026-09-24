"""人工新闻周选：data/news_manual.json → 入库（按日期+标题去重）。"""
import json
import pathlib
from . import db

DEFAULT_PATH = pathlib.Path(__file__).resolve().parents[2] / "data" / "news_manual.json"


def run(conn, path=None) -> int:
    p = pathlib.Path(path) if path else DEFAULT_PATH
    if not p.exists():
        print(f"[newsman] 未找到 {p}，跳过")
        return 0
    items = json.loads(p.read_text(encoding="utf-8"))
    existing = {(r["date"], r["title"]) for r in db.news_list(conn)}
    n = 0
    for rec in items:
        if (rec["date"], rec["title"]) in existing:
            continue
        db.upsert_news(conn, rec)
        n += 1
    conn.commit()
    return n
