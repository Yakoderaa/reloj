import tkinter as tk
from tkinter import ttk
import app as base
import app_v158 as v158

base.APP_VERSION="1.59.0"

class AppV159(v158.AppV158):
    def __init__(self, root):
        # Bypass V1.58's one-button cleanup and build from V1.57 directly.
        super(v158.AppV158, self).__init__(root)
        root.title("Reloj Lab V1.59")
        self._retitle_v159(root)
        self._keep_essential_buttons()
        self.status.set("V1.59 lista · quedan sólo los botones esenciales: resolver endpoint, buscar dispositivos y buscar actualizaciones.")

    def _retitle_v159(self, widget):
        try:
            if isinstance(widget, ttk.Label):
                t=str(widget.cget("text"))
                for old in ("V1.54","V1.55","V1.56","V1.57","V1.58"):
                    t=t.replace(old,"V1.59")
                widget.configure(text=t)
        except Exception:
            pass
        try:
            for child in widget.winfo_children():
                self._retitle_v159(child)
        except Exception:
            pass

    def _keep_essential_buttons(self):
        # Keep only the current action plus device search and updater controls.
        allowed_terms=(
            "resolver endpoint login",
            "buscar relojes",
            "buscar dispositivos",
            "buscar disp",
            "buscar actualizaciones",
            "buscar actualización",
            "buscar actualizacion",
        )
        found_action=False

        def walk(widget):
            nonlocal found_action
            for child in list(widget.winfo_children()):
                try:
                    if isinstance(child, (ttk.Button, tk.Button)):
                        text=str(child.cget("text") or "").strip().lower()
                        keep=any(term in text for term in allowed_terms)
                        if "resolver endpoint login" in text:
                            found_action=True
                        if not keep:
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

        if not found_action:
            try:
                top=self.root.winfo_children()[0]
                self.resolve_login_button_v159=ttk.Button(top,text="RESOLVER ENDPOINT LOGIN",command=self.resolve_login_endpoint)
                siblings=top.winfo_children()
                if siblings:
                    self.resolve_login_button_v159.pack(side="left",padx=(4,10),before=siblings[0])
                else:
                    self.resolve_login_button_v159.pack(side="left",padx=(4,10))
            except Exception:
                self.resolve_login_button_v159=ttk.Button(self.root,text="RESOLVER ENDPOINT LOGIN",command=self.resolve_login_endpoint)
                self.resolve_login_button_v159.place(x=8,y=8)

if __name__=="__main__":
    root=tk.Tk(); AppV159(root); root.mainloop()
