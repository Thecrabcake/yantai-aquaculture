"""全流程入口：各源抓取 → 入库 → CSV 备份。"""
import csv
import pathlib
from . import db
from .sources import moa, customs, manual_price


def run(db_path: str, csv_dir: str = None) -> dict:
    conn = db.connect(db_path)
    stats = {}
    for name, fn in [("moa", moa.run), ("customs", customs.run),
                     ("manual_price", manual_price.run)]:
        try:
            stats[name] = fn(conn)
            print(f"[pipeline] {name}: {stats[name]} 条")
        except Exception as e:  # 单源失败不拖垮整体
            print(f"[pipeline] {name} 失败，跳过: {e}")
            stats[name] = 0
    if csv_dir:
        backup_csv(conn, csv_dir)
    return stats


def backup_csv(conn, csv_dir: str) -> None:
    out = pathlib.Path(csv_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = conn.execute(
        "SELECT species, date, price, price_low, price_high, source, market "
        "FROM price ORDER BY species, date").fetchall()
    with (out / "price.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["species", "date", "price", "price_low", "price_high",
                    "source", "market"])
        w.writerows([tuple(r) for r in rows])
