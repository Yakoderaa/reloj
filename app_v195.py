import json,os
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk
import app as base
import app_v194 as v194
import app_v145 as v145

base.APP_VERSION='1.95.0'

class AppV195(v194.AppV194):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.95')
        self._clean_v195();self._install_v195();self._restore_location_button()
        self.status.set('V1.95 lista · prepara la vinculación exacta con la identidad BLE real. Sin red ni OTA.')

    def _clean_v195(self):
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

    def _install_v195(self):
        top=self.root.winfo_children()[0]
        self.v195_button=ttk.Button(top,text='PREPARAR VINCULACIÓN EXACTA',command=self.prepare_exact_bind)
        sib=top.winfo_children()
        try:self.v195_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v195_button.place(x=8,y=8)

    def prepare_exact_bind(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V1.95 · falta validación BK3288.');return
        selected=self.selected or {}
        address=selected.get('address') or getattr(selected.get('device'),'address',None)
        name=selected.get('name') or getattr(selected.get('device'),'name',None)
        if not address:
            self.status.set('V1.95 · primero usá Buscar relojes y seleccioná el reloj exacto.');return
        self.face_guard_enabled=False
        self.status.set('V1.95 · preparando body exacto con la identidad BLE seleccionada…')
        def work():
            rep={'app_version':'1.95.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'prepare_exact_userBindDevice_body_from_the_real_selected_ble_watch_without_network_or_ota',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,
                 'selected_watch':{'address':str(address),'name':str(name or '')},
                 'resolved_contract':{'endpoint':'app-device/userBindDevice','header':'access-token','body_keys':['macAddress','name','userId'],
                                      'source_evidence':{'macAddress':'real selected BLE address','name':'real selected BLE local/display name','userId':'guest-session userId returned by official service'}},
                 'request_preview':{'macAddress':str(address),'name':str(name or ''),'userId':'<guest-session-userId>'},
                 'checks':{'address_present':bool(address),'name_present':bool(name),'profile_ready':bool(ready),
                           'firmware':(validation.get('observed') or {}).get('firmware',{}).get('text')},
                 'resolved':{'ready_for_one_bind_request':bool(address and name),
                             'next':'Use this exact selected BLE identity plus the guest-session userId for one official userBindDevice request, then retry checkForUpdate.',
                             'write_gate':'KEEP_OTA_DISABLED_UNTIL_OFFICIAL_FIRMWARE_FILE_VALIDATION_SUCCEEDS'},
                 'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v195');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-bind-preview-v195.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.95 · falló: '+repr(err));return
            self.report={'utrawatch_bind_preview_v195':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            self.status.set(f"V1.95 LISTO · identidad BLE exacta={rep['resolved'].get('ready_for_one_bind_request')} · red/OTA=0 · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV195(root);root.mainloop()
