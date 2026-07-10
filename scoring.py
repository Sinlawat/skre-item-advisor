"""Scoring engine — ตัดสิน เก็บ/ขาย และบอกว่าเหมาะกับตัวประเภทไหน

หลักการ 4 ขั้น:
  1. Normalize   แปลงทุก substat เป็นหน่วยกลาง "roll equivalent"
  2. Saturate    stat ที่ตัน (CR/WK/BLK ตัน 100) นับเฉพาะส่วนที่ยังไม่เกินเพดาน
                 โดยหักของฟรี (innate + โบนัสเซ็ตของชิ้นนั้น) ออกก่อน
  3. Score       ให้คะแนนต่อโปรไฟล์ = main_fit 35% + sub_efficiency 65%
                 เทียบกับ "ชิ้นในฝัน" ของโปรไฟล์นั้น (คะแนนเลยเป็น 0..1 เสมอ)
  4. Gate        คิดเฉพาะโปรไฟล์ที่เข้ากับเซ็ตของชิ้น แล้วเอาคะแนนสูงสุดตัดสิน

ทุก threshold/สัดส่วน อยู่ด้านบนไฟล์ — จูนได้โดยไม่แตะ logic
"""
from __future__ import annotations

from dataclasses import dataclass, field

import constants as C
from models import Item
from profiles import Profile, profiles_for_set

# ---------------------------------------------------------------------------
# ค่าจูนได้
# ---------------------------------------------------------------------------
MAIN_WEIGHT = 0.35        # สัดส่วนคะแนนจาก main stat
SUB_WEIGHT = 0.65         # สัดส่วนคะแนนจาก substats

# Flat stat (Attack/Defense/HP Flat) ด้อยกว่าแบบ % ในช่วงท้ายเกม
# เพราะ % สเกลตามค่าฐานตัวละคร — ลดทอนคุณค่าต่อ roll ลง
FLAT_PENALTY = {"Attack Flat": 0.4, "Defense Flat": 0.4, "HP Flat": 0.4}

GRADES = [  # (คะแนนขั้นต่ำ, เกรด, คำตัดสิน)
    (0.80, "S", "เก็บ — ของเทพ ใช้งานทันที"),
    (0.65, "A", "เก็บ — ดีมาก ใช้งานได้เลย"),
    (0.50, "B", "เก็บเผื่อ — ใช้ได้ระหว่างรอชิ้นดีกว่า"),
    (0.35, "C", "ขายได้ — ต่ำกว่ามาตรฐาน เก็บเฉพาะช่วงต้นเกม"),
    (0.00, "F", "ขาย — ไม่มีบทบาทไหนใช้คุ้ม"),
]

# Dead-roll guard: กัน main สวยลากชิ้นที่ substat ทิ้งเยอะขึ้นเกรดสูง
# roll ที่ weight ต่ำกว่า DEAD_WEIGHT ถือว่า "ทิ้ง"; ถ้าทิ้งเกิน WASTED_CAP
# ของ roll ทั้งชิ้น เกรดสูงสุดถูกจำกัดที่ B (เก็บเผื่อ)
# 0.30 = ทิ้งได้ไม่เกิน 2 จาก 9 rolls ถึงจะมีสิทธิ์ S/A
# (จูนจาก feedback ผู้ใช้ 2 เคส: ชิ้นทิ้ง 3-4 rolls ไม่ควรได้ "ใช้งานทันที")
DEAD_WEIGHT = 0.2
WASTED_CAP = 0.30

# Speed-carry rule: SPD มีแต่ใน substat (ไม่มีใน main pool) ชิ้นสปีดสูงจึงหายาก
# และผู้เล่นระดับสูงใช้ "ยำเซ็ต" เอาชิ้นสปีดสูงสุดมาแบกสปีดทีมโดยไม่สนเซ็ต
# → SPD >= SPEED_CARRY_MIN การันตีเกรดขั้นต่ำ B เสมอ
SPEED_CARRY_MIN = 16   # = 4 rolls

