"""The contract's test list (CONTRACTS.md section 4). Runs under pytest or unittest."""

import itertools
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chalk_engine import TEMPLATES, build_play, counter_play, mirror, narrate, parse_rules, template_catalog, validate  # noqa: E402
from chalk_engine.court import AGE_GROUPS, PLAYERS_PER_SIDE, SIDES, dist  # noqa: E402

HERE = os.path.dirname(__file__)
COUNTERS = {
    "pick_and_roll": ["switch", "hedge", "drop", "zone"],
    "pick_and_pop": ["switch", "hedge", "drop", "zone"],
    "backdoor_cut": ["switch", "zone"],
    "give_and_go": ["switch", "zone"],
    "dribble_handoff": ["switch", "hedge", "zone"],
    "flare_screen": ["switch", "zone"],
    "horns": ["switch", "hedge", "drop", "zone"],
    "fast_break_3v2": [],
}


def every_combo():
    for tid, side, n, age in itertools.product(TEMPLATES, SIDES, PLAYERS_PER_SIDE, AGE_GROUPS):
        yield tid, {"side": side, "players_per_side": n, "age_group": age}


class TestTemplates(unittest.TestCase):
    def test_exactly_the_eight_templates_with_their_counters(self):
        self.assertEqual(set(TEMPLATES), set(COUNTERS))
        for tid, counters in COUNTERS.items():
            self.assertEqual(TEMPLATES[tid].counters, counters, tid)

    def test_every_template_side_players_age_builds_a_valid_play(self):
        for tid, params in every_combo():
            play = build_play(tid, params)
            self.assertTrue(play["validity"]["ok"], (tid, params, play["validity"]["issues"]))
            self.assertEqual(play["validity"], validate(play))
            self.assertEqual(play["defence"], "man")
            self.assertEqual(play["params"]["side"], params["side"])
            self.assertEqual(len(play["players"]), 2 * params["players_per_side"])

    def test_every_declared_counter_builds_a_valid_play(self):
        for tid, params in every_combo():
            base = build_play(tid, params)
            for defence in base["counters"]:
                play = counter_play(base, defence)
                self.assertTrue(play["validity"]["ok"], (tid, defence, params, play["validity"]["issues"]))
                self.assertEqual(play["defence"], defence)
                self.assertEqual(play["id"], base["id"] + "-" + defence)
                self.assertTrue(play["name"].endswith(" vs " + defence))
                self.assertEqual(play["template"], base["template"])
                self.assertEqual(play["params"], base["params"])
                # offense is unchanged; only defenders and reads move
                for b0, b1 in zip(base["beats"], play["beats"]):
                    for pid, xy in b0["positions"].items():
                        if pid.startswith("P"):
                            self.assertEqual(b1["positions"][pid], xy, (tid, defence, b0["index"], pid))
                    self.assertEqual(b0["ball"], b1["ball"])
                    self.assertEqual(b0["t"], b1["t"])

    def test_counter_rejects_unknown_defence(self):
        with self.assertRaises(ValueError):
            counter_play(build_play("fast_break_3v2", {}), "switch")
        with self.assertRaises(ValueError):
            build_play("triangle", {})

    def test_play_json_shape_and_reads(self):
        for tid, params in every_combo():
            play = build_play(tid, params)
            beats = play["beats"]
            self.assertTrue(3 <= len(beats) <= 6, tid)
            self.assertEqual(beats[0]["t"], 0)
            self.assertEqual(beats[0]["index"], 0)
            self.assertEqual(play["id"][:4], "ply_")
            self.assertEqual(len(play["id"]), 10)
            for prev, b in zip(beats, beats[1:]):
                self.assertGreater(b["t"], prev["t"], tid)
                self.assertEqual(b["index"], prev["index"] + 1)
                for pid, path in b["paths"].items():
                    self.assertEqual(path[0], prev["positions"][pid], (tid, pid))
                    self.assertEqual(path[-1], b["positions"][pid], (tid, pid))
            for b in beats:
                self.assertLess(len(b["read"]), 140, (tid, b["read"]))
                self.assertLess(len(b["title"]), 24, (tid, b["title"]))
                if isinstance(b["ball"], dict):
                    self.assertEqual(b["pass"], b["ball"])
                else:
                    self.assertIsNone(b["pass"])

    def test_age_group_scales_timing(self):
        u8 = build_play("pick_and_roll", {"age_group": "u8"})["beats"][-1]["t"]
        u16 = build_play("pick_and_roll", {"age_group": "u16"})["beats"][-1]["t"]
        self.assertGreater(u8, u16)

    def test_three_v_three_remaps_roles_and_says_so(self):
        play = build_play("pick_and_roll", {"players_per_side": 3})
        self.assertEqual(play["params"]["screener"], "P3")
        self.assertIn("3v3", play["description"])
        self.assertEqual({p["id"] for p in play["players"]}, {"P1", "P2", "P3", "D1", "D2", "D3"})

    def test_plays_look_like_basketball(self):
        """Setup spacing is realistic and finishes end near the basket."""
        for tid in TEMPLATES:
            play = build_play(tid, {})
            setup = play["beats"][0]["positions"]
            offense = [pid for pid in setup if pid.startswith("P")]
            for pid in offense:
                nearest = min(dist(setup[pid], setup[q]) for q in offense if q != pid)
                low = 6 if tid == "fast_break_3v2" else 12
                self.assertTrue(low <= nearest <= 18.5, (tid, pid, nearest))
            last = play["beats"][-1]
            holder = last["ball"]
            if last["title"] == "Layup":
                self.assertLess(dist(last["positions"][holder], (25, 5.25)), 6, tid)


