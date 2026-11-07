"""The fixture scrubber must not keep customer strings."""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "record_fixtures", Path(__file__).resolve().parents[1] / "scripts" / "record_fixtures.py"
)
record_fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(record_fixtures)


def test_scrub_replaces_strings_and_keeps_structure():
    response = {
        "content": [
            {"id": "dv_abc", "name": "Acme Web", "owner": {"name": "Jane Doe", "id": 42},
             "type": "string", "hidden": False, "containerNames": ["visitor", "visit"]},
            {"id": "dv_abc", "description": None, "precision": 2},
        ],
        "lastPage": False,
        "number": 0,
    }

    scrubbed = record_fixtures.Scrubber().scrub(response)

    first, second = scrubbed["content"]
    assert first["name"] == "str_2" and first["owner"]["name"] == "str_3"
    assert first["id"] == second["id"] == "str_1"
    assert first["owner"]["id"] == 42 and first["hidden"] is False
    assert first["type"] == "string"
    assert first["containerNames"] == ["visitor", "visit"]
    assert second["description"] is None and second["precision"] == 2
    assert scrubbed["lastPage"] is False and scrubbed["number"] == 0
    assert "Acme" not in repr(scrubbed) and "Jane" not in repr(scrubbed)