# Reroll advice: เกมมีระบบรีค่า substat โดยล็อกเก็บได้ 1 ค่า แล้วสุ่ม 3 ช่องใหม่
# ชิ้นเกรด B/C/F ที่มี substat "น่าล็อก" จึงควรเก็บไว้หลอม ไม่ใช่ขาย
# น่าล็อก = อยู่ใน stat แกนของสาย (weight สูง) และ roll สูงพอให้คุ้มเสี่ยงสุ่ม
REROLL_MIN_WEIGHT = 0.5   # ต้องเป็น stat แกนของโปรไฟล์ที่ดีที่สุด
REROLL_MIN_ROLLS = 3      # ค่าอย่างน้อย 3 rolls ถึงคุ้มล็อก
REROLL_SUGGEST_N = 4      # จำนวนค่าที่แนะนำให้หวังตอนสุ่ม


# ---------------------------------------------------------------------------
# Result objects
# ---------------------------------------------------------------------------
@dataclass
class ProfileFit:
    profile: Profile
    score: float                    # 0..1
    main_fit: float                 # 0..1
    sub_score: float                # 0..1
    wasted_fraction: float = 0.0    # สัดส่วน roll ของ substat ที่ "ทิ้ง"
    notes: list[str] = field(default_factory=list)


@dataclass
class Verdict:
    item: Item
    grade: str
    decision: str
    best: ProfileFit | None
    fits: list[ProfileFit]          # เรียงคะแนนมากไปน้อย
    reasoning: list[str]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _effective_weight(profile: Profile, opt_type: str) -> float:
    """weight ของ option หนึ่ง ๆ ในโปรไฟล์ = weight ของ stat x โทษ flat"""
    stat = C.OPTION_TARGET[opt_type]
    return profile.weights.get(stat, 0.0) * FLAT_PENALTY.get(opt_type, 1.0)


def _cap_headroom(item: Item, stat: str) -> float:
    """เพดานที่เหลือของ stat ที่ตัน หลังหักของฟรี (innate + โบนัสเซ็ตชิ้นนี้)

    ตัวอย่าง: ชิ้นเซ็ตนักฆ่า (CR +30) -> headroom CR = 100 - 5(innate) - 30 = 65
    หมายเหตุ: transcend flat (+18 CR ฯลฯ) ขึ้นกับตัวละคร จึงไม่หักตรงนี้
    แต่จะเตือนใน reasoning แทน
    """
    cap = C.CAPPED_STATS[stat]
    innate = C.INNATE_BASE.get(stat, 0)
    set_bonus = C.SETS[item.set_code][1].get(stat, 0)
    return max(cap - innate - set_bonus, 0.0)


def _capped_scale(item: Item, stat: str, notes: list[str]) -> float:
    """สัดส่วน (0..1) ของ stat ที่ตัน ที่ 'ยังนับได้' บนชิ้นนี้

    ถ้าชิ้นเดียวให้ stat นั้นเกิน headroom ส่วนเกินไร้ค่า -> ลดคะแนนตามสัดส่วน
    (กรณีจริงชิ้นเดียวมักไม่เกิน แต่กันไว้ + แจ้งเตือนภาพรวมบิลด์)
    """
    contribution = 0.0
    if item.main_stat == stat:
        contribution += item.main_value
    for s in item.substats:
        if s.stat == stat:
            contribution += s.value
    if contribution <= 0:
        return 1.0

    headroom = _cap_headroom(item, stat)
    if contribution > headroom:
        notes.append(
            f"⚠ {stat} จากชิ้นนี้ ({contribution:g}) เกินเพดานที่เหลือ "
            f"({headroom:g}) — ส่วนเกินไร้ค่า"
        )
        return headroom / contribution
    return 1.0


