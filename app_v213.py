import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v212 as v212
import app_v199 as v199
import app_v179 as v179
import app_v180 as v180
import app_v210 as v210
import app_v145 as v145

base.APP_VERSION='2.13.0'
PRES='Lcom/wtwd/cocousa/ui/module/main/health/HealthPresenter;'
HEALTH='Lcom/wtwd/cocousa/ui/module/main/health/HealthModel;'
PREF='Lcom/wtwd/cocousa/utils/PrefUtil;'
KEYS=('PREF_KEY_DEVICE_MAC','PREF_KEY_WATCH_ID')

class AppV213(v212.AppV212):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V2.13')
        self._clean_v213();self._install_v213();self._restore_location_button()
        self.status.set('V2.13 lista · cierra slots reales de HealthModel.h y writers de MAC/WATCH_ID. Sin red ni OTA.')

    def _clean_v213(self):
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

    def _install_v213(self):
        top=self.root.winfo_children()[0]
        self.v213_button=ttk.Button(top,text='CERRAR SLOTS + PREFS',command=self.resolve_slots)
        sib=top.winfo_children()
        try:self.v213_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v213_button.place(x=8,y=8)

    @staticmethod
    def _compact_trace(sym,start=88,end=118):
        out=[]
        for tr in sym.get('trace') or []:
            u=tr.get('unit')
            if isinstance(u,int) and start<=u<=end:
                out.append(tr)
        return out

    def resolve_slots(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V2.13 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V2.13 · reconstruyendo slots + writers de preferencias…')
        def work():
            rep={'app_version':'2.13.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'reconstruct_exact_invoke_range_slots_for_HealthModel_h_and_find_pref_writers_locally',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known_from_v212':{'mac_getter':'PrefUtil.d(context,PREF_KEY_DEVICE_MAC)','watchId_getter':'PrefUtil.d(context,PREF_KEY_WATCH_ID)','S0_callers':0},
                 's0_slot_traces':[],'pref_key_methods':[],
                 'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex_seen':0,'s0':0,'pref_candidates':0,'symbolized':0}
            def inspect(label,b):
                stats['dex_seen']+=1
                # Fast raw prefilter: only classes containing our target literals/classes merit full analysis.
                if not any(k.encode() in b for k in KEYS) and b'HealthPresenter' not in b:
                    return
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                exact,err=v199.AppV199._exact_code_map(b,types)
                if err:rep.setdefault('exact_map_errors',[]).append({'dex':label,'error':err})
                key_string_idxs={i for i,s in enumerate(strings) if s in KEYS}
                for m in methods:
                    ex=exact.get(m.get('idx')) or {};code=ex.get('code_off');acc=ex.get('access_flags',0)
                    if not code:continue
                    is_s0=(m.get('class')==PRES and m.get('name')=='S0')
                    # Symbolize app methods only in the DEX that contains target preference strings; retain only actual literal refs.
                    if not is_s0 and not str(m.get('class') or '').startswith('Lcom/wtwd/cocousa/'):
                        continue
                    try:sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                    except:continue
                    stats['symbolized']+=1
                    if is_s0:
                        pmap=v180.AppV180._param_map(b,code,m,acc);sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                        calls=[]
                        for inv in sym.get('invokes') or []:
                            t=inv.get('target') or {}
                            if t.get('class')==HEALTH and t.get('method')=='h':
                                calls.append({'unit':inv.get('unit'),'arg_regs':inv.get('arg_regs'),'raw_args':inv.get('args') or [],'simple_args':[v210.AppV210._simple(a) for a in (inv.get('args') or [])]})
                        rep['s0_slot_traces'].append({'dex':label,'method_idx':m.get('idx'),'proto':m.get('proto'),'incoming_registers':pmap,'health_h_calls':calls,'trace_88_118':self._compact_trace(sym)})
                        stats['s0']+=1
                    # literal string reference detection from symbolic trace, then capture full compact method summary.
                    seen=set()
                    for tr in sym.get('trace') or []:
                        if tr.get('kind')=='string' and tr.get('value') in KEYS:seen.add(tr.get('value'))
                    if seen:
                        invs=[]
                        for inv in sym.get('invokes') or []:
                            t=inv.get('target') or {}
                            if t.get('class')==PREF or 'PrefUtil' in str(t.get('class') or ''):
                                invs.append({'unit':inv.get('unit'),'target':t,'arg_regs':inv.get('arg_regs'),'args':[v210.AppV210._simple(a) for a in (inv.get('args') or [])],'raw_args':inv.get('args') or []})
                        rep['pref_key_methods'].append({'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'keys':sorted(seen),'pref_invokes':invs,'trace':(sym.get('trace') or [])[:800]})
                        stats['pref_candidates']+=1
                self._progress(f'V2.13 · {label.split("!")[-1]} · prefs={stats["pref_candidates"]}')
            def apk(name,data):
                with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                    dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                    for i,n in enumerate(dexes,1):
                        self._progress(f'V2.13 · DEX {i}/{len(dexes)} · {n}')
                        inspect(name+'!'+n,z.read(n))
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
            writers=[]
            for row in rep['pref_key_methods']:
                for inv in row.get('pref_invokes') or []:
                    t=inv.get('target') or {}
                    # PrefUtil.h is the known String writer; keep all methods too for evidence.
                    if t.get('method')=='h':writers.append({'key_context':row.get('keys'),'class':row.get('class'),'method':row.get('method'),'invoke':inv})
            rep['scan_stats']=stats
            rep['resolved']={'mac_pref_key':'PREF_KEY_DEVICE_MAC','watchId_pref_key':'PREF_KEY_WATCH_ID','pref_string_writers':writers,
                'slot_trace_count':len(rep['s0_slot_traces']),
                'next':'Use the exact live-register trace around invoke-range and preference writers to bind area/MAC/watchId runtime values. Keep network and device writes disabled.',
                'write_gate':'NO_DEVICE_WRITES_IN_THIS_VERSION'}
            rep['summary']={'s0_slot_traces':len(rep['s0_slot_traces']),'pref_key_methods':len(rep['pref_key_methods']),'pref_string_writers':len(writers)}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v213');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-slots-prefs-v213.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V2.13 · falló: '+repr(err));return
            self.report={'utrawatch_slots_prefs_v213':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep.get('summary') or {}
            self.status.set(f"V2.13 LISTO · slots={s.get('s0_slot_traces',0)} · pref methods={s.get('pref_key_methods',0)} · writers={s.get('pref_string_writers',0)} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV213(root);root.mainloop()
