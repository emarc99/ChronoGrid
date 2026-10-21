from edge.tracker import Detection, PlacementTracker

KEYS = (0.1, 0.1, 0.2, 0.2)
KEYS_ELSEWHERE = (0.7, 0.7, 0.8, 0.8)


def kinds(events):
    return [(e.kind, e.label) for e in events]


def test_placed_after_stable_hits_only_once():
    t = PlacementTracker(stable_hits=3)
    assert t.update(0, [Detection("keys", 0.8, KEYS)]) == []
    assert t.update(1, [Detection("keys", 0.8, KEYS)]) == []
    assert kinds(t.update(2, [Detection("keys", 0.8, KEYS)])) == [("placed", "keys")]
    assert t.update(3, [Detection("keys", 0.8, KEYS)]) == []


def test_move_reports_new_placement():
    t = PlacementTracker(stable_hits=2)
    for ts in (0, 1):
        t.update(ts, [Detection("keys", 0.8, KEYS)])
    t.update(2, [Detection("keys", 0.8, KEYS_ELSEWHERE)])
    assert kinds(t.update(3, [Detection("keys", 0.8, KEYS_ELSEWHERE)])) == [("placed", "keys")]


def test_removed_after_absence_but_not_when_occluded():
    t = PlacementTracker(stable_hits=1, removed_after=2)
    t.update(0, [Detection("keys", 0.8, KEYS)])
    hand = Detection("person", 0.9, (0.0, 0.0, 0.5, 0.5))
    assert kinds(t.update(5, [hand])) == [("person_enter", None)]
    assert kinds(t.update(9, [])) == [("person_exit", None), ("removed", "keys")]


def test_presence_grace_period():
    t = PlacementTracker(presence_grace=3)
    p = Detection("person", 0.9, (0, 0, 1, 1))
    assert kinds(t.update(0, [p])) == [("person_enter", None)]
    assert t.update(2, []) == []
    assert kinds(t.update(4, [])) == [("person_exit", None)]
