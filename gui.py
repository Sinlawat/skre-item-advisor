"""SKRE Item Advisor — tkinter GUI (ภาษาไทย)

โครงสร้าง: GUI เป็นแค่ "เปลือก" — รับ input, เรียก models/scoring, แสดงผล
logic ทั้งหมดอยู่ใน models.py / scoring.py ซึ่งมี unit test แยกต่างหาก
(หลัก separation of concerns: GUI เทสต์ยาก จึงต้องบางที่สุด)
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import constants as C
from models import Item, Substat, validate_item
from scoring import evaluate

PAD = {"padx": 6, "pady": 4}


class AdvisorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("SKRE Item Advisor — คัดอุปกรณ์ +15")
        root.geometry("720x640")

        form = ttk.LabelFrame(root, text="ข้อมูลอุปกรณ์ (+15)")
        form.pack(fill="x", **PAD)

        # --- slot ---
        ttk.Label(form, text="ประเภทชิ้น:").grid(row=0, column=0, sticky="w", **PAD)
        self.slot_var = tk.StringVar(value="offense")
        slot_box = ttk.Frame(form)
        slot_box.grid(row=0, column=1, columnspan=3, sticky="w")
        for text, val in (("โจมตี (offense)", "offense"), ("ป้องกัน (defense)", "defense")):
            ttk.Radiobutton(
                slot_box, text=text, value=val, variable=self.slot_var,
                command=self._refresh_main_options,
            ).pack(side="left", padx=4)

        # --- set ---
        ttk.Label(form, text="เซ็ต:").grid(row=1, column=0, sticky="w", **PAD)
        self.set_var = tk.StringVar()
        self.set_cb = ttk.Combobox(
            form, textvariable=self.set_var, state="readonly", width=28,
            values=[C.SET_THAI[s] for s in C.SET_NAMES],
        )
        self.set_cb.grid(row=1, column=1, sticky="w", **PAD)
        self.set_cb.current(0)

        # --- main stat ---
        ttk.Label(form, text="Main stat:").grid(row=2, column=0, sticky="w", **PAD)
        self.main_var = tk.StringVar()
        self.main_cb = ttk.Combobox(
            form, textvariable=self.main_var, state="readonly", width=28
        )
        self.main_cb.grid(row=2, column=1, sticky="w", **PAD)
        self._refresh_main_options()

        # --- substats (4 แถว) ---
        subs = ttk.LabelFrame(root, text="Substats 4 ช่อง (ค่าที่เห็นในเกมตอน +15)")
        subs.pack(fill="x", **PAD)
        self.sub_rows: list[tuple[tk.StringVar, tk.StringVar]] = []
        for i in range(C.SUBSTATS_PER_PIECE):
            ttk.Label(subs, text=f"ช่อง {i + 1}:").grid(row=i, column=0, sticky="w", **PAD)
            type_var = tk.StringVar()
            ttk.Combobox(
                subs, textvariable=type_var, state="readonly", width=24,
                values=C.SUBSTAT_TYPES,
            ).grid(row=i, column=1, sticky="w", **PAD)
            val_var = tk.StringVar()
            ttk.Entry(subs, textvariable=val_var, width=10).grid(
                row=i, column=2, sticky="w", **PAD
            )
            self.sub_rows.append((type_var, val_var))

        # --- action ---
        btns = ttk.Frame(root)
        btns.pack(fill="x", **PAD)
        ttk.Button(btns, text="ประเมิน", command=self.on_evaluate).pack(side="left")
        ttk.Button(btns, text="ล้างฟอร์ม", command=self.on_clear).pack(side="left", padx=6)

        # --- output ---
        out_frame = ttk.LabelFrame(root, text="ผลการประเมิน")
        out_frame.pack(fill="both", expand=True, **PAD)
        self.output = tk.Text(out_frame, wrap="word", font=("Tahoma", 11), height=18)
        self.output.pack(fill="both", expand=True, padx=4, pady=4)
        self.output.tag_configure("keep", foreground="#0a7d2c", font=("Tahoma", 13, "bold"))
        self.output.tag_configure("sell", foreground="#b3261e", font=("Tahoma", 13, "bold"))
        self.output.tag_configure("head", font=("Tahoma", 11, "bold"))

    # ------------------------------------------------------------------
    def _refresh_main_options(self) -> None:
        pool = (
            C.MAIN_VALUE_OFFENSE
            if self.slot_var.get() == "offense"
            else C.MAIN_VALUE_DEFENSE
        )
        options = list(pool.keys())
        self.main_cb["values"] = options
        if self.main_var.get() not in options:
            self.main_cb.current(0)

    def _read_item(self) -> tuple[Item | None, list[str]]:
        """แปลงค่าจากฟอร์มเป็น Item; คืน (item, errors)"""
        errors: list[str] = []
        substats: list[Substat] = []
        for i, (type_var, val_var) in enumerate(self.sub_rows, start=1):
            t, v = type_var.get().strip(), val_var.get().strip()
            if not t or not v:
                errors.append(f"ช่อง {i}: กรอกชนิดและค่าให้ครบ")
                continue
            try:
                substats.append(Substat(t, float(v)))
            except ValueError:
                errors.append(f"ช่อง {i}: '{v}' ไม่ใช่ตัวเลข")
        if errors:
            return None, errors

        item = Item(
            slot=self.slot_var.get(),
            set_code=C.THAI_TO_SET[self.set_var.get()],
            main_type=self.main_var.get(),
            substats=tuple(substats),
        )
        return item, validate_item(item)

    # ------------------------------------------------------------------
    def on_clear(self) -> None:
        for type_var, val_var in self.sub_rows:
            type_var.set("")
            val_var.set("")
        self.output.delete("1.0", "end")

    def on_evaluate(self) -> None:
        self.output.delete("1.0", "end")
        item, errors = self._read_item()
        if errors or item is None:
            self.output.insert("end", "กรอกข้อมูลไม่ถูกต้อง:\n", "sell")
            for e in errors:
                self.output.insert("end", f"  • {e}\n")
            return

        v = evaluate(item)
        tag = "keep" if v.grade in ("S", "A", "B") else "sell"
        self.output.insert("end", f"เกรด {v.grade} — {v.decision}\n\n", tag)

        self.output.insert("end", "เหมาะกับตัวประเภท:\n", "head")
        for f in v.fits:
            self.output.insert(
                "end",
                f"  {f.profile.name_th} [{f.profile.context}] "
                f"— ความเข้ากัน {f.score * 100:.0f}% "
                f"(main {f.main_fit * 100:.0f}% / subs {f.sub_score * 100:.0f}%)\n",
            )

        self.output.insert("end", "\nเหตุผล:\n", "head")
        for line in v.reasoning:
            self.output.insert("end", f"  {line}\n")


def main() -> None:
    root = tk.Tk()
    AdvisorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
