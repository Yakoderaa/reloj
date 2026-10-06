import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v220 as v220
import app_v199 as v199
import app_v179 as v179
import app_v180 as v180
import app_v210 as v210
import app_v145 as v145

base.APP_VERSION='2.21.0'
ACCESS='Lcom/wtwd/cocousa/entity/user/AccessInfo;'
WELCOME1='Lcom/wtwd/cocousa/ui/module/account/welcome/WelcomeModel$1;'
UM='Lcom/wtwd/cocousa/manager/UserManager;'

class AppV221(v220.AppV220):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V2.21')
        self._clean_v221();self._install_v221();self._restore_location_button()
        self.status.set('V2.21 lista · cierra AccessInfo.a/b y WelcomeModel$1.c sin red ni OTA.')

    def _clean_v221(self):
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

    def _install_v221(self):
        top=self.root.winfo_children()[0]
        self.v221_button=ttk.Button(top,text='CERRAR ACCESSINFO EXACTO',command=self.trace_accessinfo)
        sib=top.winfo_children()
        try:self.v221_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v221_button.place(x=8,y=8)

    @staticmethod
    def _simple(a):
        try:return v210.AppV210._simple(a)
        except:return a

    def trace_accessinfo(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V2.21 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        try:self.root.clipboard_clear();self.root.update_idletasks()
        except:pass
        self.face_guard_enabled=False
        self.status.set('V2.21 · resolviendo AccessInfo.a/b y callback guest…')
        def work():
            rep={'app_version':'2.21.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'resolve_exact_AccessInfo_token_and_userid_fields_and_WelcomeModel1_guest_callback_locally',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known_from_v220':{'token_pref_writer':'UserManager.g(String) -> PREF_KEY_ACCESS_TOKEN','guest_callback':'WelcomeModel$1.c -> AccessInfo.a(response) -> UserManager.g','pref_xrefs':3},
                 'methods':[],'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'guest_login_requests':0,'activation_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex_seen':0,'target_methods':0,'symbolized':0}
            def inspect(label,b):
                stats['dex_seen']+=1
                if b'AccessInfo' not in b and b'WelcomeModel$1' not in b:return
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                exact,err=v199.AppV199._exact_code_map(b,types)
                if err:rep.setdefault('exact_map_errors',[]).append({'dex':label,'error':err})
                for m in methods:
                    cls=m.get('class');name=m.get('name')
                    target=(cls==ACCESS) or (cls==WELCOME1 and name=='c')
                    if not target:continue
                    ex=exact.get(m.get('idx')) or {};code=ex.get('code_off');acc=ex.get('access_flags',0)
                    if not code:continue
                    stats['target_methods']+=1
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc);sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except Exception as ex2:rep.setdefault('symbolic_errors',[]).append({'class':cls,'method':name,'error':repr(ex2)});continue
                    events=[]
                    for inv in sym.get('invokes') or []:
                        t=inv.get('target') or {};tc=t.get('class');mn=t.get('method')
                        if tc in (ACCESS,UM) or (tc and ('PrefUtil' in tc or 'WelcomeModel' in tc)):
                            events.append({'unit':inv.get('unit'),'class':tc,'method':mn,'args':[self._simple(a) for a in (inv.get('args') or [])],'arg_regs':inv.get('arg_regs')})
                    rep['methods'].append({'dex':label,'class':cls,'method':name,'method_idx':m.get('idx'),'proto':m.get('proto'),'incoming_registers':pmap,'events':events,'trace':(sym.get('trace') or [])[:2600]})
                    stats['symbolized']+=1
                self._progress(f'V2.21 · {label.split("!")[-1]} · targets={stats["target_methods"]}')
            def apk(name,data):
                with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                    dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                    for i,n in enumerate(dexes,1):
                        self._progress(f'V2.21 · DEX {i}/{len(dexes)} · {n}');inspect(name+'!'+n,z.read(n))
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
            access=[r for r in rep['methods'] if r['class']==ACCESS]
            cb=next((r for r in rep['methods'] if r['class']==WELCOME1 and r['method']=='c'),None)
            def returned_field(r):
                for t in r.get('trace') or []:
                    if t.get('kind')=='return':
                        v=t.get('value') or {}
                        if isinstance(v,dict) and v.get('kind')=='instance_field':return v.get('field')
                return None
            amap={r['method']:returned_field(r) for r in access if r['method'] in ('a','b')}
            cb_events=(cb or {}).get('events') or []
            rep['scan_stats']=stats
            rep['resolved']={'AccessInfo_a_return_field':amap.get('a'),'AccessInfo_b_return_field':amap.get('b'),'guest_callback_events':cb_events,
                'token_chain_confirmed':any(e.get('class')==ACCESS and e.get('method')=='a' for e in cb_events) and any(e.get('class')==UM and e.get('method')=='g' for e in cb_events),
                'network_gate':'NO_NETWORK_IN_THIS_VERSION','next':'If AccessInfo.a resolves to the access-token field and callback order is unambiguous, the next step is a single guest-login probe with token kept transient and never logged raw; no activation/download/OTA yet.','write_gate':'NO_DEVICE_WRITES'}
            rep['summary']={'target_methods':stats['target_methods'],'symbolized':stats['symbolized'],'access_methods':len(access),'callback_found':cb is not None,'token_chain_confirmed':rep['resolved']['token_chain_confirmed']}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v221');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-accessinfo-v221.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V2.21 · falló: '+repr(err));return
            self.report={'utrawatch_accessinfo_v221':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep.get('summary') or {}
            self.status.set(f"V2.21 LISTO · access={s.get('access_methods',0)} · callback={s.get('callback_found')} · chain={s.get('token_chain_confirmed')} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV221(root);root.mainloop()
