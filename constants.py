"""Game constants for SKRE Item Advisor.

ค่าตัวเลขทั้งหมดยกมาจากโปรเจกต์ Builder-Optimize-7K (reverse-engineered จาก
SKRE Build Maker BETA.4) เพื่อให้สองโปรเจกต์ใช้ตัวเลขชุดเดียวกัน

Stat codes: ATK DEF HP SPD CR CDM WK BLK RED EHR ERes
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Stat codes
# ---------------------------------------------------------------------------
STATS = ["ATK", "DEF", "HP", "SPD", "CR", "CDM", "WK", "BLK", "RED", "EHR", "ERes"]

# Stat ที่ "ตัน" (cap) ที่ 100% — แต้มที่เกินไม่มีค่า
CAPPED_STATS = {"CR": 100, "WK": 100, "BLK": 100}

# ค่าเริ่มต้นที่ทุกตัวละครมีติดตัว (ไม่ต้องพึ่งอุปกรณ์)
INNATE_BASE = {"CR": 5, "CDM": 150}

# ---------------------------------------------------------------------------
# Equipment options
# ---------------------------------------------------------------------------
# option ของอุปกรณ์ -> stat code ปลายทาง
OPTION_TARGET = {
    "Attack %": "ATK", "Attack Flat": "ATK",
    "Defense %": "DEF", "Defense Flat": "DEF",
    "HP %": "HP", "HP Flat": "HP",
    "Speed": "SPD",
    "Crit Rate": "CR", "Crit Damage": "CDM",
    "Weakness Hit Chance": "WK", "Block Rate": "BLK",
    "Effect Hit Rate": "EHR", "Effect Resistance": "ERes",
    "Damage Taken Reduction": "RED",
}

# ค่าฐานต่อ 1 roll ของ substat; ค่าจริง = base * (extra_rolls + 1)
SUBSTAT_BASE = {
    "Attack %": 5, "Attack Flat": 50,
    "Defense %": 5, "Defense Flat": 30,
    "HP %": 5, "HP Flat": 180,
    "Speed": 4,
    "Crit Rate": 4, "Crit Damage": 6,
    "Weakness Hit Chance": 5, "Block Rate": 4,
    "Effect Hit Rate": 5, "Effect Resistance": 5,
}
SUBSTAT_TYPES = list(SUBSTAT_BASE.keys())

# Main stat ที่ค่า max (+15) แยกตาม slot
MAIN_VALUE_OFFENSE = {
    "Attack %": 28, "Attack Flat": 240, "Defense %": 28, "Defense Flat": 160,
    "HP %": 28, "HP Flat": 850, "Crit Rate": 24, "Crit Damage": 36,
    "Weakness Hit Chance": 28, "Effect Hit Rate": 30,
}
MAIN_VALUE_DEFENSE = {
    "Attack %": 28, "Attack Flat": 240, "Defense %": 28, "Defense Flat": 160,
    "HP %": 28, "HP Flat": 850, "Block Rate": 24,
    "Damage Taken Reduction": 16, "Effect Resistance": 30,
}

# งบ roll ต่อชิ้น: 4 substat + roll เพิ่มรวม 5 ครั้ง (ที่ +15 ลงครบ)
ROLLS_PER_PIECE = 5
SUBSTATS_PER_PIECE = 4

# ---------------------------------------------------------------------------
# Sets — ชื่อไทยจากในเกม + โบนัส 4 ชิ้น (เฉพาะส่วนที่เป็น stat)
# ---------------------------------------------------------------------------
# set code -> (ชื่อไทย, {stat: bonus}, คำอธิบายผล 4 ชิ้นแบบเต็ม)
# ชื่อไทยรวม "ชื่อเรียกในหมู่ผู้เล่น" ไว้ในวงเล็บ (ยืนยันจากผู้ใช้ 2026-07)
SETS = {
    "Vanguard": ("ผู้บัญชาการ (เซ็ตโจมตี)", {"ATK_pct": 45, "EHR": 20},
                 "พลังโจมตี 45% + ผลเข้าเป้า 20%"),
    "Bounty Tracker": ("ผู้ไล่ล่า (เซ็ตจุดอ่อน)", {"WK": 35},
                       "อัตราโจมตีจุดอ่อน 35% + ความเสียหายจุดอ่อน 35%"),
    "Paladin": ("อัศวินศักดิ์สิทธิ์ (เซ็ตเลือด)", {"HP_pct": 40},
                "HP 40% + ปริมาณฟื้นฟู 20%"),
    "Gatekeeper": ("นายประตู (เซ็ตบล็อค)", {"BLK": 30},
                   "อัตราบล็อค 30% + ลดความเสียหายบล็อค 10%"),
    "Guardian": ("ผู้พิทักษ์ (เซ็ตป้องกัน)", {"DEF_pct": 45, "ERes": 20},
                 "พลังป้องกัน 45% + ต้านทานผล 20%"),
    "Assassin": ("นักฆ่า (เซ็ตคริ)", {"CR": 30},
                 "อัตราคริ 30% + ไม่สนพลังป้องกัน 15%"),
    "Avenger": ("ผู้ล้างแค้น (ไฮดร้า)", {},
                "ความเสียหายที่สร้าง 30% + ความเสียหายต่อบอส 40%"),
    "Spellweaver": ("หมอผี (แม่นยำ)", {"EHR": 35},
                    "ผลเข้าเป้า 35% + อัตราปรับผลใช้ 10%"),
    "Orchestrator": ("ผู้ปรับสมดุล (เซ็ตต้าน)", {"ERes": 35},
                     "ต้านทานผล 35% + คุ้มกันดีบัฟ 1 เทิร์นตอนเริ่มสู้"),
}
SET_NAMES = list(SETS.keys())
SET_THAI = {code: th for code, (th, _, _) in SETS.items()}
THAI_TO_SET = {th: code for code, th in SET_THAI.items()}

# ---------------------------------------------------------------------------
# Meta assumptions (จูนได้ตามสนามจริง)
# ---------------------------------------------------------------------------
# ค่าเฉลี่ยที่เจอในสนาม GVG: ศัตรูสายถึกมี ERes ~100, Block ~100
META_ENEMY_ERES = 100
META_ENEMY_BLOCK = 100