class TestValidator(unittest.TestCase):
    def test_catches_every_issue_code(self):
        play = build_play("give_and_go", {})
        play["beats"][1]["positions"]["P1"] = [-1, 10]
        play["beats"][2]["positions"]["P2"] = play["beats"][2]["positions"]["P3"]
        play["beats"][3]["positions"]["P4"] = [45, 45]
        play["beats"][4]["ball"] = {"from": "P9", "to": "P1"}
        del play["beats"][4]["positions"]["P5"]
        codes = {i["code"] for i in validate(play)["issues"]}
        self.assertEqual(codes, {"out_of_bounds", "overlap", "too_fast", "ball_orphan", "missing_player"})


class TestRulesParser(unittest.TestCase):
    def test_forty_fixture_phrasings(self):
        with open(os.path.join(HERE, "phrasings.json")) as f:
            fixtures = json.load(f)
        self.assertEqual(len(fixtures), 40)
        for fx in fixtures:
            got = parse_rules(fx["text"])
            self.assertIsNotNone(got, fx["text"])
            self.assertEqual(got["template"], fx["template"], fx["text"])
            for key, value in fx["params"].items():
                self.assertEqual(got["params"].get(key), value, (fx["text"], key))
            self.assertTrue(0 < got["confidence"] <= 1)
            build_play(got["template"], got["params"])  # parsed params always build

    def test_non_basketball_text_is_none(self):
        self.assertIsNone(parse_rules("what time is practice on thursday"))
        self.assertIsNone(parse_rules(""))


class TestMirrorAndCatalog(unittest.TestCase):
    def test_mirror_is_an_involution(self):
        for tid, params in every_combo():
            play = build_play(tid, params)
            flipped = mirror(play)
            self.assertNotEqual(flipped["params"]["side"], play["params"]["side"])
            self.assertEqual(mirror(flipped), play, tid)
            self.assertTrue(validate(flipped)["ok"], tid)

    def test_catalog(self):
        cat = template_catalog()
        self.assertEqual([c["id"] for c in cat], list(TEMPLATES))
        for c in cat:
            self.assertEqual(set(c), {"id", "name", "summary", "params_schema", "counters"})
            self.assertIn("side", c["params_schema"]["properties"])

    def test_narrate_glosses_once_per_play(self):
        play = build_play("pick_and_roll", {})
        glossed = [b["read"] for b in play["beats"] if "(stand still" in b["read"]]
        self.assertEqual(len(glossed), 1)
        self.assertIs(narrate(play), play)


class TestTimingAndWording(unittest.TestCase):
    def test_every_beat_lasts_1_5_to_3_seconds_at_every_age(self):
        for tid, params in every_combo():
            beats = build_play(tid, params)["beats"]
            for prev, b in zip(beats, beats[1:]):
                self.assertTrue(1.5 <= b["t"] - prev["t"] <= 3.0, (tid, params["age_group"], b["index"], b["t"] - prev["t"]))

    def test_reads_only_use_left_and_right_for_the_side(self):
        # mirror() swaps the words, so "right away" or "left behind" would mirror into nonsense
        import re
        banned = re.compile(r"\b(right (away|there|now|past)|left (behind|out|over))\b")
        for tid in TEMPLATES:
            base = build_play(tid, {})
            for defence in ["man"] + base["counters"]:
                play = base if defence == "man" else counter_play(base, defence)
                for b in play["beats"]:
                    self.assertIsNone(banned.search(b["read"]), (tid, defence, b["read"]))


if __name__ == "__main__":
    unittest.main()
