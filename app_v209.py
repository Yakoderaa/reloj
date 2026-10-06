import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v208 as v208
import app_v183 as v183
import app_v199 as v199
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='2.09.0'
BASEAPI='Lcom/wtwd/cocousa/api/BaseApi;'
UDI='Lcom/wtwd/cocousa/entity/user/UserDeviceInfo;'
DI='Lcom/wtwd/cocousa/entity/device/DeviceInfo;'
APP='Lcom/wtwd/cocousa/ui/module/application/Application;'
DM1='Lcom/wtwd/cocousa/ui/module/main/device/DeviceModel$1;'
HEALTH='Lcom/wtwd/cocousa/ui/module/main/health/HealthModel;'
GF='Lcom/wtwd/cocousa/entity/GaoFengLocationInfo;'
ACT_METHOD='L'

class AppV209(v208.AppV208):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V2.09')
        self._clean_v209();self._install_v209();self._restore_location_button()
        self.status.set('V2.09 lista · mapea WATCH_ID real y los 5 valores de activationDevice. Sin red ni OTA.')

    def _clean_v209(self):
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

    def _install_v209(self):
        top=self.root.winfo_children()[0]
        self.v209_button=ttk.Button(top,text='CERRAR WATCHID REAL + ACTIVACIÓN',command=self.resolve_values)
        sib=top.winfo_children()
        try:self.v209_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v209_button.place(x=8,y=8)

    @staticmethod
    def _ret_field(sym):
        for tr in reversed(sym.get('trace') or []):
            if tr.get('kind')=='return':
                v=tr.get('value')
                if isinstance(v,dict) and v.get('kind')=='field':
                    f=v.get('field') or {}
                    return {'class':f.get('class'),'name':f.get('name'),'type':f.get('type')}
        return None

    def resolve_values(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V2.09 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V2.09 · cerrando getters y contrato exacto de activación…')
        def work():
            rep={'app_version':'2.09.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'resolve_exact_watchId_value_origin_and_activationDevice_field_sources_with_targeted_local_analysis_only',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known_from_v208':{'watchid_xrefs':5,'writer_from_ble':'Application.h -> String.valueOf(DeviceInfo.b()) -> PREF_KEY_WATCH_ID','writer_from_account':'DeviceModel$1.c -> UserDeviceInfo.e() -> PREF_KEY_WATCH_ID','activation_body_keys':['area','lat','lng','macAddress','watchId']},
                 'user_device_getters':[],'device_info_getters':[],'writer_methods':[],'gaofeng_getters':[],'health_l':[],'activation_api_annotations':[],
                 'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex_seen':0,'target_methods_symbolized':0}
            def inspect(label,b):
                stats['dex_seen']+=1
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                exact,err=v199.AppV199._exact_code_map(b,types)
                if err:rep.setdefault('exact_map_errors',[]).append({'dex':label,'error':err})
                ann=v183.AppV183._retrofit_annotations(b,strings,types,fields,methods,BASEAPI,ACT_METHOD)
                if ann.get('method_annotations') or ann.get('parameter_annotations'):
                    rep['activation_api_annotations'].append({'dex':label,'method':ACT_METHOD,'annotation_directory':ann,'http_annotations':v183.AppV183._find_http_annotations(ann.get('method_annotations',[]))})
                targets=[]
                for m in methods:
                    cls,name=m.get('class'),m.get('name')
                    if cls in (UDI,DI,GF) or (cls==APP and name in ('h','i')) or (cls==DM1 and name=='c') or (cls==HEALTH and name=='l'):
                        ex=exact.get(m.get('idx')) or {};code=ex.get('code_off');acc=ex.get('access_flags',0)
                        if code:targets.append((m,code,acc))
                self._progress(f'V2.09 · {label.split("!")[-1]} · targets={len(targets)}')
                for m,code,acc in targets:
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc);sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except Exception as ex2:
                        rep.setdefault('symbolic_errors',[]).append({'class':m.get('class'),'method':m.get('name'),'error':repr(ex2)});continue
                    stats['target_methods_symbolized']+=1
                    row={'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'incoming_registers':pmap,'return_field':self._ret_field(sym),'invokes':sym.get('invokes') or [],'trace':(sym.get('trace') or [])[:1800]}
                    cls=m.get('class')
                    if cls==UDI:rep['user_device_getters'].append(row)
                    elif cls==DI:rep['device_info_getters'].append(row)
                    elif cls==GF:rep['gaofeng_getters'].append(row)
                    elif cls in (APP,DM1):rep['writer_methods'].append(row)
                    elif cls==HEALTH:rep['health_l'].append(row)
            def apk(name,data):
                with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                    dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                    for i,n in enumerate(dexes,1):
                        self._progress(f'V2.09 · DEX {i}/{len(dexes)} · {n}')
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
            u_map={x.get('method'):x.get('return_field') for x in rep['user_device_getters'] if x.get('return_field')}
            d_map={x.get('method'):x.get('return_field') for x in rep['device_info_getters'] if x.get('return_field')}
            g_map={x.get('method'):x.get('return_field') for x in rep['gaofeng_getters'] if x.get('return_field')}
            endpoints=[];params=[]
            for a in rep['activation_api_annotations']:
                for h in a.get('http_annotations') or []:
                    endpoints.extend([v for v in (h.get('annotation',{}).get('elements',{}) or {}).values() if isinstance(v,str)])
                for p in a.get('annotation_directory',{}).get('parameter_annotations',[]):params.extend(p.get('parameters') or [])
            rep['scan_stats']=stats
            rep['resolved']={'user_device_getter_fields':u_map,'device_info_getter_fields':d_map,'gaofeng_getter_fields':g_map,
                'ble_watchid_source':'DeviceInfo.b()','account_watchid_source':'UserDeviceInfo.e()',
                'activation_endpoint_candidates':list(dict.fromkeys(endpoints)),'activation_parameter_annotations':params,
                'activation_body_keys':['area','lat','lng','macAddress','watchId'],
                'next':'Use these exact getter mappings to build one explicit activationDevice request with the selected watch and location values; keep firmware download and OTA disabled until server metadata succeeds.',
                'write_gate':'NO_DEVICE_WRITES_IN_THIS_VERSION'}
            rep['summary']={'user_device_getters':len(rep['user_device_getters']),'device_info_getters':len(rep['device_info_getters']),'gaofeng_getters':len(rep['gaofeng_getters']),'writer_methods':len(rep['writer_methods']),'health_l':len(rep['health_l']),'activation_annotations':len(rep['activation_api_annotations'])}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v209');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-activation-values-v209.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V2.09 · falló: '+repr(err));return
            self.report={'utrawatch_activation_values_v209':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep.get('summary') or {}
            self.status.set(f"V2.09 LISTO · UDI={s.get('user_device_getters',0)} · DeviceInfo={s.get('device_info_getters',0)} · annotations={s.get('activation_annotations',0)} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV209(root);root.mainloop()
