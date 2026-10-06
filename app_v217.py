import io,json,os,zipfile,re,hashlib
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v216 as v216
import app_v145 as v145

base.APP_VERSION='2.17.0'

class AppV217(v216.AppV216):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V2.17')
        self._clean_v217();self._install_v217();self._restore_location_button()
        self.status.set('V2.17 lista · prepara contrato AUTH + ACTIVATION en modo lectura. Sin red, firmware ni OTA.')

    def _clean_v217(self):
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

    def _install_v217(self):
        top=self.root.winfo_children()[0]
        self.v217_button=ttk.Button(top,text='PREPARAR AUTH + ACTIVACIÓN',command=self.prepare_contract)
        sib=top.winfo_children()
        try:self.v217_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v217_button.place(x=8,y=8)

    @staticmethod
    def _ascii_strings(data,minlen=4):
        return [m.group().decode('utf-8','ignore') for m in re.finditer(rb'[\x20-\x7e]{%d,}'%minlen,data)]

    def prepare_contract(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V2.17 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V2.17 · verificando endpoints, headers y campos de activación…')
        def work():
            rep={'app_version':'2.17.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'prepare_exact_guest_auth_and_activation_contract_read_only_before_first_network_request',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known_from_v216':{'account_watchid':'UserDeviceInfo.e() -> PREF_KEY_WATCH_ID when non-empty','mac':'DeviceManager.a param1 -> PREF_KEY_DEVICE_MAC','area':'WEATHER JSON','lat':'Double.parseDouble(HealthPresenter.S0 param1)','lng':'Double.parseDouble(HealthPresenter.S0 param2)','clears_are_explicit_paths':True},
                 'hits':{},'dex_files':[],'request_preview':{},
                 'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'guest_login_requests':0,'activation_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            needles=['app-user/touristLogin','touristLogin','appDeviceId','access-token','activationDevice','app-device/activation','app-device/checkForUpdate','checkForUpdate','currentFirmware','language','macAddress','watchId','area','lat','lng','filePath','updateFlag']
            corpus=[]
            def inspect(label,data):
                rep['dex_files'].append({'name':label,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()})
                ss=self._ascii_strings(data,4);corpus.extend(ss)
                for n in needles:
                    hs=[s for s in ss if n.lower() in s.lower()]
                    if hs:rep['hits'].setdefault(n,[]).extend(hs[:25])
            def inspect_apk(name,data):
                with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                    for n in z.namelist():
                        if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')):inspect(name+'!'+n,z.read(n))
            try:
                if zipfile.is_zipfile(chosen):
                    with zipfile.ZipFile(chosen,'r') as z:
                        apks=[n for n in z.namelist() if n.lower().endswith('.apk')]
                        if apks:
                            preferred=[n for n in apks if 'com.wtwd.utrawatch' in n.lower() or os.path.basename(n).lower().startswith(('base','master'))]
                            for n in (preferred or apks[:1]):inspect_apk(n,z.read(n))
                        else:
                            for n in z.namelist():
                                if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')):inspect(n,z.read(n))
                else:
                    with open(chosen,'rb') as f:inspect_apk(os.path.basename(chosen),f.read())
            except Exception as ex:rep.setdefault('errors',[]).append({'input':chosen,'error':repr(ex)})
            uniq={k:sorted(set(v)) for k,v in rep['hits'].items()};rep['hits']=uniq
            auth_ok=bool(uniq.get('app-user/touristLogin') or uniq.get('touristLogin')) and bool(uniq.get('appDeviceId'))
            token_ok=bool(uniq.get('access-token'))
            activation_ok=bool(uniq.get('activationDevice') or uniq.get('app-device/activation'))
            update_ok=bool(uniq.get('app-device/checkForUpdate') or uniq.get('checkForUpdate'))
            fields={k:bool(uniq.get(k)) for k in ('currentFirmware','language','macAddress','watchId','area','lat','lng')}
            rep['request_preview']={
                'guest_login':{'endpoint':'app-user/touristLogin','body':{'appDeviceId':'<generated opaque guest id>'},'send':False},
                'activation':{'endpoint':'<exact activation path must be confirmed from app metadata>','header':{'access-token':'<transient token; never logged raw>'},'body':{'area':'<WEATHER JSON>','currentFirmware':'','lat':'<explicit location latitude>','lng':'<explicit location longitude>','macAddress':'<runtime PREF_KEY_DEVICE_MAC>','watchId':'<runtime PREF_KEY_WATCH_ID>'},'send':False},
                'check_for_update':{'endpoint':'app-device/checkForUpdate','header':{'access-token':'<transient token>'},'body':{'currentFirmware':'0.0.1','language':'<resolved app language>'},'send':False}}
            rep['resolved']={'guest_auth_contract_present':auth_ok,'access_token_header_present':token_ok,'activation_marker_present':activation_ok,'check_for_update_contract_present':update_ok,'activation_fields_present':fields,
                'network_gate':'NO_NETWORK_IN_THIS_VERSION','next':'If activation endpoint/path and all required fields are confirmed, next version may perform guest login only, hold token transiently, and stop before activation/download/OTA.','write_gate':'NO_DEVICE_WRITES_IN_THIS_VERSION'}
            rep['summary']={'dex_files':len(rep['dex_files']),'auth_ok':auth_ok,'token_ok':token_ok,'activation_ok':activation_ok,'update_ok':update_ok,'field_hits':sum(1 for x in fields.values() if x)}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v217');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-auth-activation-contract-v217.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V2.17 · falló: '+repr(err));return
            self.report={'utrawatch_auth_activation_contract_v217':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep.get('summary') or {}
            self.status.set(f"V2.17 LISTO · auth={s.get('auth_ok')} · token={s.get('token_ok')} · activation={s.get('activation_ok')} · update={s.get('update_ok')} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV217(root);root.mainloop()
