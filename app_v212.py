import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v211 as v211
import app_v199 as v199
import app_v179 as v179
import app_v180 as v180
import app_v210 as v210
import app_v145 as v145

base.APP_VERSION='2.12.0'
HEALTH='Lcom/wtwd/cocousa/ui/module/main/health/HealthModel;'
PRES='Lcom/wtwd/cocousa/ui/module/main/health/HealthPresenter;'
DM='Lcom/wtwd/cocousa/manager/DeviceManager;'

class AppV212(v211.AppV211):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V2.12')
        self._clean_v212();self._install_v212();self._restore_location_button()
        self.status.set('V2.12 lista · traza AREA, MAC y WATCH_ID hasta sus productores reales. Sin red ni OTA.')

    def _clean_v212(self):
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

    def _install_v212(self):
        top=self.root.winfo_children()[0]
        self.v212_button=ttk.Button(top,text='TRAZAR VALORES ACTIVATION',command=self.resolve_sources)
        sib=top.winfo_children()
        try:self.v212_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v212_button.place(x=8,y=8)

    def resolve_sources(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V2.12 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V2.12 · trazando productores exactos de AREA, MAC y WATCH_ID…')
        def work():
            rep={'app_version':'2.12.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'resolve_runtime_producers_for_activation_area_mac_watchid_and_call_chain_locally',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known':{'endpoint':'app-device/activationDevice','health_model_method':'h','presenter_callsite':'HealthPresenter.S0','watchId_ble_semantics':'String.valueOf(DeviceInfo.customerId)'},
                 'device_manager_methods':[],'health_presenter_S0':[],'health_presenter_S0_callers':[],
                 'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex_seen':0,'symbolized':0,'s0_callers':0}
            def inspect(label,b):
                stats['dex_seen']+=1
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                exact,err=v199.AppV199._exact_code_map(b,types)
                if err:rep.setdefault('exact_map_errors',[]).append({'dex':label,'error':err})
                s0_idxs={m.get('idx') for m in methods if m.get('class')==PRES and m.get('name')=='S0'}
                targets=[]
                for m in methods:
                    ex=exact.get(m.get('idx')) or {};code=ex.get('code_off');acc=ex.get('access_flags',0)
                    if not code:continue
                    if m.get('class')==DM and m.get('name') in ('d','j'):
                        targets.append((m,code,acc,'dm'))
                    elif m.get('class')==PRES and m.get('name')=='S0':
                        targets.append((m,code,acc,'s0'))
                    else:
                        try:sym0=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        except:continue
                        if any((i.get('target') or {}).get('idx') in s0_idxs for i in (sym0.get('invokes') or [])):
                            targets.append((m,code,acc,'caller'))
                for m,code,acc,kind in targets:
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc);sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except Exception as ex2:
                        rep.setdefault('symbolic_errors',[]).append({'class':m.get('class'),'method':m.get('name'),'error':repr(ex2)});continue
                    stats['symbolized']+=1
                    row={'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'incoming_registers':pmap,
                         'invokes':(sym.get('invokes') or [])[:1400],'trace':(sym.get('trace') or [])[:2200]}
                    # Capture field reads/returns so DeviceManager.d/j can be mapped exactly.
                    field_reads=[];returns=[]
                    for tr in sym.get('trace') or []:
                        if tr.get('kind') in ('iget','sget'):
                            field_reads.append({'unit':tr.get('unit'),'kind':tr.get('kind'),'dst':tr.get('dst'),'field':tr.get('field'),'object':tr.get('object') or tr.get('obj')})
                        if tr.get('kind')=='return':returns.append(tr)
                    row['field_reads']=field_reads;row['returns']=returns
                    if kind=='dm':rep['device_manager_methods'].append(row)
                    elif kind=='s0':
                        hcalls=[]
                        for inv in sym.get('invokes') or []:
                            t=inv.get('target') or {}
                            if t.get('class')==HEALTH and t.get('method')=='h':
                                hcalls.append({'unit':inv.get('unit'),'arg_regs':inv.get('arg_regs'),'args':[v210.AppV210._simple(a) for a in (inv.get('args') or [])],'raw_args':inv.get('args') or []})
                        row['health_h_calls']=hcalls;rep['health_presenter_S0'].append(row)
                    else:
                        calls=[]
                        for inv in sym.get('invokes') or []:
                            t=inv.get('target') or {}
                            if t.get('idx') in s0_idxs:
                                calls.append({'unit':inv.get('unit'),'arg_regs':inv.get('arg_regs'),'args':[v210.AppV210._simple(a) for a in (inv.get('args') or [])],'raw_args':inv.get('args') or []})
                        if calls:
                            row['S0_calls']=calls;rep['health_presenter_S0_callers'].append(row);stats['s0_callers']+=len(calls)
                self._progress(f'V2.12 · {label.split("!")[-1]} · S0 callers={stats["s0_callers"]}')
            def apk(name,data):
                with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                    dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                    for i,n in enumerate(dexes,1):
                        self._progress(f'V2.12 · DEX {i}/{len(dexes)} · {n}')
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
            dm={}
            for row in rep['device_manager_methods']:
                reads=row.get('field_reads') or []
                dm[row.get('method')]={'field_reads':reads,'return_type':(row.get('proto') or {}).get('return')}
            s0calls=[]
            for row in rep['health_presenter_S0']:
                s0calls.extend(row.get('health_h_calls') or [])
            callers=[]
            for row in rep['health_presenter_S0_callers']:
                callers.append({'class':row.get('class'),'method':row.get('method'),'calls':row.get('S0_calls') or []})
            rep['scan_stats']=stats
            rep['resolved']={
                'activation_endpoint':'app-device/activationDevice',
                'health_h_signature':['area','lat','lng','macAddress','watchId'],
                'device_manager_getters':dm,
                'health_h_calls_from_S0':s0calls,
                'S0_callers':callers,
                'next':'Use resolved getter fields and S0 caller arguments to bind exact runtime activation values; keep network and device writes disabled until those values are unambiguous.',
                'write_gate':'NO_DEVICE_WRITES_IN_THIS_VERSION'}
            rep['summary']={'device_manager_methods':len(rep['device_manager_methods']),'S0_methods':len(rep['health_presenter_S0']),'S0_callers':len(rep['health_presenter_S0_callers']),'S0_call_count':stats['s0_callers']}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v212');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-activation-sources-v212.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V2.12 · falló: '+repr(err));return
            self.report={'utrawatch_activation_sources_v212':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep.get('summary') or {}
            self.status.set(f"V2.12 LISTO · DM={s.get('device_manager_methods',0)} · S0 callers={s.get('S0_call_count',0)} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV212(root);root.mainloop()
