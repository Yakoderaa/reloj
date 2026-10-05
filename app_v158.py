import tkinter as tk
from tkinter import ttk
import app as base
import app_v157 as v157

base.APP_VERSION="1.58.0"

class AppV158(v157.AppV157):
    def __init__(self, root):
        super().__init__(root)
        root.title("Reloj Lab V1.58")
        self._retitle_v158(root)
        self._leave_only_required_button()
        self.status.set("V1.58 lista · interfaz limpia. Usá únicamente RESOLVER ENDPOINT LOGIN.")

    def _retitle_v158(self, widget):
        try:
            if isinstance(widget, ttk.Label):
                t=str(widget.cget("text"))
                for old in ("V1.54","V1.55","V1.56","V1.57"):
                    t=t.replace(old,"V1.58")
                widget.configure(text=t)
        except Exception:
            pass
        try:
            for child in widget.winfo_children():
                self._retitle_v158(child)
        except Exception:
            pass

    def _leave_only_required_button(self):
        # Remove every inherited button from the visible UI so there is no ambiguity.
        def hide_buttons(widget):
            for child in list(widget.winfo_children()):
                try:
                    if isinstance(child, ttk.Button) or isinstance(child, tk.Button):
                        try: child.pack_forget()
                        except Exception: pass
                        try: child.grid_remove()
                        except Exception: pass
                        try: child.place_forget()
                        except Exception: pass
                    else:
                        hide_buttons(child)
                except Exception:
                    pass
        hide_buttons(self.root)

        # Add back exactly one action button: the one required for this version.
        try:
            top=self.root.winfo_children()[0]
            self.resolve_login_button_v158=ttk.Button(
                top,
                text="RESOLVER ENDPOINT LOGIN",
                command=self.resolve_login_endpoint
            )
            self.resolve_login_button_v158.pack(side="left",padx=8,pady=4)
        except Exception:
            self.resolve_login_button_v158=ttk.Button(
                self.root,
                text="RESOLVER ENDPOINT LOGIN",
                command=self.resolve_login_endpoint
            )
            self.resolve_login_button_v158.place(x=8,y=8)

if __name__=="__main__":
    root=tk.Tk(); AppV158(root); root.mainloop()
