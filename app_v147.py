import tkinter as tk
from tkinter import ttk
import app as base
import app_v146 as v146

base.APP_VERSION="1.47.0"

class AppV147(v146.AppV146):
    def __init__(self,root):
        super().__init__(root)
        root.title("Reloj Lab V1.47")
        self._retitle_v147(root)
        self.status.set("V1.47 lista · guardia legacy pausada durante descubrimiento; BUSCAR FIRMWARE EXACTO usa el perfil BK3288 validado.")

    def _retitle_v147(self,widget):
        try:
            if isinstance(widget,ttk.Label):
                t=str(widget.cget("text"))
                if "V1.46" in t:
                    widget.configure(text=t.replace("V1.46","V1.47"))
        except Exception:
            pass
        try:
            for child in widget.winfo_children():
                self._retitle_v147(child)
        except Exception:
            pass

    def start_saved_face_guard_if_available(self):
        # V1.43's legacy guard depended on a fresh BLE advertisement and could
        # falsely report "out of range" while Windows still had an active GATT
        # connection. Discovery builds must not compete for the same BLE link.
        self.face_guard_enabled=False
        self.face_guard_future=None
        try:
            self.status.set("V1.47 · reloj disponible por perfil validado; guardia legacy pausada para no interferir con BLE.")
        except Exception:
            pass

    def find_exact_firmware(self):
        self.face_guard_enabled=False
        if self.face_guard_future:
            try:self.face_guard_future.cancel()
            except Exception:pass
            self.face_guard_future=None
        self.status.set("V1.47 · guardia pausada; buscando firmware exacto sin competir por Bluetooth…")
        return super().find_exact_firmware()

if __name__=="__main__":
    root=tk.Tk();AppV147(root);root.mainloop()