def _ideal_sub_score(profile: Profile, item: Item) -> float:
    """คะแนน substat ของ 'ชิ้นในฝัน' สำหรับโปรไฟล์นี้ (ตัวหารของ efficiency)

    ชิ้นในฝัน = เลือก 4 substat ชนิดที่ weight สูงสุด (ซ้ำ main ได้
    ตามกฎเกมจริง) ได้ base คนละ 1 roll แล้วเท roll เพิ่มทั้ง 5 ให้ชนิดที่
    weight สูงสุด
    """
    ws = sorted(
        (_effective_weight(profile, t) for t in C.SUBSTAT_TYPES),
        reverse=True,
    )[: C.SUBSTATS_PER_PIECE]
    return sum(ws) + C.ROLLS_PER_PIECE * ws[0] if ws else 1.0


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------
def score_profile(item: Item, profile: Profile) -> ProfileFit:
    notes: list[str] = []

    # scale ของ stat ที่ตัน (คำนวณครั้งเดียวต่อ stat)
    cap_scale = {stat: _capped_scale(item, stat, notes) for stat in C.CAPPED_STATS}

    # --- main fit: weight ของ main เทียบ weight สูงสุดในโปรไฟล์ ---
    max_w = max(profile.weights.values())
    main_w = _effective_weight(profile, item.main_type)
    main_w *= cap_scale.get(item.main_stat, 1.0)
    main_fit = main_w / max_w if max_w > 0 else 0.0

    # --- substat efficiency + สัดส่วน roll ที่ทิ้ง ---
    raw = 0.0
    total_rolls = 0.0
    wasted_rolls = 0.0
    for s in item.substats:
        w = _effective_weight(profile, s.type)
        w *= cap_scale.get(s.stat, 1.0)
        raw += w * s.roll_equivalent
        total_rolls += s.roll_equivalent
        if w < DEAD_WEIGHT:
            wasted_rolls += s.roll_equivalent
    sub_score = min(raw / _ideal_sub_score(profile, item), 1.0)
    wasted_fraction = wasted_rolls / total_rolls if total_rolls else 0.0

    score = MAIN_WEIGHT * main_fit + SUB_WEIGHT * sub_score
    return ProfileFit(profile, score, main_fit, sub_score, wasted_fraction, notes)


def _reroll_advice(item: Item, best: ProfileFit) -> tuple[str, list[str]] | None:
    """หา substat ที่คุ้มล็อกไว้แล้วสุ่มช่องที่เหลือใหม่ (ระบบรีค่าในเกม)

    คืน (ข้อความต่อท้ายคำตัดสิน, บรรทัดเหตุผล) หรือ None ถ้าไม่มีค่าน่าล็อก
    เลือก keeper จากค่า weight x rolls สูงสุด ที่ผ่านเกณฑ์ขั้นต่ำทั้งสองข้อ
    """
    profile = best.profile
    keeper = None
    keeper_value = 0.0
    for s in item.substats:
        w = _effective_weight(profile, s.type)
        if w >= REROLL_MIN_WEIGHT and s.roll_equivalent >= REROLL_MIN_ROLLS:
            v = w * s.roll_equivalent
            if v > keeper_value:
                keeper, keeper_value = s, v
    if keeper is None:
        return None

    # ค่าที่ควรหวังตอนสุ่ม: substat weight สูงสุดของสายนี้ (ห้ามซ้ำ keeper)
    candidates = sorted(
        ((t, _effective_weight(profile, t)) for t in C.SUBSTAT_TYPES
         if t != keeper.type),
        key=lambda kv: kv[1],
        reverse=True,
    )
    wishlist = [t for t, w in candidates[:REROLL_SUGGEST_N] if w > 0]

    suffix = f" → เก็บไว้รอหลอมใหม่ (ล็อก {keeper.type} {keeper.value:g})"
    lines = [
        f"🔁 หลอมใหม่: ล็อก {keeper.type} {keeper.value:g} "
        f"({keeper.roll_equivalent:g} rolls ใน stat แกนของ{profile.name_th}) "
        f"แล้วสุ่ม 3 ช่องที่เหลือ",
        f"   ค่าที่ควรหวัง: {', '.join(wishlist)}",
    ]
    return suffix, lines


