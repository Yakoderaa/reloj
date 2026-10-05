import tkinter as tk
from tkinter import ttk
import app as base
import app_v149 as v149

base.APP_VERSION="1.50.0"

class AppV150(v149.AppV149):
    def __init__(self,root):
        super().__init__(root)
        root.title("Reloj Lab V1.50")
        self._retitle_v150(root)
        self._ensure_api_button_first()
        self.status.set("V1.50 lista · CONSULTAR API UTRAWATCH queda primero y siempre visible en la barra superior.")

    def _retitle_v150(self,widget):
        try:
            if isinstance(widget,ttk.Label):
                t=str(widget.cget("text"))
                if "V1.49" in t: widget.configure(text=t.replace("V1.49","V1.50"))
        except Exception: pass
        try:
            for child in widget.winfo_children(): self._retitle_v150(child)
        except Exception: pass

    def _ensure_api_button_first(self):
        # The V1.49 button was appended after several inherited toolbar buttons and
        # could end up outside the visible width. Repack it before every other item.
        try:
            top=self.root.winfo_children()[0]
            existing=None
            for child in top.winfo_children():
                try:
                    if isinstance(child,ttk.Button) and str(child.cget("text")).strip().upper()=="CONSULTAR API UTRAWATCH":
                        existing=child;break
                except Exception: pass
            if existing is not None:
                existing.pack_forget()
            btn=existing or ttk.Button(top,text="CONSULTAR API UTRAWATCH",command=self.query_utrawatch_api)
            siblings=[w for w in top.winfo_children() if w is not btn]
            if siblings:
                btn.pack(side="left",padx=(0,10),before=siblings[0])
            else:
                btn.pack(side="left",padx=(0,10))
            self.api_button_v150=btn
        except Exception:
            # Fallback: fixed visible button at the upper-left of the main window.
            self.api_button_v150=ttk.Button(self.root,text="CONSULTAR API UTRAWATCH",command=self.query_utrawatch_api)
            self.api_button_v150.place(x=4,y=4)

if __name__=="__main__":
    root=tk.Tk();AppV150(root);root.mainloop()
