from aqua.sources import base, moa


def test_parse_moa_fixture():
    """zjbhi 转载农业农村部月报：虾蟹类/贝类大类均价（元/公斤→元/斤）。"""
    text = base.load_fixture("zjbhi_sample.html")
    records = moa.parse(text)
    assert len(records) >= 2
    species = {r["species"] for r in records}
    assert {"虾蟹类", "贝类"} <= species
    for r in records:
        assert r["date"].startswith("2026-07-")
        assert r["price"] > 0
        assert r["unit"] == "元/斤"
        assert r["source"] == "moa"
    shrimp = next(r for r in records if r["species"] == "虾蟹类")
    assert shrimp["price"] == 32.4  # 64.80元/公斤 ÷ 2
    shell = next(r for r in records if r["species"] == "贝类")
    assert shell["price"] == 10.05  # 20.10元/公斤 ÷ 2


def test_parse_import_from_fixture():
    text = base.load_fixture("zjbhi_sample.html")
    imp = moa.parse_import(text)
    assert imp["ym"] == "2026-06"  # 文中为6月份进口数据
    assert imp["product"] == "水产品"
    assert imp["volume_ton"] == 558000.0  # 55.80万吨
