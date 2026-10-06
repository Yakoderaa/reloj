import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v204 as v204
import app_v199 as v199
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='2.05.0'
HEALTH='Lcom/wtwd/cocousa/ui/module/main/health/HealthModel;'
PRES='Lcom/wtwd/cocousa/ui/module/main/health/HealthPresenter;'

class AppV205(v204.AppV204):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V2.05')
        self._clean_v205();self._install_v205();self._restore_location_button()
        self.status.set('V2.05 lista · rastrea Location → lat/lng → WEATHER sin buscar callers globales.')

    def _clean_v205(self):
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

    def _install_v205(self):
        top=self.root.winfo_children()[0]
        self.v205_button=ttk.Button(top,text='RASTREAR LOCATION → LAT/LNG',command=self.resolve_location_flow)
        sib=top.winfo_children()
        try:self.v205_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v205_button.place(x=8,y=8)

    def resolve_location_flow(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V2.05 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V2.05 · leyendo sólo HealthModel.j(Location), S0 y métodos vecinos…')
        def work():
            rep={'app_version':'2.05.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'resolve_location_getLatitude_getLongitude_origin_for_activation_without_global_caller_scan',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known':{'S0_direct_callers_found_v204':0,'HealthModel_h_signature':'h(String,double,double,String,String)','HealthPresenter_S0_signature':'S0(String,String,String,WeatherBean)'},
                 'target_methods':[],'location_calls':[],'weather_calls':[],'device_manager_calls':[],
                 'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex_seen':0,'target_methods':0,'location_getters':0,'weather_related':0}
            wanted={(HEALTH,'j'),(HEALTH,'h'),(HEALTH,'k'),(HEALTH,'n'),(PRES,'S0')}
            def inspect(label,b):
                stats['dex_seen']+=1
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                targets=[m for m in methods if (m.get('class'),m.get('name')) in wanted]
                if not targets:return
                exact,err=v199.AppV199._exact_code_map(b,types)
                if err:rep.setdefault('exact_map_errors',[]).append({'dex':label,'error':err})
                for m in targets:
                    ex=exact.get(m.get('idx')) or {};code=ex.get('code_off');acc=ex.get('access_flags',0)
                    if not code:continue
                    self._progress(f'V2.05 · {m.get("class","").split("/")[-1]}{m.get("name")}')
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc)
                        sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except Exception as ex2:
                        rep.setdefault('symbolic_errors',[]).append({'class':m.get('class'),'method':m.get('name'),'error':repr(ex2)});continue
                    invs=sym.get('invokes') or []
                    row={'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'code_off':code,'incoming_registers':pmap,'invokes':invs,'trace':sym.get('trace',[])[:3200]}
                    rep['target_methods'].append(row);stats['target_methods']+=1
                    for inv in invs:
                        t=inv.get('target') or {};cl=t.get('class');mn=t.get('method')
                        if cl=='Landroid/location/Location;' and mn in ('getLatitude','getLongitude'):
                            rep['location_calls'].append({'owner_class':m.get('class'),'owner_method':m.get('name'),'getter':mn,'unit':inv.get('unit'),'args':inv.get('args'),'arg_regs':inv.get('arg_regs')});stats['location_getters']+=1
                        if ('Weather' in str(cl)) or mn in ('S0','h','n'):
                            rep['weather_calls'].append({'owner_class':m.get('class'),'owner_method':m.get('name'),'target':t,'unit':inv.get('unit'),'args':inv.get('args'),'arg_regs':inv.get('arg_regs')});stats['weather_related']+=1
                        if cl=='Lcom/wtwd/cocousa/manager/DeviceManager;' and mn in ('d','j','g'):
                            rep['device_manager_calls'].append({'owner_class':m.get('class'),'owner_method':m.get('name'),'target':t,'unit':inv.get('unit'),'args':inv.get('args')})
            def apk(name,data):
                with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                    dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                    for i,n in enumerate(dexes,1):
                        self._progress(f'V2.05 · DEX {i}/{len(dexes)} · {n}')
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
            getters={x.get('getter') for x in rep['location_calls']}
            rep['scan_stats']=stats
            rep['resolved']={'getLatitude_found':'getLatitude' in getters,'getLongitude_found':'getLongitude' in getters,
                'location_flow_closed':('getLatitude' in getters and 'getLongitude' in getters),
                'mac_source':'DeviceManager.d()','watchId_source':'DeviceManager.j()',
                'next':'If both Location getters are confirmed in HealthModel.j, use the selected watch MAC/watchId plus explicit location values for a single activation request; keep OTA disabled.',
                'write_gate':'NO_DEVICE_WRITES_IN_THIS_VERSION'}
            rep['summary']={'target_methods':len(rep['target_methods']),'location_calls':len(rep['location_calls']),'weather_calls':len(rep['weather_calls']),'device_manager_calls':len(rep['device_manager_calls'])}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v205');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-location-flow-v205.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V2.05 · falló: '+repr(err));return
            self.report={'utrawatch_location_flow_v205':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            r=rep.get('resolved') or {}
            self.status.set(f"V2.05 LISTO · lat={r.get('getLatitude_found')} · lng={r.get('getLongitude_found')} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV205(root);root.mainloop()
