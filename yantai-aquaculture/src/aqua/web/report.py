"""月报一页纸：SQLite → site/月报-YYYY-MM.html，微信可直接转发。"""
import json
import pathlib
from .. import db
from .build import TEMPLATES, TABS


def _shift(ym: str, delta: int) -> str:
    """ym='2026-09'，delta 月偏移 → '2026-08' / '2025-09'。"""
    y, m = int(ym[:4]), int(ym[5:7])
    idx = y * 12 + (m - 1) + delta
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}"


def _avg(rows: list[dict]) -> float | None:
    if not rows:
        return None
    return round(sum(r["price"] for r in rows) / len(rows), 1)


def _fmt(v: float | None) -> str:
    return "—" if v is None else f"{v:.1f}"


def _pct(cur: float | None, base: float | None) -> str:
    if cur is None or not base:
        return "—"
    return f"{(cur - base) / base * 100:+.1f}%"


def generate(db_path: str, ym: str, out_dir: str) -> str:
    conn = db.connect(db_path)
    prev, yoy = _shift(ym, -1), _shift(ym, -12)
    y, m = int(ym[:4]), int(ym[5:7])

    rows = []
    for sp in TABS:
        series = db.price_series(conn, sp)
        cur = _avg([r for r in series if r["date"].startswith(ym)])
        base_p = _avg([r for r in series if r["date"].startswith(prev)])
        base_y = _avg([r for r in series if r["date"].startswith(yoy)])
        rows.append({"species": sp, "cur": _fmt(cur),
                     "mom": _pct(cur, base_p), "yoy": _pct(cur, base_y)})

    news = [n for n in db.news_list(conn) if n["date"].startswith(ym)]
    imports = [r for r in db.import_by_month(conn, "暖水虾")
               if r["ym"].startswith(ym)]

    # 数据驱动的一句话点评（可手动改写）
    main = next((r for r in rows if r["cur"] != "—"), None)
    if main:
        comment = (f"本月{main['species']}均价 {main['cur']} 元/斤"
                   f"（环比 {main['mom']}）；收录要闻 {len(news)} 条。")
    else:
        comment = f"本月暂无价格数据；收录要闻 {len(news)} 条。"

    html = (TEMPLATES / "report.html").read_text(encoding="utf-8")
    html = (html
            .replace("__TITLE__", f"{y}年{m}月")
            .replace("__ROWS__", json.dumps(rows, ensure_ascii=False))
            .replace("__NEWS__", json.dumps(news, ensure_ascii=False))
            .replace("__IMPORTS__", json.dumps(imports, ensure_ascii=False))
            .replace("__COMMENT__", comment))
    out = pathlib.Path(out_dir) / f"月报-{ym}.html"
    out.write_text(html, encoding="utf-8")
    print(f"[report] 月报已生成: {out}")
    return str(out)
