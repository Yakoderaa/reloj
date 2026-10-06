import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v213 as v213
import app_v199 as v199
import app_v179 as v179
import app_v180 as v180
import app_v210 as v210
import app_v145 as v145

base.APP_VERSION='2.14.0'
PRES='Lcom/wtwd/cocousa/ui/module/main/health/HealthPresenter;'
HEALTH='Lcom/wtwd/cocousa/ui/module/main/health/HealthModel;'
DM='Lcom/wtwd/cocousa/manager/DeviceManager;'
APP='Lcom/wtwd/cocousa/ui/module/application/Application;'
DEV1='Lcom/wtwd/cocousa/ui/module/main/device/DeviceModel$1;'
PREF='Lcom/wtwd/cocousa/utils/PrefUtil;'
TARGETS={(PRES,'S0'),(DM,'a'),(DM,'l'),(APP,'h'),(DEV1,'c')}

class AppV214(v213.AppV213):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V2.14')
        self._clean_v214();self._install_v214();self._restore_location_button()
        self.status.set('V2.14 lista · une AREA/LAT/LNG/MAC/WATCH_ID y precedencia de writers. Sin red ni OTA.')

    def _clean_v214(self):
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

    def _install_v214(self):
        top=self.root.winfo_children()[0]
        self.v214_button=ttk.Button(top,text='CERRAR ACTIVATION 5/5',command=self.resolve_binding)
        sib=top.winfo_children()
        try:self.v214_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v214_button.place(x=8,y=8)

    @staticmethod
    def _simple(a):
        try:return v210.AppV210._simple(a)
        except:return a

    def resolve_binding(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V2.14 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V2.14 · trazando sólo 5 métodos exactos…')
        def work():
            rep={'app_version':'2.14.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'bind_exact_activation_5_fields_and_watchid_writer_precedence_locally',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known_from_v213':{'area_slot_candidate':'WEATHER','mac_pref':'PREF_KEY_DEVICE_MAC','watchId_pref':'PREF_KEY_WATCH_ID','ble_watchId_source':'String.valueOf(DeviceInfo.b())','account_watchId_source':'UserDeviceInfo.e()'},
                 'target_methods':[],'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex_seen':0,'target_methods':0,'symbolized':0}
            def inspect(label,b):
                stats['dex_seen']+=1
                if not any(x in b for x in (b'HealthPresenter',b'PREF_KEY_WATCH_ID',b'PREF_KEY_DEVICE_MAC')):return
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                exact,err=v199.AppV199._exact_code_map(b,types)
                if err:rep.setdefault('exact_map_errors',[]).append({'dex':label,'error':err})
                for m in methods:
                    if (m.get('class'),m.get('name')) not in TARGETS:continue
                    ex=exact.get(m.get('idx')) or {};code=ex.get('code_off');acc=ex.get('access_flags',0)
                    if not code:continue
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc);sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except Exception as e:
                        rep.setdefault('symbolic_errors',[]).append({'class':m.get('class'),'method':m.get('name'),'error':repr(e)});continue
                    stats['symbolized']+=1;stats['target_methods']+=1
                    row={'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'incoming_registers':pmap,
                         'invokes':[],'trace':(sym.get('trace') or [])[:3000]}
                    for inv in sym.get('invokes') or []:
                        t=inv.get('target') or {}
                        interesting=(t.get('class') in (HEALTH,PREF,DM) or 'DeviceInfo;' in str(t.get('class')) or 'UserDeviceInfo;' in str(t.get('class')) or t.get('method') in ('valueOf','getAddress'))
                        if interesting:
                            row['invokes'].append({'unit':inv.get('unit'),'target':t,'arg_regs':inv.get('arg_regs'),'args':[self._simple(a) for a in (inv.get('args') or [])],'raw_args':inv.get('args') or []})
                    rep['target_methods'].append(row)
                self._progress(f'V2.14 · {label.split("!")[-1]} · targets={stats["target_methods"]}')
            def apk(name,data):
                with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                    dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                    for i,n in enumerate(dexes,1):
                        self._progress(f'V2.14 · DEX {i}/{len(dexes)} · {n}')
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

            s0=next((r for r in rep['target_methods'] if r['class']==PRES and r['method']=='S0'),None)
            hcall=None
            if s0:
                for inv in s0['invokes']:
                    t=inv.get('target') or {}
                    if t.get('class')==HEALTH and t.get('method')=='h':hcall=inv;break
            slot_binding={}
            if hcall:
                a=hcall.get('args') or []
                # invoke-virtual/range signature: receiver + String + double(2 regs) + double(2 regs) + String + String.
                if len(a)>=8:
                    slot_binding={'receiver':a[0],'area':a[1],'lat_low':a[2],'lat_high':a[3],'lng_low':a[4],'lng_high':a[5],'macAddress':a[6],'watchId':a[7],
                                  'semantic':['receiver','area','lat(low)','lat(high)','lng(low)','lng(high)','macAddress','watchId']}
            writers=[]
            for r in rep['target_methods']:
                for inv in r['invokes']:
                    t=inv.get('target') or {}
                    if t.get('class')==PREF and t.get('method')=='h':
                        args=inv.get('args') or []
                        if len(args)>=3 and args[1] in ('PREF_KEY_WATCH_ID','PREF_KEY_DEVICE_MAC'):
                            writers.append({'class':r['class'],'method':r['method'],'unit':inv.get('unit'),'key':args[1],'value':args[2],'incoming_registers':r.get('incoming_registers')})
            rep['scan_stats']=stats
            rep['resolved']={'activation_endpoint':'app-device/activationDevice','activation_signature':['area','lat','lng','macAddress','watchId'],
                'health_h_slot_binding':slot_binding,
                'expected_slot_semantics':{'area':'WEATHER','lat':'Double.parseDouble(S0 param1)','lng':'Double.parseDouble(S0 param2)','macAddress':'DeviceManager.d() -> PREF_KEY_DEVICE_MAC','watchId':'DeviceManager.j() -> PREF_KEY_WATCH_ID'},
                'watchId_writer_semantics':{'ble':'Application.h writes String.valueOf(DeviceInfo.b()) (DeviceInfo.b previously mapped to customerId)','account':'DeviceModel$1.c writes UserDeviceInfo.e() (watchId field)','clear':'DeviceManager.l writes empty string'},
                'preference_writers':writers,
                'next':'Confirm writer ordering/guards and exact DeviceManager.a MAC parameter. No network request until watchId source precedence is unambiguous.',
                'write_gate':'NO_DEVICE_WRITES_IN_THIS_VERSION'}
            rep['summary']={'target_methods':len(rep['target_methods']),'writers':len(writers),'slot_binding_found':bool(slot_binding)}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v214');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-activation-binding-v214.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V2.14 · falló: '+repr(err));return
            self.report={'utrawatch_activation_binding_v214':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep.get('summary') or {}
            self.status.set(f"V2.14 LISTO · targets={s.get('target_methods',0)} · writers={s.get('writers',0)} · slots={s.get('slot_binding_found',False)} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV214(root);root.mainloop()
