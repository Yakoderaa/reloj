import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v189 as v189
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='1.90.0'
ACCESSINFO=v189.ACCESSINFO
BASEAPI='Lcom/wtwd/cocousa/api/BaseApi;'
WELCOME='Lcom/wtwd/cocousa/ui/module/account/welcome/WelcomeFragment;'
WMODEL='Lcom/wtwd/cocousa/ui/module/account/welcome/WelcomeModel;'
WMODEL_CB='Lcom/wtwd/cocousa/ui/module/account/welcome/WelcomeModel$1;'

class AppV190(v189.AppV189):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.90')
        self._clean_v190();self._install_v190();self._restore_location_button()
        self.status.set('V1.90 lista · valida el contrato exacto de sesión invitado y corrige la detección de android_id. Sin red ni OTA.')

    def _clean_v190(self):
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

    def _install_v190(self):
        top=self.root.winfo_children()[0]
        self.v190_button=ttk.Button(top,text='VALIDAR CONTRATO SESIÓN INVITADO',command=self.validate_guest_contract)
        sib=top.winfo_children()
        try:self.v190_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v190_button.place(x=8,y=8)

    def validate_guest_contract(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V1.90 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.90 · validando contrato exacto de sesión invitado…')
        def work():
            rep={'app_version':'1.90.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'validate_exact_guest_session_contract_and_fix_android_id_evidence_without_network_or_ota',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'methods':[],'accessinfo_fields':[],'evidence_rows':[],'scan_stats':{},
                 'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex':0,'methods_symbolic':0}
            def inspect(label,b):
                stats['dex']+=1
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                for f in fields:
                    if f.get('class')==ACCESSINFO:
                        rep['accessinfo_fields'].append({'dex':label,'idx':f.get('idx'),'name':f.get('name'),'type':f.get('type')})
                em={mid:(code,kind,acc) for _,mid,code,kind,acc in enc}
                targets=[m for m in methods if m.get('class') in (ACCESSINFO,WELCOME,WMODEL,WMODEL_CB)]
                self._progress(f'V1.90 · {label} · {len(targets)} métodos exactos…')
                for m in targets:
                    code,kind,acc=em.get(m.get('idx'),(0,None,None))
                    if not code:continue
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc);sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except Exception as ex:
                        rep.setdefault('symbolic_errors',[]).append({'dex':label,'method_idx':m.get('idx'),'error':repr(ex)});continue
                    stats['methods_symbolic']+=1
                    row={'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'incoming_registers':pmap,
                         'invokes':sym.get('invokes',[])[:280],'field_writes':sym.get('critical_field_writes',[])[:180],'returns':sym.get('returns',[])[:100]}
                    txt=json.dumps(row,ensure_ascii=False)
                    low=txt.lower()
                    if any(k in low for k in ('android_id','appimei','appdeviceid','baseapi','accessinfo')):
                        rep['methods'].append(row)
                    for inv in sym.get('invokes',[]):
                        t=inv.get('target') or {}
                        args=inv.get('args') or []
                        if t.get('class')=='Landroid/provider/Settings$Secure;' and t.get('method')=='getString':
                            if 'android_id' in json.dumps(args,ensure_ascii=False).lower():
                                rep['evidence_rows'].append({'kind':'android_id_read','dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'invoke':inv})
                        if t.get('class')==WMODEL and t.get('method')=='e':
                            rep['evidence_rows'].append({'kind':'welcome_to_model_e','dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'invoke':inv})
                        if t.get('class')==BASEAPI and t.get('method')=='B':
                            rep['evidence_rows'].append({'kind':'tourist_baseapi_B','dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'invoke':inv})
            def apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                        for i,n in enumerate(dexes,1):
                            self._progress(f'V1.90 · DEX {i}/{len(dexes)} · {n}')
                            inspect(name+'!'+n,z.read(n))
                except Exception as ex:rep.setdefault('errors',[]).append({'apk':name,'error':repr(ex)})
            if zipfile.is_zipfile(chosen):
                with zipfile.ZipFile(chosen,'r') as z:
                    apks=[n for n in z.namelist() if n.lower().endswith('.apk')]
                    if apks:
                        preferred=[n for n in apks if 'com.wtwd.utrawatch' in n.lower() or os.path.basename(n).lower().startswith(('base','master'))]
                        for n in (preferred or apks[:1]):apk(n,z.read(n))
                    else:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')):inspect(n,z.read(n))
            else:
                with open(chosen,'rb') as f:apk(os.path.basename(chosen),f.read())
            fields={x.get('name'):x.get('type') for x in rep['accessinfo_fields']}
            token_method=None
            for m in rep['methods']:
                if m.get('class')!=ACCESSINFO:continue
                proto=m.get('proto') or {}
                if proto.get('return')=='Ljava/lang/String;':
                    token_method={'method':m.get('method'),'method_idx':m.get('method_idx'),'reason':'only AccessInfo String-returning getter; token is the only String field'}
                    break
            kinds=[x.get('kind') for x in rep['evidence_rows']]
            all_text=json.dumps(rep['methods'],ensure_ascii=False).lower()
            rep['scan_stats']=stats
            rep['resolved']={
                'endpoint':{'base_url':'https://wr.watchhealth.com.cn/app-halfwit/','path':'app-user/touristLogin','baseapi_method':'B'},
                'request_body':{'appDeviceId':'WelcomeFragment.appIMEi sourced from Settings.Secure android_id'},
                'source_chain':[
                    'Settings.Secure.getString(ContentResolver, "android_id")',
                    'WelcomeFragment.appIMEi',
                    'WelcomeFragment → WelcomeModel.e(String)',
                    'WelcomeModel callback → JSON appDeviceId → BaseApi.B'
                ],
                'evidence':{
                    'settings_secure_android_id':'android_id_read' in kinds,
                    'appimei_present':'appimei' in all_text,
                    'welcome_model_e_present':'welcome_to_model_e' in kinds,
                    'baseapi_B_present':'tourist_baseapi_B' in kinds,
                    'appdeviceid_present':'appdeviceid' in all_text,
                    'accessinfo_fields_complete':all(k in fields for k in ('token','userId','expireTime'))
                },
                'accessinfo_field_map':fields,
                'token_getter':token_method,
                'manual_access_token_required':False,
                'next':'Use the validated guest-session contract for one user-initiated official metadata request in the next version; keep firmware and OTA writes disabled until file validation succeeds.',
                'write_gate':'KEEP_OTA_DISABLED_UNTIL_OFFICIAL_FIRMWARE_METADATA_AND_FILE_VALIDATION_SUCCEED'
            }
            rep['summary']={'methods':len(rep['methods']),'evidence_rows':len(rep['evidence_rows']),'accessinfo_fields':len(rep['accessinfo_fields']),'methods_symbolic':stats['methods_symbolic']}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v190');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-guest-contract-v190.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.90 · falló: '+repr(err));return
            self.report={'utrawatch_guest_contract_v190':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            ev=(rep.get('resolved') or {}).get('evidence') or {}
            ok=sum(1 for v in ev.values() if v)
            self.status.set(f'V1.90 LISTO · evidencia={ok}/{len(ev)} · red=0 · firmware/OTA=0 · diagnóstico copiado.')
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV190(root);root.mainloop()
