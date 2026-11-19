import json

from nutrinin.store import RecordStore


def test_record_store_loads_and_searches_records(tmp_path):
    path = tmp_path / "records.json"
    path.write_text(json.dumps([{"id": "A1", "title": "Iron"}]), encoding="utf-8")

    store = RecordStore(path)

    assert store.ready is False
    assert store.load() == 1
    assert store.ready is True
    assert store.search("iron") == [{"id": "A1", "title": "Iron"}]
    assert store.get("A1") == {"id": "A1", "title": "Iron"}
