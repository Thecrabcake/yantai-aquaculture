import json
from aqua import db
from aqua.sources import customs


def test_run_imports_manual_file(tmp_path):
    manual = tmp_path / "import_manual.json"
    manual.write_text(json.dumps([
        {"ym": "2026-07", "product": "冻虾", "volume_ton": 61000,
         "source": "海关月度"},
        {"ym": "2026-08", "product": "冻虾", "volume_ton": 58000,
         "source": "海关月度"},
    ], ensure_ascii=False), encoding="utf-8")
    conn = db.connect(":memory:")
    n = customs.run(conn, path=str(manual))
    assert n == 2
    assert db.import_by_month(conn, "冻虾")[0]["volume_ton"] == 61000