def evaluate(item: Item) -> Verdict:
    """ประเมินไอเทม 1 ชิ้น -> เกรด + คำตัดสิน + เหตุผลรายบรรทัด (ไทย)"""
    profiles = profiles_for_set(item.set_code)
    fits = sorted(
        (score_profile(item, p) for p in profiles),
        key=lambda f: f.score,
        reverse=True,
    )

    reasoning: list[str] = []
    set_th = C.SET_THAI[item.set_code]

    if not fits:
        return Verdict(item, "F", "ขาย — เซ็ตนี้ไม่มีบทบาทที่รองรับ", None, [], reasoning)

    best = fits[0]

    # --- สรุปรายละเอียด substat ต่อโปรไฟล์ที่ดีที่สุด ---
    reasoning.append(
        f"เซ็ต {set_th} → ประเมินกับบทบาท: "
        + ", ".join(f.profile.name_th for f in fits)
    )
    for s in item.substats:
        w = _effective_weight(best.profile, s.type)
        tag = "✓ ตรงสาย" if w >= 0.5 else ("~ พอได้" if w > 0 else "✗ ช่องทิ้ง")
        reasoning.append(
            f"  {tag}  {s.type} {s.value:g} = {s.roll_equivalent:g} rolls "
            f"(weight {w:.2f} ใน {best.profile.name_th})"
        )
    main_w = _effective_weight(best.profile, item.main_type)
    reasoning.append(
        f"  main {item.main_type} {item.main_value} → weight {main_w:.2f}"
    )

    # --- แจ้งเตือนเชิงบริบท ---
    for f in fits:
        reasoning.extend(f.notes)

    for stat in C.CAPPED_STATS:
        has = item.main_stat == stat or any(s.stat == stat for s in item.substats)
        if has:
            free = C.INNATE_BASE.get(stat, 0) + C.SETS[item.set_code][1].get(stat, 0)
            reasoning.append(
                f"ℹ {stat} ตันที่ 100 — เซ็ต+innate ให้ฟรี {free:g} แล้ว "
                f"อย่าลืมนับ transcend flat และชิ้นอื่นตอนประกอบบิลด์จริง"
            )
    if any(s.stat == "EHR" for s in item.substats) or item.main_stat == "EHR":
        reasoning.append(
            f"ℹ meta ปัจจุบัน: ศัตรูสายถึกต้าน ~{C.META_ENEMY_ERES} — "
            "สายดีบัฟต้องสะสม EHR สูง แต้ม EHR จึงมีค่าเต็ม"
        )

    # --- เกรด ---
    grade, decision = "F", GRADES[-1][2]
    for threshold, g, d in GRADES:
        if best.score >= threshold:
            grade, decision = g, d
            break

    # Dead-roll guard: main สวยห้ามลากชิ้นที่ substat ทิ้งเยอะขึ้น S/A
    # เหตุผล: substat คืองบ roll ส่วนใหญ่ของชิ้น ถ้าทิ้งเกิน WASTED_CAP
    # แปลว่าชิ้นนี้ "ใช้ไปก่อนได้" แต่ไม่ใช่ชิ้นปลายทาง
    if grade in ("S", "A") and best.wasted_fraction >= WASTED_CAP:
        grade, decision = "B", "เก็บเผื่อ — main ดี แต่ substat ทิ้งเยอะ รอชิ้นดีกว่ามาแทน"
        reasoning.append(
            f"⚠ dead-roll guard: substat ทิ้ง {best.wasted_fraction * 100:.0f}% "
            f"ของ roll ทั้งชิ้น (เกิน {WASTED_CAP * 100:.0f}%) → จำกัดเกรดที่ B"
        )

    # Speed-carry rule: ชิ้น SPD สูงมาก มีค่าแบกสปีดทีมโดยไม่สนเซ็ต
    # (SPD ไม่มีใน main pool จึงหาได้จาก substat เท่านั้น — ของหายาก)
    spd = max((s.value for s in item.substats if s.stat == "SPD"), default=0)
    if spd >= SPEED_CARRY_MIN and grade in ("C", "F"):
        grade = "B"
        decision = "เก็บ — ชิ้นแบกสปีด (Speed สูงใช้ได้ไม่สนเซ็ต)"
        reasoning.append(
            f"★ speed-carry: Speed {spd:g} (≥ {SPEED_CARRY_MIN}) หายากมาก — "
            "ผู้เล่นระดับสูงยำเซ็ตเพื่อชิ้นแบบนี้ → ยกเกรดขั้นต่ำเป็น B"
        )

    # Reroll advice: ชิ้นยังไม่ถึง S/A แต่มีค่าน่าล็อก → เก็บไว้หลอมใหม่
    if grade in ("B", "C", "F"):
        advice = _reroll_advice(item, best)
        if advice:
            suffix, lines = advice
            decision += suffix
            reasoning.extend(lines)

    return Verdict(item, grade, decision, best, fits, reasoning)
