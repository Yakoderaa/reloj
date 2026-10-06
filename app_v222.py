import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v221 as v221
import app_v199 as v199
import app_v179 as v179
import app_v180 as v180
import app_v210 as v210
import app_v145 as v145

base.APP_VERSION='2.22.0'
TARGETS=('Lcom/wtwd/cocousa/ui/module/account/welcome/WelcomeModel;',
         'Lcom/wtwd/cocousa/ui/module/account/welcome/WelcomeModel$1;',
         'Lcom/wtwd/cocousa/ui/module/account/welcome/WelcomePresenter;')
NEEDLES=('appDeviceId','appIMEi','android_id')

class AppV222(v221.AppV221):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V2.22')
        self._clean_v222();self._install_v222();self._restore_location_button()
        self.status.set('V2.22 lista · cierra cómo se forma appDeviceId en UtraWatch. Sin red, activation, firmware ni OTA.')

    def _clean_v222(self):
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

    def _install_v222(self):
        top=self.root.winfo_children()[0]
        self.v222_button=ttk.Button(top,text='CERRAR APPDEVICEID',command=self.trace_appdeviceid)
        sib=top.winfo_children()
        try:self.v222_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v222_button.place(x=8,y=8)

    @staticmethod
    def _simple(a):
        try:return v210.AppV210._simple(a)
        except:return a

    def trace_appdeviceid(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V2.22 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        try:self.root.clipboard_clear();self.root.update_idletasks()
        except:pass
        self.face_guard_enabled=False
        self.status.set('V2.22 · siguiendo appDeviceId / appIMEi / android_id…')
        def work():
            rep={'app_version':'2.22.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'resolve_exact_appDeviceId_generation_chain_locally_before_any_network_request',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known_from_v221':{'AccessInfo.a':'token','AccessInfo.b':'userId','guest_callback':'WelcomeModel$1.c -> AccessInfo.a -> UserManager.g -> PREF_KEY_ACCESS_TOKEN'},
                 'methods':[],'string_hits':[],'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'guest_login_requests':0,'activation_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex_seen':0,'target_methods':0,'symbolized':0,'string_hits':0}
            def inspect(label,b):
                stats['dex_seen']+=1
                if not any(x.encode() in b for x in NEEDLES) and b'WelcomeModel' not in b:return
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                exact,err=v199.AppV199._exact_code_map(b,types)
                if err:rep.setdefault('exact_map_errors',[]).append({'dex':label,'error':err})
                needle_idxs={n:[i for i,s in enumerate(strings) if s==n] for n in NEEDLES}
                for m in methods:
                    cls=m.get('class');name=m.get('name');ex=exact.get(m.get('idx')) or {};code=ex.get('code_off');acc=ex.get('access_flags',0)
                    if not code:continue
                    hit_names=[]
                    for n,idxs in needle_idxs.items():
                        for idx in idxs:
                            try:
                                import app_v208 as v208
                                if v208.AppV208._code_refs_string(b,code,idx):hit_names.append(n);break
                            except:pass
                    target=cls in TARGETS
                    if hit_names:
                        rep['string_hits'].append({'dex':label,'class':cls,'method':name,'method_idx':m.get('idx'),'proto':m.get('proto'),'strings':hit_names})
                        stats['string_hits']+=1
                    if not (target or hit_names):continue
                    stats['target_methods']+=1
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc);sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except Exception as ex2:rep.setdefault('symbolic_errors',[]).append({'class':cls,'method':name,'error':repr(ex2)});continue
                    events=[]
                    for inv in sym.get('invokes') or []:
                        t=inv.get('target') or {};tc=t.get('class') or '';mn=t.get('method')
                        if ('Welcome' in tc or 'Settings$Secure' in tc or 'BaseApi' in tc or 'JsonUtils' in tc or 'BaseModel' in tc or 'TextUtils' in tc):
                            events.append({'unit':inv.get('unit'),'class':tc,'method':mn,'args':[self._simple(a) for a in (inv.get('args') or [])],'arg_regs':inv.get('arg_regs')})
                    rep['methods'].append({'dex':label,'class':cls,'method':name,'method_idx':m.get('idx'),'proto':m.get('proto'),'strings':hit_names,'incoming_registers':pmap,'events':events,'trace':(sym.get('trace') or [])[:3200]})
                    stats['symbolized']+=1
                self._progress(f'V2.22 · {label.split("!")[-1]} · strings={stats["string_hits"]} · sym={stats["symbolized"]}')
            def apk(name,data):
                with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                    dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                    for i,n in enumerate(dexes,1):
                        self._progress(f'V2.22 · DEX {i}/{len(dexes)} · {n}');inspect(name+'!'+n,z.read(n))
            try:
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
            except Exception as ex:rep.setdefault('errors',[]).append({'input':chosen,'error':repr(ex)})
            relevant=[]
            for r in rep['methods']:
                txt=json.dumps({'strings':r.get('strings'),'events':r.get('events'),'trace':r.get('trace')},ensure_ascii=False)
                if any(n in txt for n in NEEDLES):relevant.append({'class':r['class'],'method':r['method'],'proto':r['proto'],'strings':r.get('strings'),'events':r.get('events')})
            rep['scan_stats']=stats
            rep['resolved']={'relevant_methods':relevant,'appDeviceId_marker_found':any('appDeviceId' in x.get('strings',[]) for x in rep['string_hits']),
                             'appIMEi_marker_found':any('appIMEi' in x.get('strings',[]) for x in rep['string_hits']),
                             'android_id_marker_found':any('android_id' in x.get('strings',[]) for x in rep['string_hits']),
                             'network_gate':'NO_NETWORK_IN_THIS_VERSION','next':'Use the exact locally proven appDeviceId generation semantics for the first guest-login probe; do not reuse or impersonate an existing phone identifier.','write_gate':'NO_DEVICE_WRITES'}
            rep['summary']={'string_hits':stats['string_hits'],'symbolized':stats['symbolized'],'relevant_methods':len(relevant)}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v222');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-appdeviceid-v222.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V2.22 · falló: '+repr(err));return
            self.report={'utrawatch_appdeviceid_v222':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep.get('summary') or {}
            self.status.set(f"V2.22 LISTO · strings={s.get('string_hits',0)} · métodos={s.get('relevant_methods',0)} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV222(root);root.mainloop()
