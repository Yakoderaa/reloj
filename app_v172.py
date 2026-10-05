import io, json, os, zipfile
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, filedialog
import app as base
import app_v171 as v171
import app_v166 as v166
import app_v145 as v145

base.APP_VERSION='1.72.0'
BASE_API='Lcom/wtwd/cocousa/api/BaseApi;'
UPDATE_PREFIX='Lcom/wtwd/cocousa/ui/module/main/device/update/'

class AppV172(v171.AppV171):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.72')
        self._clean_v172(); self._install_v172()
        self.status.set('V1.72 lista · rastrea origen de access-token, URL base y construcción exacta de checkForUpdate. Sin red ni escrituras OTA.')

    def _clean_v172(self):
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

    def _install_v172(self):
        top=self.root.winfo_children()[0]
        self.v172_button=ttk.Button(top,text='RASTREAR TOKEN Y REQUEST OTA',command=self.extract_auth_request)
        sib=top.winfo_children()
        try:self.v172_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except Exception:self.v172_button.place(x=8,y=8)

    def extract_auth_request(self):
        ready,validation,vpath=self._ready_report()
        if not ready:
            self.status.set('V1.72 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.72 · rastreando access-token, Retrofit base y request de firmware…')
        def work():
            rep={'app_version':'1.72.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'trace_exact_access_token_source_retrofit_base_url_and_checkForUpdate_request_builder_without_network_or_ota_writes',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'proven_contract':{
                    'base_url_candidate':'https://wr.watchhealth.com.cn/app-halfwit/',
                    'check_method':'POST','check_path':'app-device/checkForUpdate','check_header':'access-token','check_body':'RequestBody',
                    'download_method':'GET','download_url':'@Url String','download_streaming':True,'download_return':'okhttp3.ResponseBody'},
                 'interesting_methods':[],'auth_strings':[],'url_strings':[],'request_field_strings':[],
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            seen_auth=set();seen_url=set();seen_fields=set()
            needles=('access-token','accesstoken','token','authorization','login','touristlogin','userinfo','pref_key','sharedpreferences','app-halfwit','checkforupdate','currentfirmware','language','macaddress','watchid','filepath','hardwareversion')
            def inspect(label,b):
                try: strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex: rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                encmap={mid:(code,kind,acc) for _,mid,code,kind,acc in enc}
                for s in strings:
                    sl=s.lower()
                    if any(k in sl for k in ('access-token','accesstoken','authorization','touristlogin','login','pref_key','token')) and len(s)<800:
                        if s not in seen_auth:seen_auth.add(s);rep['auth_strings'].append(s)
                    if ('watchhealth.com.cn' in sl or 'app-halfwit' in sl or sl.startswith('http://') or sl.startswith('https://')) and len(s)<800:
                        if s not in seen_url:seen_url.add(s);rep['url_strings'].append(s)
                    if s in ('currentFirmware','language','macAddress','watchId','filePath','fileType','version','access-token'):
                        if s not in seen_fields:seen_fields.add(s);rep['request_field_strings'].append(s)
                for m in methods:
                    code,kind,acc=encmap.get(m['idx'],(0,None,None))
                    if not code: continue
                    d=self._details(b,code,strings,methods,fields)
                    ss=[str(x) for x in d.get('strings',[])]
                    calls=d.get('calls',[])
                    joined=' '.join(ss).lower()
                    hit_strings=any(n in joined for n in needles)
                    hit_calls=any((c.get('class')==BASE_API and c.get('method') in ('i','y','B','k')) for c in calls)
                    hit_update=m['class'].startswith(UPDATE_PREFIX)
                    if hit_strings or hit_calls or hit_update:
                        score=(3 if hit_calls else 0)+(2 if hit_update else 0)+sum(1 for n in needles if n in joined)
                        if score>=2:
                            rep['interesting_methods'].append({'score':score,'dex':label,'class':m['class'],'method':m['name'],'method_idx':m['idx'],'proto':m.get('proto'),'kind':kind,'access_flags':acc,'code_off':code,
                                'strings':ss,'calls':calls,'fields':d.get('fields',[]),'consts':d.get('consts',[]),'raw_code_hex':d.get('raw_code_hex','')})
            def inspect_apk(name,data):
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
                            if 'com.wtwd.utrawatch' in n.lower() or 'base' in n.lower():inspect_apk(n,z.read(n))
                    else:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')):inspect(n,z.read(n))
            else:
                with open(chosen,'rb') as f:inspect_apk(os.path.basename(chosen),f.read())
            rep['interesting_methods']=sorted(rep['interesting_methods'],key=lambda x:x['score'],reverse=True)[:500]
            rep['auth_strings']=rep['auth_strings'][:500];rep['url_strings']=rep['url_strings'][:500]
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v172');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-auth-request-v172.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.72 · falló: '+repr(err));return
            self.report={'auth_request_v172':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except Exception:pass
            self.status.set(f"V1.72 LISTO · métodos={len(rep['interesting_methods'])} · auth={len(rep['auth_strings'])} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV172(root);root.mainloop()
