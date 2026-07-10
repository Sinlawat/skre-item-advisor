"""Item model + validation.

หลักคิด: ดัก input ผิดตั้งแต่ต้นทางด้วย "กฎของเกม" (game invariants)
ที่ +15 ค่า substat ต้องลงตัวกับ SUBSTAT_BASE เสมอ และ roll เพิ่มรวมทั้งชิ้น
ต้องเท่ากับ ROLLS_PER_PIECE (5) พอดี — ถ้าบวกไม่ลงตัว แปลว่ากรอกผิดแน่นอน
"""
from __future__ import annotations

from dataclasses import dataclass, field

import constants as C


@dataclass(frozen=True)
class Substat:
    type: str          # ชื่อ option เช่น "Crit Rate"
    value: float       # ค่าที่อ่านจากหน้าจอเกม (+15 แล้ว)

    @property
    def stat(self) -> str:
        """Stat code ปลายทาง เช่น Crit Rate -> CR"""
        return C.OPTION_TARGET[self.type]

    @property
    def roll_equivalent(self) -> float:
        """แปลงค่าเป็นหน่วยกลาง 'จำนวน roll' (base 1 + extra)

        เช่น Speed 12 = 12/4 = 3.0 rolls, Crit Rate 4 = 1.0 roll
        ใช้หน่วยนี้เพื่อเทียบ substat คนละชนิดกันได้อย่างยุติธรรม
        """
        return self.value / C.SUBSTAT_BASE[self.type]

    @property
    def extra_rolls(self) -> float:
        return self.roll_equivalent - 1


@dataclass(frozen=True)
class Item:
    slot: str                      # "offense" | "defense"
    set_code: str                  # เช่น "Assassin"
    main_type: str                 # ชื่อ option ของ main stat
    substats: tuple[Substat, ...] = field(default_factory=tuple)

    @property
    def main_stat(self) -> str:
        return C.OPTION_TARGET[self.main_type]

    @property
    def main_value(self) -> int:
        pool = C.MAIN_VALUE_OFFENSE if self.slot == "offense" else C.MAIN_VALUE_DEFENSE
        return pool[self.main_type]


def validate_item(item: Item) -> list[str]:
    """คืน list ข้อความ error (ภาษาไทย); list ว่าง = ผ่าน

    เขียนเป็น pure function แยกจาก dataclass เพื่อให้เทสต์ง่าย
    และเก็บ error ทุกข้อพร้อมกัน (ไม่ fail ทีละข้อ) — UX ดีกว่าเวลากรอกฟอร์ม
    """
    errors: list[str] = []

    # --- slot / set / main ---
    if item.slot not in ("offense", "defense"):
        errors.append(f"slot ต้องเป็น offense หรือ defense (ได้ {item.slot!r})")
        return errors  # เช็กต่อไม่ได้ถ้า slot ผิด

    if item.set_code not in C.SETS:
        errors.append(f"ไม่รู้จักเซ็ต {item.set_code!r}")

    pool = C.MAIN_VALUE_OFFENSE if item.slot == "offense" else C.MAIN_VALUE_DEFENSE
    if item.main_type not in pool:
        errors.append(
            f"main '{item.main_type}' ใช้กับชิ้น {item.slot} ไม่ได้"
        )

    # --- substats ---
    if len(item.substats) != C.SUBSTATS_PER_PIECE:
        errors.append(
            f"ต้องมี substat {C.SUBSTATS_PER_PIECE} ช่อง (ได้ {len(item.substats)})"
        )

    # หมายเหตุ: เกมจริงอนุญาตให้ substat ซ้ำชนิดกับ main stat ได้
    # (ยืนยันจากผู้ใช้ 2026-07) — ห้ามเฉพาะ substat ซ้ำกันเอง
    types = [s.type for s in item.substats]
    if len(types) != len(set(types)):
        errors.append("substat ห้ามซ้ำชนิดกัน")

    total_extra = 0.0
    for s in item.substats:
        if s.type not in C.SUBSTAT_BASE:
            errors.append(f"ไม่รู้จัก substat {s.type!r}")
            continue
        base = C.SUBSTAT_BASE[s.type]
        if s.value <= 0 or s.value % base != 0:
            errors.append(
                f"{s.type} = {s.value:g} ไม่ลงตัว — ต้องเป็นพหุคูณของ {base} "
                f"(เช่น {base}, {base * 2}, {base * 3}, ...)"
            )
            continue
        if s.extra_rolls > C.ROLLS_PER_PIECE:
            errors.append(f"{s.type} = {s.value:g} เกิน roll สูงสุดต่อช่อง")
        total_extra += s.extra_rolls

    # เช็กงบ roll รวม เฉพาะเมื่อค่าราย substat ถูกต้องแล้วเท่านั้น
    if not errors and total_extra != C.ROLLS_PER_PIECE:
        errors.append(
            f"roll เพิ่มรวมทั้งชิ้นต้องเท่ากับ {C.ROLLS_PER_PIECE} ที่ +15 "
            f"(ตอนนี้ได้ {total_extra:g}) — ตรวจตัวเลขอีกครั้ง น่าจะกรอกผิด 1 ช่อง"
        )

    return errors
