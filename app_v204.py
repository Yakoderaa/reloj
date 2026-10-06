import io,json,os,zipfile,struct
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v203 as v203
import app_v199 as v199
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='2.04.0'
HEALTH_PRESENTER='Lcom/wtwd/cocousa/ui/module/main/health/HealthPresenter;'
APP_PREFIX='Lcom/wtwd/cocousa/'

class AppV204(v203.AppV203):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V2.04')
        self._clean_v204();self._install_v204();self._restore_location_button()
        self.status.set('V2.04 lista · busca callers de HealthPresenter.S0 por bytecode directo; simboliza sólo coincidencias.')

    def _clean_v204(self):
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
                    else:
                        walk(c)
                except:pass
        walk(self.root)

    def _install_v204(self):
        top=self.root.winfo_children()[0]
        self.v204_button=ttk.Button(top,text='BUSCAR CALLER EXACTO S0',command=self.resolve_s0_exact)
        sib=top.winfo_children()
        try:self.v204_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v204_button.place(x=8,y=8)

    @staticmethod
    def _is_s0(inv):
        t=inv.get('target') or {}
        return t.get('class')==HEALTH_PRESENTER and t.get('method')=='S0'

    @staticmethod
    def _raw_invokes_method(b,code_off,target_idx):
        try:
            if not code_off or code_off+16>len(b):return False
            insns_size=struct.unpack_from('<I',b,code_off+12)[0]
            start=code_off+16;end=min(len(b),start+insns_size*2)
            if end-start<4:return False
            units=struct.unpack_from('<'+'H'*((end-start)//2),b,start)
            invoke_ops=set(range(0x6e,0x73))|set(range(0x74,0x79))
            for i in range(len(units)-1):
                if (units[i]&0xff) in invoke_ops and units[i+1]==target_idx:
                    return True
        except Exception:
            return False
        return False

    def resolve_s0_exact(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V2.04 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V2.04 · buscando S0 sin simbolizar miles de métodos…')
        def work():
            rep={'app_version':'2.04.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'find_exact_HealthPresenter_S0_callers_with_raw_dex_invoke_prefilter_then_symbolize_only_matches',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known_from_v203':{'HealthPresenter.S0_signature':'S0(String,String,String,WeatherBean)','health_h_caller':'HealthPresenter.S0','v203_s0_callers':0},
                 'dex_results':[],'raw_candidates':[],'confirmed_s0_callers':[],
                 'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex_seen':0,'dex_with_s0_ref':0,'encoded_methods_scanned':0,'raw_candidates':0,'confirmed_callers':0}

            def inspect(label,b):
                stats['dex_seen']+=1
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:
                    rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                s0refs=[m for m in methods if m.get('class')==HEALTH_PRESENTER and m.get('name')=='S0']
                if not s0refs:return
                stats['dex_with_s0_ref']+=1
                exact,err=v199.AppV199._exact_code_map(b,types)
                if err:rep.setdefault('exact_map_errors',[]).append({'dex':label,'error':err})
                for s0 in s0refs:
                    target_idx=s0.get('idx')
                    dexrow={'dex':label,'s0_method_idx':target_idx,'s0_proto':s0.get('proto'),'raw_candidates':0,'confirmed':0}
                    encoded=[m for m in methods if (exact.get(m.get('idx')) or {}).get('code_off')]
                    total=len(encoded)
                    for pos,m in enumerate(encoded,1):
                        if pos==1 or pos%1000==0 or pos==total:
                            self._progress(f'V2.04 · scan S0 {pos}/{total} · candidatos={stats["raw_candidates"]}')
                        ex=exact.get(m.get('idx')) or {};code=ex.get('code_off')
                        if not self._raw_invokes_method(b,code,target_idx):continue
                        stats['raw_candidates']+=1;dexrow['raw_candidates']+=1
                        cand={'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'code_off':code}
                        rep['raw_candidates'].append(cand)
                        try:
                            acc=ex.get('access_flags',0)
                            sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                            pmap=v180.AppV180._param_map(b,code,m,acc)
                            sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                        except Exception as ex2:
                            cand['symbolic_error']=repr(ex2);continue
                        calls=[x for x in (sym.get('invokes') or []) if self._is_s0(x)]
                        if not calls:continue
                        stats['confirmed_callers']+=1;dexrow['confirmed']+=1
                        rep['confirmed_s0_callers'].append({'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'code_off':code,'incoming_registers':pmap,'target_calls':calls,'trace':sym.get('trace',[])[:2600]})
                    stats['encoded_methods_scanned']+=total
                    rep['dex_results'].append(dexrow)

            def apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                        for i,n in enumerate(dexes,1):
                            self._progress(f'V2.04 · DEX {i}/{len(dexes)} · {n}')
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
            rep['resolved']={'confirmed_s0_callers_found':len(rep['confirmed_s0_callers']),
                'ready_for_value_origin_trace':bool(rep['confirmed_s0_callers']),
                'next':'Use only confirmed S0 callers to resolve the three String inputs and WeatherBean source; do not broaden scanning again.',
                'write_gate':'NO_DEVICE_WRITES_IN_THIS_VERSION'}
            rep['summary']={'dex_with_s0_ref':stats['dex_with_s0_ref'],'encoded_methods_scanned':stats['encoded_methods_scanned'],'raw_candidates':stats['raw_candidates'],'confirmed_s0_callers':stats['confirmed_callers']}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v204');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-s0-callers-v204.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V2.04 · falló: '+repr(err));return
            self.report={'utrawatch_s0_callers_v204':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep.get('summary') or {}
            self.status.set(f"V2.04 LISTO · candidatos={s.get('raw_candidates',0)} · S0 confirmados={s.get('confirmed_s0_callers',0)} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV204(root);root.mainloop()
