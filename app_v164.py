import tkinter as tk
from tkinter import ttk
import app as base
import app_v163 as v163

base.APP_VERSION="1.64.0"

class AppV164(v163.AppV163):
    def __init__(self, root):
        super().__init__(root)
        root.title("Reloj Lab V1.64")
        self._retitle_v164(root)
        self._clean_actions_v164()
        self.status.set("V1.64 lista · SELECCIONAR UTRAWATCH siempre abre el selector. Buscar actualización vuelve a usar el canal oficial de Reloj Lab.")

    def _retitle_v164(self, widget):
        try:
            if isinstance(widget, ttk.Label):
                t=str(widget.cget("text"))
                for old in ("V1.54","V1.55","V1.56","V1.57","V1.58","V1.59","V1.60","V1.61","V1.62","V1.63"):
                    t=t.replace(old,"V1.64")
                widget.configure(text=t)
        except Exception:
            pass
        try:
            for child in widget.winfo_children():
                self._retitle_v164(child)
        except Exception:
            pass

    def _auto_candidates(self):
        # V1.64: never silently consumes a package just because one exists in Downloads.
        # The user explicitly chooses which UtraWatch APK/XAPK/ZIP to inspect every time.
        return []

    def _clean_actions_v164(self):
        allowed=(
            "seleccionar utrawatch y analizar",
            "buscar relojes","buscar dispositivos","buscar disp",
            "buscar actualización","buscar actualizacion","buscar actualizaciones"
        )
        def walk(widget):
            for child in list(widget.winfo_children()):
                try:
                    if isinstance(child,(ttk.Button,tk.Button)):
                        text=str(child.cget("text") or "").strip().lower()
                        if not any(x in text for x in allowed):
                            try: child.pack_forget()
                            except Exception: pass
                            try: child.grid_remove()
                            except Exception: pass
                            try: child.place_forget()
                            except Exception: pass
                    else:
                        walk(child)
                except Exception:
                    pass
        walk(self.root)

if __name__=="__main__":
    root=tk.Tk(); AppV164(root); root.mainloop()
