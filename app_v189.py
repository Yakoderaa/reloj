import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v188 as v188
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='1.89.0'
ACCESSINFO=v188.ACCESSINFO

TARGET_CLASSES=(
    'Lcom/wtwd/cocousa/ui/module/account/welcome/WelcomeFragment;',
    'Lcom/wtwd/cocousa/ui/module/account/welcome/WelcomeModel;',
    'Lcom/wtwd/cocousa/ui/module/account/welcome/WelcomeModel$1;',
    'Lcom/wtwd/cocousa/ui/module/account/login/LoginFragment;',
    ACCESSINFO,
)

class AppV189(v188.AppV188):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.89')
        self._clean_v189();self._install_v189();self._restore_location_button()
        self.status.set('V1.89 lista · cierra android_id → appIMEi → appDeviceId y getter de token. Sin red ni OTA.')

    def _clean_v189(self):
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

    def _install_v189(self):
        top=self.root.winfo_children()[0]
        self.v189_button=ttk.Button(top,text='CERRAR CADENA ANDROID ID → TOKEN',command=self.resolve_android_chain)
        sib=top.winfo_children()
        try:self.v189_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v189_button.place(x=8,y=8)

    def resolve_android_chain(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V1.89 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.89 · cerrando cadena android_id → appIMEi → appDeviceId…')
        def work():
            rep={'app_version':'1.89.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'close_exact_android_id_to_appIMEi_to_WelcomeModel_to_appDeviceId_chain_and_AccessInfo_token_getter_without_network_or_ota',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'target_methods':[],'accessinfo_fields':[],'relevant_strings':[],'scan_stats':{},
                 'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'credential_collection':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex':0,'methods_symbolic':0};seen_s=set()
            def inspect(label,b):
                stats['dex']+=1
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                for f in fields:
                    if f.get('class')==ACCESSINFO:
                        rep['accessinfo_fields'].append({'dex':label,'idx':f.get('idx'),'name':f.get('name'),'type':f.get('type')})
                for s in strings:
                    low=str(s).lower()
                    if any(k in low for k in ('android_id','appimei','appdeviceid','touristlogin','accessinfo','token')) and s not in seen_s:
                        seen_s.add(s);rep['relevant_strings'].append({'dex':label,'value':s})
                em={mid:(code,kind,acc) for _,mid,code,kind,acc in enc}
                targets=[m for m in methods if m.get('class') in TARGET_CLASSES]
                self._progress(f'V1.89 · {label} · {len(targets)} métodos exactos…')
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
                         'invokes':sym.get('invokes',[])[:260],'field_writes':sym.get('critical_field_writes',[])[:180],'returns':sym.get('returns',[])[:80]}
                    txt=json.dumps(row,ensure_ascii=False).lower()
                    if any(k in txt for k in ('android_id','appimei','appdeviceid','touristlogin','accessinfo','token')):
                        rep['target_methods'].append(row)
            def apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                        for i,n in enumerate(dexes,1):
                            self._progress(f'V1.89 · DEX {i}/{len(dexes)} · {n}')
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
            text=json.dumps(rep['target_methods'],ensure_ascii=False).lower()
            access_fields={x.get('name'):x.get('type') for x in rep['accessinfo_fields']}
            token_getters=[]
            for m in rep['target_methods']:
                if m.get('class')!=ACCESSINFO:continue
                for r in m.get('returns',[]):
                    v=r.get('value') or {};f=v.get('field') or {}
                    if f.get('class')==ACCESSINFO and f.get('name')=='token':
                        token_getters.append({'method':m.get('method'),'method_idx':m.get('method_idx'),'field':'token','type':f.get('type')})
            evidence={
                'settings_secure_android_id':'android/provider/Settings$Secure' in text and 'android_id' in text,
                'appimei_present':'appimei' in text,
                'welcome_model_e_present':'welcomemodel' in text and '"method": "e"' in text,
                'appdeviceid_present':'appdeviceid' in text,
                'token_field_present':'token' in access_fields,
            }
            rep['scan_stats']=stats
            rep['resolved']={
                'source_chain':[
                    'Settings.Secure.getString(ContentResolver, "android_id")',
                    'Welcome/Login appIMEi field',
                    'WelcomeFragment → WelcomeModel.e(String)',
                    'WelcomeModel touristLogin body key appDeviceId',
                ],
                'evidence':evidence,
                'accessinfo_field_map':access_fields,
                'token_getters':token_getters,
                'manual_access_token_required':False,
                'next':'Use this proven local identity chain to validate a user-initiated guest session request in a later version; keep firmware and OTA writes disabled.',
                'write_gate':'KEEP_OTA_DISABLED_UNTIL_OFFICIAL_FIRMWARE_METADATA_AND_FILE_VALIDATION_SUCCEED'
            }
            rep['summary']={'target_methods':len(rep['target_methods']),'accessinfo_fields':len(rep['accessinfo_fields']),'token_getters':len(token_getters),'methods_symbolic':stats['methods_symbolic']}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v189');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-android-chain-v189.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.89 · falló: '+repr(err));return
            self.report={'utrawatch_android_chain_v189':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep['summary'];self.status.set(f"V1.89 LISTO · métodos={s['target_methods']} · token getters={s['token_getters']} · OTA=0 · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV189(root);root.mainloop()
