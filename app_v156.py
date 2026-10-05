import tkinter as tk
from tkinter import ttk
import app as base
import app_v155 as v155

base.APP_VERSION="1.56.0"

class AppV156(v155.AppV155):
    def __init__(self, root):
        super().__init__(root)
        root.title("Reloj Lab V1.56")
        self._retitle_v156(root)
        self.status.set("V1.56 lista · inicio corregido; DESCUBRIR LOGIN REAL conserva el flujo de V1.55.")

    def _retitle_v156(self, widget):
        try:
            if isinstance(widget, ttk.Label):
                t=str(widget.cget("text"))
                if "V1.55" in t:
                    widget.configure(text=t.replace("V1.55","V1.56"))
        except Exception:
            pass
        try:
            for child in widget.winfo_children():
                self._retitle_v156(child)
        except Exception:
            pass

if __name__=="__main__":
    root=tk.Tk(); AppV156(root); root.mainloop()
