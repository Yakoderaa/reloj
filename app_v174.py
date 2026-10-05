import io, json, os, zipfile
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, filedialog
import app as base
import app_v172 as v172
import app_v145 as v145

base.APP_VERSION='1.74.0'
UM='Lcom/wtwd/cocousa/manager/UserManager;'
ACCESS='Lcom/wtwd/cocousa/entity/user/AccessInfo;'
BASEAPI='Lcom/wtwd/cocousa/api/BaseApi;'
ACCOUNT='Lcom/wtwd/cocousa/ui/module/account/'
UPDATE='Lcom/wtwd/cocousa/ui/module/main/device/update/'

class AppV174(v172.AppV172):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.74')
        self._clean_v174(); self._install_v174()
        self.status.set('V1.74 lista · prueba el origen exacto del token desde AccessInfo y mapea login→UserManager→checkForUpdate. Sin red ni OTA.')

    def _clean_v174(self):
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
                except Exception:pass
        walk(self.root)

    def _install_v174(self):
        top=self.root.winfo_children()[0]
        self.v174_button=ttk.Button(top,text='PROBAR ORIGEN TOKEN OTA',command=self.extract_token_provenance)
        sib=top.winfo_children()
        try:self.v174_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except Exception:self.v174_button.place(x=8,y=8)

    def extract_token_provenance(self):
        ready,validation,vpath=self._ready_report()
        if not ready:
            self.status.set('V1.74 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.74 · trazando AccessInfo → UserManager → request OTA…')
        def work():
            rep={'app_version':'1.74.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'prove_exact_access_token_value_flow_from_login_response_to_persistence_and_firmware_check_without_network_or_ota_writes',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known_from_v173':{'base_url':'https://wr.watchhealth.com.cn/app-halfwit/','check_path':'app-device/checkForUpdate','header':'access-token',
                    'login_callbacks_call':['AccessInfo.a()','AccessInfo.b()','UserManager.g(String)','UserManager.h(String)'],
                    'request_fields':['currentFirmware','language','macAddress','watchId']},
                 'access_info_methods':[],'access_info_fields':[],'login_callbacks':[],'user_manager_setter_callers':[],
                 'account_api_callers':[],'hardware_update_flow':[],'candidate_token_chain':[],
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            def row(label,m,code,kind,acc,d):
                return {'dex':label,'class':m['class'],'method':m['name'],'method_idx':m['idx'],'proto':m.get('proto'),'kind':kind,'access_flags':acc,'code_off':code,
                        'strings':d.get('strings',[]),'calls':d.get('calls',[]),'fields':d.get('fields',[]),'consts':d.get('consts',[]),'raw_code_hex':d.get('raw_code_hex','')}
            def inspect(label,b):
                try: strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                encmap={mid:(code,kind,acc) for _,mid,code,kind,acc in enc}
                for f in fields:
                    if f.get('class')==ACCESS: rep['access_info_fields'].append({'dex':label,**f})
                for m in methods:
                    code,kind,acc=encmap.get(m['idx'],(0,None,None))
                    if not code:continue
                    d=self._details(b,code,strings,methods,fields); calls=d.get('calls',[]); cls=m['class']; rr=None
                    if cls==ACCESS:
                        rr=row(label,m,code,kind,acc,d);rep['access_info_methods'].append(rr)
                    if cls.startswith(ACCOUNT) and any(c.get('class')==ACCESS for c in calls):
                        rr=rr or row(label,m,code,kind,acc,d);rep['login_callbacks'].append(rr)
                    if any(c.get('class')==UM and c.get('method') in ('f','g','h') for c in calls):
                        rr=rr or row(label,m,code,kind,acc,d);rep['user_manager_setter_callers'].append(rr)
                    if cls.startswith(ACCOUNT) and any(c.get('class')==BASEAPI for c in calls):
                        rr=rr or row(label,m,code,kind,acc,d);rep['account_api_callers'].append(rr)
                    if cls.startswith(UPDATE) or any(c.get('class')==BASEAPI and c.get('method')=='i' for c in calls):
                        rr=rr or row(label,m,code,kind,acc,d);rep['hardware_update_flow'].append(rr)
                    if any(c.get('class')==ACCESS and c.get('method')=='a' for c in calls) and any(c.get('class')==UM and c.get('method')=='h' for c in calls):
                        rr=rr or row(label,m,code,kind,acc,d);rep['candidate_token_chain'].append(rr)
            def apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')):inspect(name+'!'+n,z.read(n))
                except Exception as ex:rep.setdefault('errors',[]).append({'apk':name,'error':repr(ex)})
            if zipfile.is_zipfile(chosen):
                with zipfile.ZipFile(chosen,'r') as z:
                    apks=[n for n in z.namelist() if n.lower().endswith('.apk')]
                    if apks:
                        for n in apks:
                            if 'com.wtwd.utrawatch' in n.lower() or 'base' in n.lower():apk(n,z.read(n))
                    else:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')):inspect(n,z.read(n))
            else:
                with open(chosen,'rb') as f:apk(os.path.basename(chosen),f.read())
            for k,lim in [('access_info_methods',100),('login_callbacks',100),('user_manager_setter_callers',200),('account_api_callers',250),('hardware_update_flow',100),('candidate_token_chain',100)]:
                seen=set();out=[]
                for x in rep[k]:
                    q=(x['dex'],x['method_idx'])
                    if q not in seen:seen.add(q);out.append(x)
                rep[k]=out[:lim]
            rep['proof_summary']={'login_callbacks_with_accessinfo_a_and_usermanager_h':len(rep['candidate_token_chain']),'access_info_method_count':len(rep['access_info_methods']),'account_api_caller_count':len(rep['account_api_callers']),'hardware_update_method_count':len(rep['hardware_update_flow'])}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v174');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-token-provenance-v174.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.74 · falló: '+repr(err));return
            self.report={'token_provenance_v174':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except Exception:pass
            self.status.set(f"V1.74 LISTO · cadena token={len(rep['candidate_token_chain'])} · login={len(rep['login_callbacks'])} · API cuenta={len(rep['account_api_callers'])} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV174(root);root.mainloop()
