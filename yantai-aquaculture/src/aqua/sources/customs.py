"""月度虾类进口量：人工录入 JSON → 入库。

海关官方统计需交互式查询，采用人工月度录入：
每月维护者把"冻虾进口量（吨）"写进 data/import_manual.json。
"""
import json
import pathlib

from .. import db

DEFAULT_PATH = pathlib.Path(__file__).resolve().parents[3] / "data" / "import_manual.json"


def run(conn, path=None) -> int:
    p = pathlib.Path(path) if path else DEFAULT_PATH
    if not p.exists():
        print(f"[customs] 未找到 {p}，跳过（首次运行先建立该文件）")
        return 0
    data = json.loads(p.read_text(encoding="utf-8"))
    for rec in data:
        db.upsert_import(conn, rec)
    conn.commit()
    return len(data)
