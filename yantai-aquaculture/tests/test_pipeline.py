from aqua import db, pipeline


def test_run_skips_failed_source_and_backs_up(tmp_path, monkeypatch):
    def boom(conn):
        raise RuntimeError("源挂了")
    monkeypatch.setattr("aqua.sources.moa.run", boom)

    def ok(conn):
        db.upsert_price(conn, {"species": "白虾", "date": "2026-09-01",
                               "price": 22.0, "price_low": None,
                               "price_high": None, "source": "test",
                               "market": "海阳", "unit": "元/斤"})
        conn.commit()
        return 1
    monkeypatch.setattr("aqua.sources.manual_price.run", ok)
    monkeypatch.setattr("aqua.sources.customs.run", lambda conn, path=None: 0)
    monkeypatch.setattr("aqua.newsman.run", lambda conn, path=None: 0)

    db_path = str(tmp_path / "test.db")
    result = pipeline.run(db_path, csv_dir=str(tmp_path))
    assert result["moa"] == 0        # 失败源记 0，不抛异常
    assert result["manual_price"] == 1
    csvs = list(tmp_path.glob("*.csv"))
    assert len(csvs) >= 1            # 备份已生成
