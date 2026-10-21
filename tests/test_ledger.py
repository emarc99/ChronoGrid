from server.ledger import Ledger


def make_ledger() -> Ledger:
    ledger = Ledger(":memory:")
    ledger.upsert_zone("workbench", "Workbench", "bench", [[0, 0], [0.5, 0], [0.5, 1], [0, 1]])
    ledger.upsert_zone("drawer-2", "Drawer 2", "storage", [[0.5, 0], [1, 0], [1, 1], [0.5, 1]])
    return ledger


def test_placed_in_new_zone_becomes_move():
    ledger = make_ledger()
    ledger.record_event("placed", "Multimeter", "workbench", ts=100)
    moved = ledger.record_event("placed", "multimeter", "drawer-2", ts=200)
    assert moved.kind == "moved"
    assert moved.from_zone == "workbench"
    assert ledger.object_state("multimeter")["zone_id"] == "drawer-2"


def test_zone_for_point_and_resolve():
    ledger = make_ledger()
    assert ledger.zone_for_point(0.2, 0.5) == "workbench"
    assert ledger.zone_for_point(0.8, 0.5) == "drawer-2"
    assert ledger.resolve_zone("the bench") == "workbench"
    assert ledger.resolve_zone("drawer two") == "drawer-2"


def test_resolve_label_fuzzy():
    ledger = make_ledger()
    ledger.record_event("placed", "safety goggles", "workbench", ts=1)
    assert ledger.resolve_label("my goggles") == "safety goggles"
    assert ledger.resolve_label("saftey goggles") == "safety goggles"


def test_commit_and_diff():
    ledger = make_ledger()
    ledger.record_event("placed", "multimeter", "workbench", ts=1)
    ledger.record_event("placed", "pliers", "workbench", ts=2)
    ledger.commit("workbench", "clean bench", ts=3)
    ledger.record_event("placed", "multimeter", "drawer-2", ts=4)
    ledger.record_event("placed", "mug", "workbench", ts=5)
    diff = ledger.diff("workbench")
    assert diff["added"] == ["mug"]
    assert diff["removed"][0]["label"] == "multimeter"
    assert diff["removed"][0]["now_in"] == "drawer-2"
    assert diff["unchanged"] == ["pliers"]


def test_diff_since_timestamp():
    ledger = make_ledger()
    ledger.record_event("placed", "keys", "workbench", ts=10)
    ledger.record_event("removed", "keys", "workbench", ts=20)
    diff = ledger.diff("workbench", since=15)
    assert diff["removed"][0]["label"] == "keys"


def test_presence_since_only_changes_on_transition():
    ledger = make_ledger()
    ledger.record_event("person_enter", zone_id="workbench", ts=10)
    ledger.record_event("person_enter", zone_id="workbench", ts=20)
    assert ledger.presence("workbench")["since"] == 10
    ledger.record_event("person_exit", zone_id="workbench", ts=30)
    assert ledger.presence("workbench") == {"zone_id": "workbench", "present": False, "since": 30}


def test_activity_grid_counts_events():
    ledger = make_ledger()
    now = 10 * 3600 + 100
    ledger.record_event("placed", "mug", "workbench", ts=now - 10)
    ledger.record_event("placed", "pen", "drawer-2", ts=now - 3600)
    grid = ledger.activity_grid(hours=3, now=now)
    assert grid["counts"]["workbench"][-1] == 1
    assert grid["counts"]["drawer-2"][-2] == 1
