import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v201 as v201
import app_v199 as v199
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='2.02.0'
HEALTH='Lcom/wtwd/cocousa/ui/module/main/health/HealthModel;'
HEALTH_PRESENTER='Lcom/wtwd/cocousa/ui/module/main/health/HealthPresenter;'
APP_PREFIX='Lcom/wtwd/cocousa/'

class AppV202(v201.AppV201):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V2.02')
        self._clean_v202();self._install_v202();self._restore_location_button()
        self.status.set('V2.02 lista · escaneo dirigido: omite DEX de terceros y analiza sólo UtraWatch.')

    def _clean_v202(self):
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

    def _install_v202(self):
        top=self.root.winfo_children()[0]
        self.v202_button=ttk.Button(top,text='ESCANEO RÁPIDO CALLER REAL',command=self.resolve_fast)
        sib=top.winfo_children()
        try:self.v202_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v202_button.place(x=8,y=8)

    @staticmethod
    def _is_health_h(inv):
        t=inv.get('target') or {}
        return t.get('class')==HEALTH and t.get('method')=='h'

    @staticmethod
    def _is_presenter_s0(inv):
        t=inv.get('target') or {}
        return t.get('class')==HEALTH_PRESENTER and t.get('method')=='S0'

    def resolve_fast(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V2.02 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V2.02 · localizando primero el DEX real de UtraWatch…')
        def work():
            rep={'app_version':'2.02.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'avoid_full_cross_dex_symbolic_scan_and_trace_only_real_utrawatch_health_callers_locally',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'fix':{'v201_stall_cause':'symbolic analysis iterated every encoded method in third-party DEX files','strategy':'locate target DEX first, then analyze only com/wtwd/cocousa classes'},
                 'target_dexes':[],'skipped_dexes':[],'health_h_callers':[],'presenter_s0_callers':[],'semantic_maps':[],
                 'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex_seen':0,'dex_targeted':0,'dex_skipped':0,'methods_seen_target_dex':0,'app_methods_analyzed':0,'health_h_callers':0,'s0_callers':0}

            def inspect(label,b):
                stats['dex_seen']+=1
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:
                    rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                type_set=set(types or [])
                method_targets=[m for m in methods if (m.get('class') in (HEALTH,HEALTH_PRESENTER))]
                has_target=(HEALTH in type_set or HEALTH_PRESENTER in type_set or bool(method_targets))
                if not has_target:
                    stats['dex_skipped']+=1
                    rep['skipped_dexes'].append({'dex':label,'reason':'does_not_contain_HealthModel_or_HealthPresenter','methods':len(methods)})
                    self._progress(f'V2.02 · omitido {os.path.basename(label)} · DEX de terceros')
                    return
                stats['dex_targeted']+=1
                rep['target_dexes'].append({'dex':label,'methods':len(methods),'target_refs':len(method_targets)})
                exact,err=v199.AppV199._exact_code_map(b,types)
                if err:rep.setdefault('exact_map_errors',[]).append({'dex':label,'error':err})
                encoded=[m for m in methods if (exact.get(m.get('idx')) or {}).get('code_off')]
                stats['methods_seen_target_dex']+=len(encoded)
                app_encoded=[m for m in encoded if str(m.get('class') or '').startswith(APP_PREFIX)]
                total=len(app_encoded)
                for pos,m in enumerate(app_encoded,1):
                    if pos==1 or pos%100==0 or pos==total:
                        self._progress(f'V2.02 · UtraWatch {pos}/{total} · {m.get("class","").split("/")[-1]}')
                    ex=exact.get(m.get('idx')) or {};code=ex.get('code_off');acc=ex.get('access_flags',0)
                    if not code:continue
                    stats['app_methods_analyzed']+=1
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc)
                        sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except Exception:continue
                    invs=sym.get('invokes') or []
                    hh=[x for x in invs if self._is_health_h(x)]
                    if hh:
                        stats['health_h_callers']+=1
                        rep['health_h_callers'].append({'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'code_off':code,'incoming_registers':pmap,'target_calls':hh,'trace':sym.get('trace',[])[:1800]})
                        for inv in hh:
                            rep['semantic_maps'].append({'caller_class':m.get('class'),'caller_method':m.get('name'),'unit':inv.get('unit'),'raw_arg_regs':inv.get('arg_regs'),'raw_args':inv.get('args')})
                    s0=[x for x in invs if self._is_presenter_s0(x)]
                    if s0:
                        stats['s0_callers']+=1
                        rep['presenter_s0_callers'].append({'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'code_off':code,'incoming_registers':pmap,'target_calls':s0,'trace':sym.get('trace',[])[:1800]})

            def apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                        for i,n in enumerate(dexes,1):
                            self._progress(f'V2.02 · índice DEX {i}/{len(dexes)} · {n}')
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

            rep['scan_stats']=stats
            rep['resolved']={'stall_fixed':True,'target_dex_count':len(rep['target_dexes']),'third_party_dex_skipped':len(rep['skipped_dexes']),
                'health_h_callers_found':len(rep['health_h_callers']),'s0_callers_found':len(rep['presenter_s0_callers']),
                'ready_for_next_trace':bool(rep['health_h_callers']),
                'next':'Use only the exact UtraWatch caller evidence to finish latitude/longitude and DeviceManager value origins locally.',
                'write_gate':'NO_DEVICE_WRITES_IN_THIS_VERSION'}
            rep['summary']={'target_dexes':len(rep['target_dexes']),'skipped_dexes':len(rep['skipped_dexes']),'app_methods_analyzed':stats['app_methods_analyzed'],'health_h_callers':len(rep['health_h_callers']),'s0_callers':len(rep['presenter_s0_callers'])}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v202');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-fast-real-caller-v202.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V2.02 · falló: '+repr(err));return
            self.report={'utrawatch_fast_real_caller_v202':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep.get('summary') or {}
            self.status.set(f"V2.02 LISTO · DEX objetivo={s.get('target_dexes',0)} · omitidos={s.get('skipped_dexes',0)} · métodos app={s.get('app_methods_analyzed',0)} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV202(root);root.mainloop()
