"""Tests: validation invariants + scoring sanity checks.

หลักการเทสต์ scoring: ไม่เทสต์ตัวเลขคะแนนเป๊ะ ๆ (เพราะ weight จะถูกจูน)
แต่เทสต์ "ความสัมพันธ์" ที่ต้องจริงเสมอ เช่น ชิ้นเทพต้องชนะชิ้นขยะ,
เซ็ตผิดสายต้องไม่ถูกประเมินกับโปรไฟล์นั้น — เทสต์แบบนี้ทนต่อการจูน weight
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import constants as C
from models import Item, Substat, validate_item
from profiles import PROFILE_BY_CODE, profiles_for_set
from scoring import evaluate, score_profile


def make(slot="offense", set_code="Assassin", main="Attack %", subs=None) -> Item:
    subs = subs or [
        ("Crit Rate", 12),        # 3 rolls (+2)
        ("Crit Damage", 12),      # 2 rolls (+1)
        ("Speed", 12),            # 3 rolls (+2)
        ("Effect Resistance", 5), # 1 roll  (+0)   รวม extra = 5 ✓
    ]
    return Item(slot, set_code, main, tuple(Substat(t, v) for t, v in subs))


# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------
class TestValidation:
    def test_valid_item_passes(self):
        assert validate_item(make()) == []

    def test_value_not_multiple_of_base(self):
        item = make(subs=[("Crit Rate", 13), ("Crit Damage", 12),
                          ("Speed", 12), ("Effect Resistance", 5)])
        errors = validate_item(item)
        assert any("พหุคูณ" in e for e in errors)

    def test_total_rolls_must_be_five(self):
        item = make(subs=[("Crit Rate", 4), ("Crit Damage", 6),
                          ("Speed", 4), ("Effect Resistance", 5)])  # extra = 0
        errors = validate_item(item)
        assert any("roll เพิ่มรวม" in e for e in errors)

    def test_duplicate_substat_rejected(self):
        item = make(subs=[("Crit Rate", 12), ("Crit Rate", 12),
                          ("Speed", 12), ("Effect Resistance", 5)])
        assert any("ห้ามซ้ำชนิด" in e for e in validate_item(item))

    def test_sub_may_duplicate_main(self):
        """กฎเกมจริง: substat ซ้ำชนิดกับ main ได้ (ยืนยันจากผู้ใช้)"""
        item = make(main="Crit Rate",
                    subs=[("Crit Rate", 12), ("Crit Damage", 12),
                          ("Speed", 12), ("Effect Resistance", 5)])
        assert validate_item(item) == []

    def test_illegal_main_for_slot(self):
        item = make(slot="defense", main="Crit Rate")
        assert any("ใช้กับชิ้น defense ไม่ได้" in e for e in validate_item(item))


# ---------------------------------------------------------------------------
# roll normalization
# ---------------------------------------------------------------------------
def test_roll_equivalent():
    assert Substat("Speed", 12).roll_equivalent == 3
    assert Substat("Crit Damage", 6).roll_equivalent == 1
    assert Substat("Attack %", 25).roll_equivalent == 5


# ---------------------------------------------------------------------------
# scoring relationships
# ---------------------------------------------------------------------------
class TestScoring:
    def test_god_piece_beats_junk_piece(self):
        god = make(main="Crit Damage",
                   subs=[("Crit Rate", 12), ("Speed", 16),
                         ("Attack %", 10), ("Weakness Hit Chance", 5)])
        junk = make(main="HP Flat",
                    subs=[("Defense Flat", 120), ("HP Flat", 360),
                          ("Block Rate", 4), ("Effect Resistance", 5)])
        assert evaluate(god).best.score > evaluate(junk).best.score

    def test_set_gating(self):
        """เซ็ตนักฆ่าต้องไม่ถูกประเมินกับโปรไฟล์สายถึก และกลับกัน"""
        codes = {p.code for p in profiles_for_set("Assassin")}
        assert "tank" not in codes
        codes = {p.code for p in profiles_for_set("Guardian")}
        assert codes == {"tank"}

    def test_all_sets_have_at_least_one_profile(self):
        for s in C.SET_NAMES:
            assert profiles_for_set(s), f"set {s} ไม่มีโปรไฟล์รองรับ"

    def test_tank_piece_scores_high_on_tank_profile(self):
        item = make(slot="defense", set_code="Guardian", main="Damage Taken Reduction",
                    subs=[("HP %", 15), ("Defense %", 10),
                          ("Block Rate", 8), ("Effect Resistance", 10)])
        fit = score_profile(item, PROFILE_BY_CODE["tank"])
        assert fit.score >= 0.65

    def test_score_bounded_zero_one(self):
        v = evaluate(make())
        for f in v.fits:
            assert 0.0 <= f.score <= 1.0

    def test_verdict_has_thai_reasoning(self):
        v = evaluate(make())
        assert v.reasoning and any("เซ็ต" in line for line in v.reasoning)

    def test_flat_penalty_applies(self):
        """ATK flat ต้องมีค่าน้อยกว่า ATK% ที่ roll เท่ากันในสาย DPS"""
        pct = make(subs=[("Attack %", 15), ("Crit Damage", 12),
                         ("Speed", 8), ("Effect Resistance", 5)])
        flat = make(subs=[("Attack Flat", 150), ("Crit Damage", 12),
                          ("Speed", 8), ("Effect Resistance", 5)])
        p = PROFILE_BY_CODE["crit_dps_pvp"]
        assert score_profile(pct, p).sub_score > score_profile(flat, p).sub_score

    def test_dead_roll_guard_caps_grade(self):
        """เคสจริงจากผู้ใช้: main CDM เทพ แต่ HP%/HP flat กิน 4/9 rolls
        → ห้ามเกิน B แม้คะแนนดิบจะแตะ A"""
        item = make(set_code="Vanguard", main="Crit Damage",
                    subs=[("Crit Damage", 18), ("Speed", 8),
                          ("HP %", 15), ("HP Flat", 180)])
        v = evaluate(item)
        assert v.grade == "B"
        assert any("dead-roll guard" in line for line in v.reasoning)

    def test_dead_roll_guard_spares_good_piece(self):
        """ชิ้นเทพตาม meta ใหม่ (main WK, subs SPD/WK/CR/ATK%) ต้องไม่โดน guard"""
        item = make(main="Weakness Hit Chance",
                    subs=[("Speed", 12), ("Weakness Hit Chance", 15),
                          ("Attack %", 5), ("Crit Rate", 8)])
        v = evaluate(item)
        assert v.grade == "S"
        assert not any("dead-roll guard" in line for line in v.reasoning)

    def test_certain_crit_profile_kills_cr_value(self):
        """ตัวคริแน่นอน 100%: CR จากอุปกรณ์ต้องเป็น stat ตาย (weight 0)
        ชิ้น CDM หนักต้องชนะชิ้น CR หนักในโปรไฟล์นี้"""
        p = PROFILE_BY_CODE["certain_crit_pvp"]
        cdm_piece = make(main="Crit Damage",
                         subs=[("Crit Damage", 24), ("Speed", 12),
                               ("Attack %", 5), ("Weakness Hit Chance", 5)])
        cr_piece = make(main="Crit Rate",
                        subs=[("Crit Rate", 16), ("Speed", 12),
                              ("Attack %", 5), ("Weakness Hit Chance", 5)])
        assert score_profile(cdm_piece, p).score > score_profile(cr_piece, p).score

    def test_dead_roll_guard_three_dead_rolls(self):
        """เคสจริงจากผู้ใช้ #2: เซ็ตจุดอ่อน main ATK% + CDM/SPD ดี
        แต่ DEF flat + HP flat กิน 3/9 rolls → ห้ามเกิน B
        (S/A ต้องทิ้งไม่เกิน 2 จาก 9 rolls)"""
        item = make(set_code="Bounty Tracker", main="Attack %",
                    subs=[("Crit Damage", 18), ("Speed", 12),
                          ("Defense Flat", 60), ("HP Flat", 180)])
        assert validate_item(item) == []
        v = evaluate(item)
        assert v.grade == "B"
        assert any("dead-roll guard" in line for line in v.reasoning)

    def test_speed_carry_floor(self):
        """ชิ้น SPD 4 rolls บนเซ็ต/ช่องอื่นทิ้ง ต้องได้อย่างน้อย B
        (ผู้เล่นยำเซ็ตเพื่อชิ้นแบกสปีด — ยืนยันจากผู้ใช้)"""
        item = make(slot="defense", set_code="Guardian", main="HP Flat",
                    subs=[("Speed", 16), ("Attack Flat", 150),
                          ("Crit Damage", 6), ("Weakness Hit Chance", 5)])
        assert validate_item(item) == []
        v = evaluate(item)
        assert v.grade in ("S", "A", "B")
        assert any("speed-carry" in line for line in v.reasoning)

    def test_death_team_profile_on_spellweaver(self):
        """ชิ้นหมอผี EHR+SPD+ถึก ต้องเข้าโปรไฟล์ทีมเดธได้คะแนนดี"""
        item = make(slot="defense", set_code="Spellweaver",
                    main="Damage Taken Reduction",
                    subs=[("Effect Hit Rate", 15), ("Speed", 12),
                          ("HP %", 10), ("Defense Flat", 30)])
        v = evaluate(item)
        codes = {f.profile.code for f in v.fits}
        assert "death_pvp" in codes
        assert v.grade in ("S", "A")

    def test_reroll_advice_on_user_case(self):
        """เคสจริงจากผู้ใช้ #3: นายประตู main HP% + sub HP% 20 (4 rolls)
        ช่องอื่นทิ้ง → เกรด B พร้อมคำแนะนำล็อก HP% แล้วหลอมใหม่"""
        item = make(slot="defense", set_code="Gatekeeper", main="HP %",
                    subs=[("HP %", 20), ("Attack Flat", 50),
                          ("Block Rate", 4), ("Speed", 12)])
        assert validate_item(item) == []
        v = evaluate(item)
        assert v.grade == "B"
        assert "หลอมใหม่" in v.decision and "HP %" in v.decision
        assert any("หลอมใหม่" in line for line in v.reasoning)

    def test_no_reroll_advice_on_top_grade(self):
        """ชิ้น S ดีอยู่แล้ว ห้ามแนะนำให้เสี่ยงหลอม"""
        item = make(main="Weakness Hit Chance",
                    subs=[("Speed", 12), ("Weakness Hit Chance", 15),
                          ("Attack %", 5), ("Crit Rate", 8)])
        v = evaluate(item)
        assert v.grade == "S"
        assert "หลอมใหม่" not in v.decision


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
