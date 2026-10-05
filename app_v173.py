import io, json, os, zipfile
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, filedialog
import app as base
import app_v172 as v172
import app_v145 as v145

base.APP_VERSION='1.73.0'

TARGET_CLASSES=(
    'Lcom/wtwd/cocousa/manager/UserManager;',
    'Lcom/wtwd/cocousa/ui/module/main/device/update/HardwareUpdateModel;',
    'Lcom/wtwd/cocousa/ui/module/main/device/DeviceModel;',
    'Lcom/wtwd/cocousa/ui/base/view/BaseApplication;',
    'Lcom/wtwd/cocousa/ui/module/application/Application;',
)

class AppV173(v172.AppV172):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.73')
        self._clean_v173(); self._install_v173()
        self.status.set('V1.73 lista · reconstruye lectura/escritura del access-token y configuración Retrofit real. Sin red ni escrituras OTA.')

    def _clean_v173(self):
        keep=('buscar relojes','buscar dispositivos','buscar disp','buscar actualización','buscar actualizacion','buscar actualizaciones')
        def walk(w):
            for c in list(w.winfo_children()):
                try:
                    if isinstance(c,(ttk.Button,tk.Button)):
                        t=str(c.cget('text') or '').lower()
                        if not any(x in t for x in keep):
                            try:c.pack_forget()
                            except Exception:pass
                            try:c.grid_remove()
                            except Exception:pass
                            try:c.place_forget()
                            except Exception:pass
                    else: walk(c)
                except Exception: pass
        walk(self.root)

    def _install_v173(self):
        top=self.root.winfo_children()[0]
        self.v173_button=ttk.Button(top,text='RECONSTRUIR TOKEN + RETROFIT',command=self.extract_token_retrofit)
        sib=top.winfo_children()
        try:self.v173_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except Exception:self.v173_button.place(x=8,y=8)

    def extract_token_retrofit(self):
        ready,validation,vpath=self._ready_report()
        if not ready:
            self.status.set('V1.73 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.73 · reconstruyendo access-token, login y base URL Retrofit…')
        def work():
            rep={'app_version':'1.73.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'reconstruct_exact_access_token_read_write_flow_and_retrofit_base_url_configuration_without_network_or_ota_writes',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'proven_contract':{'base_url':'https://wr.watchhealth.com.cn/app-halfwit/','check_path':'app-device/checkForUpdate','header':'access-token',
                                    'request_fields':['currentFirmware','language','macAddress','watchId']},
                 'token_readers':[],'token_writers':[],'user_manager_methods':[],'request_builders':[],
                 'base_url_users':[],'retrofit_builder_methods':[],'login_token_candidates':[],'exact_strings':[],
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            seen_strings=set()
            def add_row(dst,label,m,code,kind,acc,d):
                row={'dex':label,'class':m['class'],'method':m['name'],'method_idx':m['idx'],'proto':m.get('proto'),'kind':kind,'access_flags':acc,'code_off':code,
                     'strings':d.get('strings',[]),'calls':d.get('calls',[]),'fields':d.get('fields',[]),'consts':d.get('consts',[]),'raw_code_hex':d.get('raw_code_hex','')}
                dst.append(row)
            def inspect(label,b):
                try: strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex: rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                encmap={mid:(code,kind,acc) for _,mid,code,kind,acc in enc}
                for s in strings:
                    sl=s.lower()
                    if s in ('PREF_KEY_ACCESS_TOKEN','access-token','currentFirmware','language','macAddress','watchId') or 'app-halfwit' in sl or 'checkforupdate' in sl:
                        if s not in seen_strings:seen_strings.add(s);rep['exact_strings'].append(s)
                for m in methods:
                    code,kind,acc=encmap.get(m['idx'],(0,None,None))
                    if not code: continue
                    d=self._details(b,code,strings,methods,fields)
                    ss=[str(x) for x in d.get('strings',[])]
                    joined=' '.join(ss).lower()
                    calls=d.get('calls',[])
                    cls=m['class']
                    if cls=='Lcom/wtwd/cocousa/manager/UserManager;': add_row(rep['user_manager_methods'],label,m,code,kind,acc,d)
                    if 'pref_key_access_token' in joined or any(c.get('class')=='Lcom/wtwd/cocousa/manager/UserManager;' and c.get('method')=='a' for c in calls):
                        add_row(rep['token_readers'],label,m,code,kind,acc,d)
                    if ('pref_key_access_token' in joined and any(c.get('class')=='Lcom/wtwd/cocousa/utils/PrefUtil;' and c.get('method') in ('h','g','f','e') for c in calls)):
                        add_row(rep['token_writers'],label,m,code,kind,acc,d)
                    if cls in ('Lcom/wtwd/cocousa/ui/module/main/device/update/HardwareUpdateModel;','Lcom/wtwd/cocousa/ui/module/main/device/DeviceModel;') and (
                        any(x in ss for x in ('currentFirmware','language','macAddress','watchId')) or any(c.get('class')=='Lcom/wtwd/cocousa/api/BaseApi;' and c.get('method')=='i' for c in calls)):
                        add_row(rep['request_builders'],label,m,code,kind,acc,d)
                    if 'app-halfwit' in joined or 'wr.watchhealth.com.cn' in joined:
                        add_row(rep['base_url_users'],label,m,code,kind,acc,d)
                    retrofit_hit=any(('retrofit' in str(c.get('class','')).lower() or 'okhttp3' in str(c.get('class','')).lower()) and str(c.get('method','')).lower() in ('baseurl','client','build','addconverterfactory','addcalladapterfactory','url') for c in calls)
                    if retrofit_hit or (cls in TARGET_CLASSES and any(('retrofit' in str(c.get('class','')).lower() or 'okhttp3' in str(c.get('class','')).lower()) for c in calls)):
                        add_row(rep['retrofit_builder_methods'],label,m,code,kind,acc,d)
                    if ('login' in cls.lower() or 'verify' in cls.lower() or 'welcome' in cls.lower()) and (
                        'pref_key_access_token' in joined or 'access-token' in joined or any(c.get('class')=='Lcom/wtwd/cocousa/utils/PrefUtil;' and c.get('method')=='h' for c in calls)):
                        add_row(rep['login_token_candidates'],label,m,code,kind,acc,d)
            def inspect_apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')): inspect(name+'!'+n,z.read(n))
                except Exception as ex:rep.setdefault('errors',[]).append({'apk':name,'error':repr(ex)})
            if zipfile.is_zipfile(chosen):
                with zipfile.ZipFile(chosen,'r') as z:
                    apks=[n for n in z.namelist() if n.lower().endswith('.apk')]
                    if apks:
                        for n in apks:
                            if 'com.wtwd.utrawatch' in n.lower() or 'base' in n.lower(): inspect_apk(n,z.read(n))
                    else:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')): inspect(n,z.read(n))
            else:
                with open(chosen,'rb') as f: inspect_apk(os.path.basename(chosen),f.read())
            for k,lim in [('token_readers',200),('token_writers',200),('user_manager_methods',100),('request_builders',100),('base_url_users',100),('retrofit_builder_methods',300),('login_token_candidates',200)]:
                # de-duplicate by dex/method_idx
                seen=set(); out=[]
                for x in rep[k]:
                    q=(x['dex'],x['method_idx'])
                    if q not in seen:seen.add(q);out.append(x)
                rep[k]=out[:lim]
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v173');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-token-retrofit-v173.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.73 · falló: '+repr(err));return
            self.report={'token_retrofit_v173':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except Exception:pass
            self.status.set(f"V1.73 LISTO · lectores={len(rep['token_readers'])} · escritores={len(rep['token_writers'])} · baseURL={len(rep['base_url_users'])} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
