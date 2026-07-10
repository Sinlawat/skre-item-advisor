# SKRE Item Advisor

โปรแกรมหน้าต่าง (tkinter) สำหรับคัดอุปกรณ์ Seven Knights Rebirth ที่ **+15 แล้ว**
กรอกค่า stat → ระบบตัดสิน **เก็บ/ขาย** พร้อมบอกว่า **เหมาะกับตัวประเภทไหน** และอธิบายเหตุผลรายบรรทัด

ค่าคงที่ทั้งหมด (substat base, main value, set bonus) ใช้ชุดเดียวกับโปรเจกต์
[Builder-Optimize-7K](../Builder-Optimize-7K) ซึ่ง reverse-engineer จาก SKRE Build Maker BETA.4

## วิธีรัน (Windows + VS Code)

ต้องมี Python 3.10+ (ตัวติดตั้งจาก python.org มี tkinter มาให้อยู่แล้ว)

```bash
# เปิดโฟลเดอร์นี้ใน VS Code แล้วรันใน terminal
python gui.py

# รันเทสต์ (ต้องติดตั้ง pytest ก่อน: pip install pytest)
python -m pytest tests/ -v      # 14 passed
```

## วิธีใช้

1. เลือกประเภทชิ้น (offense/defense) — รายการ main stat จะเปลี่ยนตาม slot ให้เอง
2. เลือกเซ็ต (ชื่อไทยตามเกม) และ main stat
3. กรอก substat 4 ช่อง: ชนิด + ค่าตัวเลขที่เห็นในเกม
4. กด **ประเมิน**

ถ้ากรอกเลขผิด ระบบจับได้จาก "กฎของเกม" เอง:
ค่าทุกช่องต้องหารด้วยค่าฐานลงตัว และ roll เพิ่มรวมทั้งชิ้นต้อง = 5 ที่ +15 พอดี

## สถาปัตยกรรม

```
gui.py        เปลือก UI (บางที่สุด ไม่มี logic)
   │
models.py     Item dataclass + validate_item (กฎ game invariant)
   │
scoring.py    engine 4 ขั้น: normalize → saturate → score → gate
   │
profiles.py   ★ จุดจูนหลัก: weight ต่อบทบาท + เซ็ตที่เข้ากัน
constants.py  ค่าคงที่จากเกม + ชื่อเซ็ตไทย + meta assumptions
```

### หลักคิดของ scoring

- **Roll equivalent** — แปลงทุก substat เป็นหน่วยเดียวกัน (`value / base`)
  เพื่อเทียบ Speed กับ Crit Damage ได้อย่างยุติธรรม
- **Saturation** — CR / WK / BLK ตันที่ 100: นับเฉพาะส่วนที่ไม่เกินเพดาน
  หลังหักของฟรี (innate 5 CR + โบนัสเซ็ตของชิ้นนั้น)
- **Set gating** — ชิ้นถูกประเมินเฉพาะกับบทบาทที่ใช้เซ็ตนั้นจริง
  (substat สายแทงค์บนเซ็ตนักฆ่า = ขยะ ต่อให้ roll สวย)
- **คะแนน = main 35% + subs 65%** เทียบกับ "ชิ้นในฝัน" ของบทบาทนั้น
  จึงเป็น 0–100% เสมอ → ตัดเกรด S/A/B/C/F

### เกรดและคำตัดสิน

| เกรด | คะแนน | คำตัดสิน |
|---|---|---|
| S | ≥ 80% | เก็บ — ของเทพ ใช้งานทันที |
| A | ≥ 65% | เก็บ — ดีมาก |
| B | ≥ 50% | เก็บเผื่อ |
| C | ≥ 35% | ขายได้ |
| F | < 35% | ขาย |

## การจูน

คำตัดสินช่วงแรก **จะยังไม่ตรงใจ 100%** — นี่คือเรื่องปกติ จูนได้ 3 จุดโดยไม่แตะ logic:

1. `profiles.py` — weight ของแต่ละ stat ต่อบทบาท (จุดหลัก)
2. `scoring.py` ด้านบน — `MAIN_WEIGHT/SUB_WEIGHT`, `FLAT_PENALTY`, ขั้นเกรด `GRADES`
3. `constants.py` — `META_ENEMY_ERES` ตาม meta ที่เจอจริง

จูนแล้วรัน `pytest` ทุกครั้ง — เทสต์เขียนแบบเช็ก "ความสัมพันธ์"
(ชิ้นเทพต้องชนะชิ้นขยะ) จึงทนต่อการปรับ weight

## ข้อจำกัดที่รู้อยู่แล้ว (by design)

- ประเมิน **รายชิ้น** ไม่ใช่ทั้งบิลด์ — การเช็กว่า CR รวมทั้งบิลด์เกิน 100 หรือไม่
  เป็นหน้าที่ของ Builder-Optimize-7K (โปรแกรมจะเตือนใน reasoning ให้)
- ยังไม่เก็บประวัติไอเทมลงไฟล์/ฐานข้อมูล (เป็น candidate สำหรับ phase ถัดไป)
