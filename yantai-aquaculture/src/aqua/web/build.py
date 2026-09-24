"""静态站点生成：SQLite → site/。模板用 __XXX__ 占位符替换，无模板引擎。"""
import json
import pathlib
import urllib.request
from .. import config, db

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATES = HERE / "templates"
ECHARTS_URL = ("https://registry.npmmirror.com/echarts/5.5.0/"
               "files/dist/echarts.min.js")

# 看板 tab：大类（数据厚）+ 品种（随人工周录积累）
TABS = ["虾蟹类", "白虾", "皮皮虾", "梭子蟹", "生蚝", "贝类"]


def _vendor_echarts(out: pathlib.Path) -> None:
    """下载 echarts.min.js 到 site/assets（本地优先，不依赖 CDN）。"""
    target = out / "assets" / "echarts.min.js"
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(ECHARTS_URL, timeout=60) as r:
        target.write_bytes(r.read())
    print(f"[build] echarts 已下载: {target}")


def build(db_path: str, out_dir: str) -> None:
    conn = db.connect(db_path)
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    _vendor_echarts(out)

    series = {s: db.price_series(conn, s) for s in TABS}
    imports = db.import_by_month(conn, "暖水虾")

    (out / "index.html").write_text(
        (TEMPLATES / "index.html").read_text(encoding="utf-8")
        .replace("__PRICE_SERIES__", json.dumps(series, ensure_ascii=False))
        .replace("__IMPORTS__", json.dumps(imports, ensure_ascii=False))
        .replace("__HOLIDAYS__", json.dumps(config.HOLIDAYS, ensure_ascii=False))
        .replace("__TABS__", json.dumps(TABS, ensure_ascii=False)),
        encoding="utf-8",
    )
    (out / "forecast.html").write_text(
        (TEMPLATES / "forecast.html").read_text(encoding="utf-8")
        .replace("__PRICE_SERIES__", json.dumps(series, ensure_ascii=False))
        .replace("__SCENARIOS__", json.dumps(config.SCENARIOS, ensure_ascii=False)),
        encoding="utf-8",
    )
    print(f"[build] site 已生成: {out}")
