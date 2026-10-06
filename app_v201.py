import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v200 as v200
import app_v199 as v199
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='2.01.0'
HEALTH='Lcom/wtwd/cocousa/ui/module/main/health/HealthModel;'
HEALTH_PRESENTER='Lcom/wtwd/cocousa/ui/module/main/health/HealthPresenter;'

class AppV201(v200.AppV200):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V2.01')
        self._clean_v201();self._install_v201();self._restore_location_button()
        self.status.set('V2.01 lista · elimina colisiones de method_idx y corrige el mapa semántico de WEATHER/lat/lng/MAC/watchId.')

    def _clean_v201(self):
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

    def _install_v201(self):
        top=self.root.winfo_children()[0]
        self.v201_button=ttk.Button(top,text='CORREGIR CALLER REAL Y LAT/LNG',command=self.resolve_real_caller)
        sib=top.winfo_children()
        try:self.v201_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v201_button.place(x=8,y=8)

    @staticmethod
    def _is_health_h(inv):
        t=inv.get('target') or {}
        return t.get('class')==HEALTH and t.get('method')=='h'

    @staticmethod
    def _is_presenter_s0(inv):
        t=inv.get('target') or {}
        return t.get('class')==HEALTH_PRESENTER and t.get('method')=='S0'

    @staticmethod
    def _semantic_args(inv):
        # invoke-virtual/range uses register slots, so wide D/J parameters occupy two entries.
        # For HealthModel.h(String,double,double,String,String): receiver + 1 + 2 + 2 + 1 + 1 = 8 slots.
        a=list(inv.get('args') or [])
        r=list(inv.get('arg_regs') or [])
        def slot(i):
            return {'reg':r[i] if i < len(r) else None,'value':a[i] if i < len(a) else None}
        return {
            'receiver':slot(0),
            'area':slot(1),
            'lat':{'low':slot(2),'wide_high':slot(3)},
            'lng':{'low':slot(4),'wide_high':slot(5)},
            'macAddress':slot(6),
            'watchId':slot(7),
        }

    def resolve_real_caller(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V2.01 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V2.01 · filtrando callers por clase+método y reconstruyendo slots wide…')
        def work():
            rep={'app_version':'2.01.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'remove_cross_dex_method_index_collisions_and_resolve_exact_HealthModel_h_semantic_arguments_and_HealthPresenter_S0_callers_locally',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known_from_v200':{'false_positive_cause':'method_idx 16728 is not globally unique across DEX files','real_target':'HealthModel.h(String,double,double,String,String)'},
                 'real_health_h_callers':[],'presenter_s0_callers':[],'semantic_maps':[],
                 'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex':0,'exact_methods':0,'health_h_callers':0,'s0_callers':0,'third_party_idx_collisions_ignored':0}
            def inspect(label,b):
                stats['dex']+=1
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                exact,err=v199.AppV199._exact_code_map(b,types)
                if err:rep.setdefault('exact_map_errors',[]).append({'dex':label,'error':err})
                for m in methods:
                    ex=exact.get(m.get('idx'))
                    if not ex or not ex.get('code_off'):continue
                    stats['exact_methods']+=1
                    code=ex['code_off'];acc=ex.get('access_flags',0)
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc)
                        sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except:continue
                    invs=sym.get('invokes') or []
                    # Count same numeric index collisions only as diagnostic; never treat them as the target.
                    for inv in invs:
                        t=inv.get('target') or {}
                        if t.get('idx')==16728 and not self._is_health_h(inv):stats['third_party_idx_collisions_ignored']+=1
                    hh=[x for x in invs if self._is_health_h(x)]
                    if hh:
                        stats['health_h_callers']+=1
                        row={'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'code_off':code,'incoming_registers':pmap,'target_calls':hh,'trace':sym.get('trace',[])[:1700]}
                        rep['real_health_h_callers'].append(row)
                        for inv in hh:
                            rep['semantic_maps'].append({'caller_class':m.get('class'),'caller_method':m.get('name'),'unit':inv.get('unit'),'raw_arg_regs':inv.get('arg_regs'),'semantic_slots':self._semantic_args(inv)})
                    s0=[x for x in invs if self._is_presenter_s0(x)]
                    if s0:
                        stats['s0_callers']+=1
                        rep['presenter_s0_callers'].append({'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'code_off':code,'incoming_registers':pmap,'target_calls':s0,'trace':sym.get('trace',[])[:1400]})
            def apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                        for i,n in enumerate(dexes,1):
                            self._progress(f'V2.01 · DEX {i}/{len(dexes)} · {n}')
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
            # Compact interpretation from the exact app caller. The raw evidence is retained above.
            compact=[]
            for x in rep['semantic_maps']:
                s=x.get('semantic_slots') or {}
                compact.append({'caller':x.get('caller_class')+'.'+str(x.get('caller_method')),
                    'area':(s.get('area') or {}).get('value'),
                    'lat':((s.get('lat') or {}).get('low') or {}).get('value'),
                    'lng':((s.get('lng') or {}).get('low') or {}).get('value'),
                    'macAddress':(s.get('macAddress') or {}).get('value'),
                    'watchId':(s.get('watchId') or {}).get('value')})
            rep['scan_stats']=stats
            rep['resolved']={'real_target_filter':'class == HealthModel AND method == h','semantic_register_widths':{'receiver':1,'area':1,'lat':2,'lng':2,'macAddress':1,'watchId':1},
                'compact_real_maps':compact,'s0_callers_found':len(rep['presenter_s0_callers']),
                'ready_for_lat_lng_origin_trace':bool(rep['presenter_s0_callers']),
                'next':'Trace the exact HealthPresenter.S0 callers to identify where its latitude and longitude strings originate; keep all device writes disabled.',
                'write_gate':'NO_DEVICE_WRITES_IN_THIS_VERSION'}
            rep['summary']={'real_health_h_callers':len(rep['real_health_h_callers']),'semantic_maps':len(rep['semantic_maps']),'s0_callers':len(rep['presenter_s0_callers']),'third_party_idx_collisions_ignored':stats['third_party_idx_collisions_ignored']}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v201');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-real-caller-map-v201.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V2.01 · falló: '+repr(err));return
            self.report={'utrawatch_real_caller_map_v201':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep.get('summary') or {}
            self.status.set(f"V2.01 LISTO · caller real={s.get('real_health_h_callers',0)} · S0 callers={s.get('s0_callers',0)} · colisiones ignoradas={s.get('third_party_idx_collisions_ignored',0)} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV201(root);root.mainloop()
