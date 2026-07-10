"""Archetype profiles — "ไอเทมชิ้นนี้เหมาะกับตัวประเภทไหน"

นี่คือไฟล์จูนหลักของทั้งระบบ: น้ำหนัก (weight) ของแต่ละ stat ต่อบทบาท
ถูกตั้งจากคำอธิบายการใช้งานจริงของผู้ใช้ (GVG meta) และ *ควรถูกปรับ*
เมื่อใช้จริงแล้วรู้สึกว่าคำตัดสินเพี้ยน — ปรับที่นี่ที่เดียว logic ไม่ต้องแตะ

weight ความหมาย:
    1.0  = stat หัวใจของบทบาทนี้
    0.5  = มีประโยชน์ชัดเจนแต่ไม่ใช่แกน
    0.2-0.3 = ได้ก็ดี (nice to have)
    0.0  = ไร้ค่าในบทบาทนี้ (ช่องทิ้ง)
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Profile:
    code: str
    name_th: str
    context: str                     # "PVP" | "PVE" | "PVP/PVE"
    weights: dict[str, float]        # stat code -> weight (0..1)
    sets: frozenset[str]             # เซ็ตที่บิลด์สายนี้ใช้จริง
    note: str = ""


# fmt: off
PROFILES: list[Profile] = [
    Profile(
        code="crit_dps_pvp",
        name_th="DPS สายจุดอ่อน (PVP)",
        context="PVP",
        weights={
            # meta จริง (ยืนยันจากผู้ใช้ 2026-07): งบ stat ถูก SPD + WK 100
            # กินก่อน → CDM แทบไม่เหลือที่ลง, CR กลาง ๆ (บางตัวยังต้องทำ)
            "SPD": 1.0, "WK": 1.0,
            "CR": 0.6, "CDM": 0.35,
            "ATK": 0.6,            # รวม Attack % / Flat (flat ถูกลดทอนใน scoring)
            "ERes": 0.3,           # "บางตัวต้องทำต้านทานกันติดดีบัฟ"
        },
        sets=frozenset({"Assassin", "Bounty Tracker", "Vanguard"}),
        note="เปิดก่อนด้วย SPD + ทำจุดอ่อนให้ตัน 100; คริ/คริดาเมจได้เท่าที่งบเหลือ",
    ),
    Profile(
        code="certain_crit_pvp",
        name_th="DPS คริแน่นอน 100% จากพาสซีฟ (PVP)",
        context="PVP",
        weights={
            # ตัวที่พาสซีฟการันตีคริ 100%: CR จากอุปกรณ์ = stat ตาย (0)
            # งบทั้งหมดเทให้ SPD/WK/CDM ได้เต็มที่
            "SPD": 1.0, "WK": 1.0, "CDM": 1.0,
            "CR": 0.0,
            "ATK": 0.6,
            "ERes": 0.3,
        },
        sets=frozenset({"Assassin", "Bounty Tracker", "Vanguard", "Avenger"}),
        note="เฉพาะตัวที่มีพาสซีฟคริแน่นอน; top player ใช้เซ็ตผู้ล้างแค้น (ไฮดร้า) "
             "กับตัวแบบนี้ใน PVP เพราะโบนัส CR ของเซ็ตนักฆ่าเสียเปล่า",
    ),
    Profile(
        code="death_pvp",
        name_th="ทีมเดธ (PVP)",
        context="PVP",
        weights={
            # ข้อมูล top player: EHR 75-90 + SPD 83-97 + ถึกได้ยิ่งดี (RED 32-42)
            "SPD": 1.0, "EHR": 1.0,
            "RED": 0.9,
            "HP": 0.5, "DEF": 0.5,
            "ERes": 0.3,
        },
        sets=frozenset({"Spellweaver"}),
        note="เน้นสปีด + เข้าเป้าเยอะ ๆ ยิ่งถึกได้ด้วยยิ่งดี (เซ็ตแม่นยำ)",
    ),
    Profile(
        code="pve_dps",
        name_th="DPS ตีบอส (PVE)",
        context="PVE",
        weights={
            "CR": 1.0, "CDM": 1.0, "WK": 0.9, "ATK": 0.7,
            "SPD": 0.4,            # "สปีดติดมาบ้างนิดหน่อยได้"
        },
        sets=frozenset({"Avenger"}),
        note="เซ็ตผู้ล้างแค้น: เน้นคริ/คริดาเมจ/จุดอ่อน สปีดรองลงมา",
    ),
    Profile(
        code="debuffer_pvp",
        name_th="สายเปิดเกม/ดีบัฟ (PVP)",
        context="PVP",
        weights={
            "SPD": 1.0, "EHR": 1.0,
            "HP": 0.25, "ERes": 0.25,   # กันตายก่อนได้เปิดสกิล
        },
        sets=frozenset({"Spellweaver", "Vanguard"}),
        note="ต้องเร็วพอเปิดก่อน + EHR สูงพอชนะ ERes ศัตรู (meta ~100)",
    ),
    Profile(
        code="tank",
        name_th="สายถึก/ฮีลเลอร์ (PVP/PVE)",
        context="PVP/PVE",
        weights={
            "HP": 1.0, "DEF": 1.0, "BLK": 0.9, "ERes": 0.9,
            "EHR": 0.5,            # ผู้ใช้ระบุว่าสายถึกก็อยากได้เข้าเป้าด้วย
            "SPD": 0.15,           # ข้อมูล top player: ทีมถึก SPD 25-33 = ไม่ลงทุน
            "RED": 1.0,
        },
        sets=frozenset({"Paladin", "Gatekeeper", "Guardian", "Orchestrator"}),
        note="HP/DEF/บล็อค/ต้านทาน/ลดความเสียหาย; ฮีลเลอร์สาย Paladin ฮีลแรงตาม HP",
    ),
]
# fmt: on

PROFILE_BY_CODE = {p.code: p for p in PROFILES}


def profiles_for_set(set_code: str) -> list[Profile]:
    """โปรไฟล์ที่ 'เข้ากัน' กับเซ็ตนี้จริง — set gating

    เหตุผล: ชิ้น substat สายแทงค์บนเซ็ตนักฆ่า ต่อให้ roll สวยก็ใช้จริงไม่ได้
    เพราะบิลด์จริงต้องการทั้ง set bonus และ stat ไปทางเดียวกัน
    """
    return [p for p in PROFILES if set_code in p.sets]
