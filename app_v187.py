import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v186 as v186
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='1.87.0'
BASEAPI=v186.BASEAPI
USERINFO='Lcom/wtwd/cocousa/entity/user/UserInfo;'
ACCESSINFO='Lcom/wtwd/cocousa/entity/user/AccessInfo;'

class AppV187(v186.AppV186):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.87')
        self._clean_v187();self._install_v187();self._restore_location_button()
        self.status.set('V1.87 lista · reconstruye el body exacto de touristLogin y la extracción de AccessInfo. Sin red ni OTA.')

    def _clean_v187(self):
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

    def _install_v187(self):
        top=self.root.winfo_children()[0]
        self.v187_button=ttk.Button(top,text='RECONSTRUIR SESIÓN INVITADO',command=self.resolve_tourist_contract)
        sib=top.winfo_children()
        try:self.v187_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v187_button.place(x=8,y=8)

    @staticmethod
    def _interesting(cls,name=''):
        q=(str(cls or '')+' '+str(name or '')).lower()
        if not (str(cls or '').lower().startswith('lcom/wtwd/cocousa/') or str(cls or '').lower().startswith('lcom/wtwd/')):return False
        return any(k in q for k in ('tourist','login','account','user','startup','splash','welcome','accessinfo','userinfo','token','session'))

    @staticmethod
    def _field_rows(fields,ctype):
        out=[]
        for f in fields:
            try:
                if f.get('class')==ctype:out.append({'idx':f.get('idx'),'name':f.get('name'),'type':f.get('type')})
            except:pass
        return out

    def resolve_tourist_contract(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V1.87 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.87 · buscando exactamente quién llama touristLogin…')
        def work():
            rep={'app_version':'1.87.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'reconstruct_exact_touristLogin_request_body_and_AccessInfo_token_extraction_without_credentials_network_or_ota',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'tourist_endpoint':{'base_url':'https://wr.watchhealth.com.cn/app-halfwit/','path':'app-user/touristLogin','baseapi_method':'B','request_type':'okhttp3.RequestBody','response_type':'ResponseContent<AccessInfo>'},
                 'tourist_call_sites':[],'userinfo_fields':[],'accessinfo_fields':[],'userinfo_methods':[],'accessinfo_methods':[],
                 'relevant_strings':[],'scan_stats':{},'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'credential_collection':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            seen_s=set();stats={'dex':0,'methods_total':0,'methods_symbolic':0,'candidate_methods':0}
            def inspect(label,b):
                stats['dex']+=1;self._progress(f'V1.87 · {label} · leyendo estructura…')
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                rep['userinfo_fields'] += [{'dex':label,**x} for x in self._field_rows(fields,USERINFO)]
                rep['accessinfo_fields'] += [{'dex':label,**x} for x in self._field_rows(fields,ACCESSINFO)]
                for s in strings:
                    low=str(s).lower()
                    if any(k in low for k in ('touristlogin','tourist','accesstoken','access_token','deviceid','device_id','androidid','android_id','language','country','timezone','userinfo','accessinfo')):
                        if s not in seen_s:
                            seen_s.add(s);rep['relevant_strings'].append({'dex':label,'value':s})
                em={mid:(code,kind,acc) for _,mid,code,kind,acc in enc};stats['methods_total']+=len(methods)
                targets=[]
                for m in methods:
                    cls=m.get('class');name=m.get('name')
                    if cls in (USERINFO,ACCESSINFO) or self._interesting(cls,name):targets.append(m)
                stats['candidate_methods']+=len(targets)
                self._progress(f'V1.87 · {label} · analizando {len(targets)} candidatos…')
                for pos,m in enumerate(targets):
                    code,kind,acc=em.get(m.get('idx'),(0,None,None))
                    if not code:continue
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc);sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except:continue
                    stats['methods_symbolic']+=1
                    cls=m.get('class');name=m.get('name')
                    compact={'dex':label,'class':cls,'method':name,'method_idx':m.get('idx'),'proto':m.get('proto'),'incoming_registers':pmap,
                             'invokes':sym.get('invokes',[])[:180],'field_writes':sym.get('critical_field_writes',[])[:120],'returns':sym.get('returns',[])[:40]}
                    if cls==USERINFO:rep['userinfo_methods'].append(compact)
                    if cls==ACCESSINFO:rep['accessinfo_methods'].append(compact)
                    for inv in sym.get('invokes',[]):
                        t=inv.get('target') or {}
                        if t.get('class')==BASEAPI and t.get('method')=='B':
                            rep['tourist_call_sites'].append({**compact,'tourist_invoke':inv})
                            break
                    if pos and pos%100==0:self._progress(f'V1.87 · {label} · {pos}/{len(targets)} candidatos…')
            def apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                        for i,n in enumerate(dexes,1):
                            self._progress(f'V1.87 · DEX {i}/{len(dexes)} · {n}')
                            inspect(name+'!'+n,z.read(n))
                except Exception as ex:rep.setdefault('errors',[]).append({'apk':name,'error':repr(ex)})
            if zipfile.is_zipfile(chosen):
                with zipfile.ZipFile(chosen,'r') as z:
                    apks=[n for n in z.namelist() if n.lower().endswith('.apk')]
                    if apks:
                        preferred=[n for n in apks if 'com.wtwd.utrawatch' in n.lower() or os.path.basename(n).lower().startswith(('base','master'))]
                        for i,n in enumerate(preferred or apks[:1],1):
                            self._progress(f'V1.87 · APK {i} · {os.path.basename(n)}')
                            apk(n,z.read(n))
                    else:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')):inspect(n,z.read(n))
            else:
                with open(chosen,'rb') as f:apk(os.path.basename(chosen),f.read())
            # Reduce the result to strong hints useful for the next executable version.
            body_hints=[];token_hints=[]
            for c in rep['tourist_call_sites']:
                txt=json.dumps(c,ensure_ascii=False)
                for key in ('deviceId','device_id','androidId','android_id','language','country','timezone','uuid','mac','model','version'):
                    if key.lower() in txt.lower():body_hints.append(key)
            for m in rep['accessinfo_methods']:
                txt=json.dumps(m,ensure_ascii=False).lower()
                if 'access' in txt and 'token' in txt:token_hints.append({'class':m.get('class'),'method':m.get('method'),'method_idx':m.get('method_idx')})
            rep['scan_stats']=stats
            rep['resolved']={'tourist_call_sites':len(rep['tourist_call_sites']),'request_body_field_hints':sorted(set(body_hints)),
                             'access_token_method_hints':token_hints[:30],
                             'manual_access_token_required':False,
                             'next':'If the touristLogin call site fully resolves the RequestBody and AccessInfo token getter, issue one official touristLogin request and then one checkForUpdate request. Keep OTA writes disabled.',
                             'write_gate':'KEEP_OTA_DISABLED_UNTIL_OFFICIAL_FIRMWARE_METADATA_AND_FILE_VALIDATION_SUCCEED'}
            rep['summary']={'tourist_call_sites':len(rep['tourist_call_sites']),'userinfo_fields':len(rep['userinfo_fields']),'accessinfo_fields':len(rep['accessinfo_fields']),
                            'userinfo_methods':len(rep['userinfo_methods']),'accessinfo_methods':len(rep['accessinfo_methods']),'methods_symbolic':stats['methods_symbolic']}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v187');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-tourist-contract-v187.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.87 · falló: '+repr(err));return
            self.report={'utrawatch_tourist_contract_v187':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep['summary'];self.status.set(f"V1.87 LISTO · tourist calls={s['tourist_call_sites']} · UserInfo={s['userinfo_fields']} campos · AccessInfo={s['accessinfo_fields']} campos · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV187(root);root.mainloop()
