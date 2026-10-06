import io,json,os,zipfile,struct
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v219 as v219
import app_v208 as v208
import app_v199 as v199
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='2.20.0'
KEY='PREF_KEY_ACCESS_TOKEN'
TARGET_CLASS_PARTS=('UserManager','WelcomeModel','WelcomePresenter','Login','Tourist','UserInfo','UserBean')

class AppV220(v219.AppV219):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V2.20')
        self._clean_v220();self._install_v220();self._restore_location_button()
        self.status.set('V2.20 lista · cierra localmente de dónde sale y dónde se guarda access-token. Sin red ni OTA.')

    def _clean_v220(self):
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
                    else:walk(c)
                except:pass
        walk(self.root)

    def _install_v220(self):
        top=self.root.winfo_children()[0]
        self.v220_button=ttk.Button(top,text='CERRAR TOKEN RESPONSE',command=self.trace_token_response)
        sib=top.winfo_children()
        try:self.v220_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v220_button.place(x=8,y=8)

    @staticmethod
    def _simple(a):
        try:
            import app_v210 as v210
            return v210.AppV210._simple(a)
        except:return a

    def trace_token_response(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V2.20 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        try:self.root.clipboard_clear();self.root.update_idletasks()
        except:pass
        self.face_guard_enabled=False
        self.status.set('V2.20 · buscando xrefs exactos de PREF_KEY_ACCESS_TOKEN…')
        def work():
            rep={'app_version':'2.20.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'resolve_exact_guest_login_response_token_field_and_PREF_KEY_ACCESS_TOKEN_writer_locally',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known_from_v218':{'base_url':'https://wr.watchhealth.com.cn/app-halfwit/','guest_endpoint':'app-user/touristLogin','activation_endpoint':'app-device/activationDevice','check_for_update_endpoint':'app-device/checkForUpdate','token_markers':['PREF_KEY_ACCESS_TOKEN','access-token','accessToken','access_token']},
                 'raw_token_pref_xrefs':[],'symbolized_methods':[],'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'guest_login_requests':0,'activation_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex_seen':0,'methods_checked_raw':0,'raw_pref_xrefs':0,'target_class_methods':0,'symbolized':0}
            def inspect(label,b):
                stats['dex_seen']+=1
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                exact,err=v199.AppV199._exact_code_map(b,types)
                if err:rep.setdefault('exact_map_errors',[]).append({'dex':label,'error':err})
                try:key_idx=next(i for i,s in enumerate(strings) if s==KEY)
                except StopIteration:key_idx=None
                candidates=[];seen=set()
                for m in methods:
                    ex=exact.get(m.get('idx')) or {};code=ex.get('code_off');acc=ex.get('access_flags',0)
                    if not code:continue
                    stats['methods_checked_raw']+=1
                    hit=key_idx is not None and v208.AppV208._code_refs_string(b,code,key_idx)
                    cls=m.get('class') or ''
                    target=any(p.lower() in cls.lower() for p in TARGET_CLASS_PARTS)
                    if hit:
                        rep['raw_token_pref_xrefs'].append({'dex':label,'class':cls,'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'code_off':code})
                        stats['raw_pref_xrefs']+=1
                    if target:stats['target_class_methods']+=1
                    if (hit or target) and m.get('idx') not in seen:
                        seen.add(m.get('idx'));candidates.append((m,code,acc,hit,target))
                self._progress(f'V2.20 · {label.split("!")[-1]} · pref_xrefs={stats["raw_pref_xrefs"]} · candidates={len(candidates)}')
                for m,code,acc,hit,target in candidates:
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc)
                        sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except Exception as ex2:
                        rep.setdefault('symbolic_errors',[]).append({'class':m.get('class'),'method':m.get('name'),'error':repr(ex2)});continue
                    events=[]
                    for inv in sym.get('invokes') or []:
                        t=inv.get('target') or {};cls=t.get('class') or '';mn=t.get('method')
                        if any(x.lower() in cls.lower() for x in ('UserManager','PrefUtil','Welcome','UserInfo','Login','BaseApi','JsonUtils')) or mn in ('getAccess_token','getAccessToken','getToken','a','b','c','d','e','h'):
                            events.append({'unit':inv.get('unit'),'class':cls,'method':mn,'args':[self._simple(a) for a in (inv.get('args') or [])],'arg_regs':inv.get('arg_regs')})
                    row={'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'hit_pref_key':hit,'target_class':target,'incoming_registers':pmap,'events':events,'trace':(sym.get('trace') or [])[:2600]}
                    rep['symbolized_methods'].append(row);stats['symbolized']+=1
            def apk(name,data):
                with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                    dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                    for i,n in enumerate(dexes,1):
                        self._progress(f'V2.20 · DEX {i}/{len(dexes)} · {n}');inspect(name+'!'+n,z.read(n))
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
            writers=[];getters=[]
            for r in rep['symbolized_methods']:
                txt=json.dumps({'events':r.get('events'),'trace':r.get('trace')},ensure_ascii=False)
                if 'PREF_KEY_ACCESS_TOKEN' in txt or r.get('hit_pref_key'):writers.append({'class':r['class'],'method':r['method'],'proto':r['proto'],'events':r['events']})
                if 'getAccess_token' in txt or 'getAccessToken' in txt:getters.append({'class':r['class'],'method':r['method'],'proto':r['proto'],'events':r['events']})
            rep['scan_stats']=stats
            rep['resolved']={'pref_access_token_xrefs_found':len(rep['raw_token_pref_xrefs']),'candidate_writers':writers[:20],'access_token_getter_contexts':getters[:20],
                'network_gate':'NO_NETWORK_IN_THIS_VERSION','next':'If the guest response getter and PREF_KEY_ACCESS_TOKEN writer are unambiguous, next version can attempt one touristLogin request and log only HTTP status plus token presence/length/fingerprint, never the raw token.','write_gate':'NO_DEVICE_WRITES_IN_THIS_VERSION'}
            rep['summary']={'pref_xrefs':len(rep['raw_token_pref_xrefs']),'symbolized':stats['symbolized'],'writer_contexts':len(writers),'getter_contexts':len(getters)}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v220');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-token-response-v220.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V2.20 · falló: '+repr(err));return
            self.report={'utrawatch_token_response_v220':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep.get('summary') or {}
            self.status.set(f"V2.20 LISTO · pref_xrefs={s.get('pref_xrefs',0)} · writers={s.get('writer_contexts',0)} · getters={s.get('getter_contexts',0)} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV220(root);root.mainloop()
