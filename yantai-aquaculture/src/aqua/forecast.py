"""出虾窗口价格统计：预测器核心。给区间不给点。"""
from statistics import quantiles
from . import db


def _in_window(md: str, start: str, end: str) -> bool:
    """md='mm-dd'；start>end 视为跨年窗口。"""
    if start <= end:
        return start <= md <= end
    return md >= start or md <= end


def window_stats(conn, species: str, start_md: str, end_md: str,
                 years: int = 5) -> dict:
    """近 years 年内落在 [start_md, end_md] 窗口的价格统计。"""
    rows = db.price_series(conn, species)
    sel = [r for r in rows if _in_window(r["date"][5:10], start_md, end_md)]
    if not sel:
        return {"count": 0}
    prices = sorted(r["price"] for r in sel)
    q = quantiles(prices, n=4)  # [p25, p50, p75]
    by_year: dict[str, list] = {}
    cross = start_md > end_md
    for r in sel:
        y = int(r["date"][:4])
        # 跨年窗口：12 月记录归入次年（出虾年）
        if cross and r["date"][5:10] >= start_md:
            y += 1
        by_year.setdefault(str(y), []).append(r["price"])
    return {
        "count": len(sel),
        "median": round(q[1], 2),
        "p25": round(q[0], 2),
        "p75": round(q[2], 2),
        "min": min(prices),
        "max": max(prices),
        "by_year": {y: {"count": len(v),
                        "avg": round(sum(v) / len(v), 2)}
                    for y, v in sorted(by_year.items())},
    }
