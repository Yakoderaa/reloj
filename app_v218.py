import io,json,os,zipfile,re,hashlib
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v217 as v217
import app_v145 as v145

base.APP_VERSION='2.18.0'
NEEDLES=('app-user/touristLogin','appDeviceId','access-token','app-device/activationDevice','app-device/checkForUpdate','token','accessToken','baseUrl','watchhealth','app-halfwit')

class AppV218(v217.AppV217):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V2.18')
        self._clean_v218();self._install_v218();self._restore_location_button()
        self.status.set('V2.18 lista · cierra base URL + forma del token antes de cualquier red. Sin firmware ni OTA.')

    def _clean_v218(self):
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

    def _install_v218(self):
        top=self.root.winfo_children()[0]
        self.v218_button=ttk.Button(top,text='CERRAR BASE URL + TOKEN',command=self.close_auth_source)
        sib=top.winfo_children()
        try:self.v218_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v218_button.place(x=8,y=8)

    @staticmethod
    def _ascii_strings(data,minlen=4):
        return [m.group().decode('utf-8','ignore') for m in re.finditer(rb'[\x20-\x7e]{%d,}'%minlen,data)]

    def close_auth_source(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V2.18 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V2.18 · buscando base URL, token y contratos exactos…')
        def work():
            rep={'app_version':'2.18.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'close_exact_base_url_and_guest_token_shape_locally_before_first_network_request',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known_from_v217':{'guest_endpoint':'app-user/touristLogin','activation_endpoint':'app-device/activationDevice','check_for_update_endpoint':'app-device/checkForUpdate','all_activation_fields_present':True},
                 'dex_files':[],'hits':{},'url_candidates':[],'token_candidates':[],
                 'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'guest_login_requests':0,'activation_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            def inspect(label,data):
                ss=self._ascii_strings(data,4)
                rep['dex_files'].append({'name':label,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()})
                for n in NEEDLES:
                    hs=[s for s in ss if n.lower() in s.lower()]
                    if hs:rep['hits'].setdefault(n,[]).extend(hs[:60])
                for s in ss:
                    sl=s.lower()
                    if ('http://' in sl or 'https://' in sl) and any(x in sl for x in ('watchhealth','app-halfwit','wtwd','cocousa')):
                        rep['url_candidates'].append(s[:500])
                    if any(x in sl for x in ('accesstoken','access_token','access-token')):
                        rep['token_candidates'].append(s[:300])
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
            rep['hits']={k:sorted(set(v)) for k,v in rep['hits'].items()}
            rep['url_candidates']=sorted(set(rep['url_candidates']))[:100]
            rep['token_candidates']=sorted(set(rep['token_candidates']))[:100]
            base=[u for u in rep['url_candidates'] if 'watchhealth' in u.lower() or 'app-halfwit' in u.lower()]
            guest=bool(rep['hits'].get('app-user/touristLogin'))
            token=bool(rep['hits'].get('access-token') or rep['hits'].get('accessToken'))
            activation=bool(rep['hits'].get('app-device/activationDevice'))
            update=bool(rep['hits'].get('app-device/checkForUpdate'))
            rep['resolved']={'guest_endpoint_confirmed':guest,'activation_endpoint_confirmed':activation,'check_for_update_endpoint_confirmed':update,'access_token_marker_confirmed':token,'base_url_candidates':base[:20],
                'network_gate':'NO_NETWORK_IN_THIS_VERSION','next':'Use the exact base URL candidate plus touristLogin contract for a single guest-login probe; keep token transient and do not activate/download/write yet.','write_gate':'NO_DEVICE_WRITES_IN_THIS_VERSION'}
            rep['summary']={'dex_files':len(rep['dex_files']),'guest_ok':guest,'token_ok':token,'activation_ok':activation,'update_ok':update,'base_url_candidates':len(base)}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v218');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-baseurl-token-v218.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V2.18 · falló: '+repr(err));return
            self.report={'utrawatch_baseurl_token_v218':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep.get('summary') or {}
            self.status.set(f"V2.18 LISTO · guest={s.get('guest_ok')} · token={s.get('token_ok')} · baseURLs={s.get('base_url_candidates')} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV218(root);root.mainloop()
