import tkinter as tk
from tkinter import ttk
import app as base
import app_v218 as v218

base.APP_VERSION='2.19.0'

class AppV219(v218.AppV218):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V2.19')
        self._clean_v219();self._install_v219();self._restore_location_button()
        self.status.set('V2.19 lista · fuerza un diagnóstico NUEVO de base URL + token y evita copiar el diagnóstico anterior.')

    def _clean_v219(self):
        keep=('buscar relojes','buscar dispositivos','buscar disp','buscar actualización','buscar actualizacion','buscar actualizaciones','buscar ubicación','buscar ubicacion')
        def walk(w):
            for c in list(w.winfo_children()):
                try:
                    if isinstance(c,(ttk.Button,tk.Button)):
                        t=str(c.cget('text') or '').lower()
                        if not any(x in t for x in keep):
                            try:c.pack_forget()
                            except:pass
                            try:c.grid_remove()
                            except:pass
                            try:c.place_forget()
                            except:pass
                    else:walk(c)
                except:pass
        walk(self.root)

    def _install_v219(self):
        top=self.root.winfo_children()[0]
        self.v219_button=ttk.Button(top,text='GENERAR DIAGNÓSTICO NUEVO V2.18',command=self.run_fresh_v218)
        sib=top.winfo_children()
        try:self.v219_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v219_button.place(x=8,y=8)

    def run_fresh_v218(self):
        try:
            self.root.clipboard_clear()
            self.root.update_idletasks()
        except:pass
        self.status.set('V2.19 · portapapeles limpiado; ejecutando análisis V2.18 real…')
        return v218.AppV218.close_auth_source(self)

if __name__=='__main__':
    root=tk.Tk();AppV219(root);root.mainloop()
