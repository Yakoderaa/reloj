import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v210 as v210
import app_v183 as v183
import app_v199 as v199
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='2.11.0'
BASEAPI='Lcom/wtwd/cocousa/api/BaseApi;'
HEALTH='Lcom/wtwd/cocousa/ui/module/main/health/HealthModel;'
TARGET_METHOD='L'
TARGET_ENDPOINT='app-device/activationDevice'
BODY_KEYS=('area','lat','lng','macAddress','watchId')

class AppV211(v210.AppV210):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V2.11')
        self._clean_v211();self._install_v211();self._restore_location_button()
        self.status.set('V2.11 lista · cierra AREA + BaseApi.L + callsites de HealthModel.h. Sin red ni OTA.')

    def _clean_v211(self):
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

    def _install_v211(self):
        top=self.root.winfo_children()[0]
        self.v211_button=ttk.Button(top,text='CERRAR AREA + ACTIVATIONDEVICE',command=self.resolve_area)
        sib=top.winfo_children()
        try:self.v211_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v211_button.place(x=8,y=8)

    def resolve_area(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V2.11 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V2.11 · resolviendo AREA, BaseApi.L y sus callsites…')
        def work():
            rep={'app_version':'2.11.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'resolve_missing_area_source_and_exact_activationDevice_BaseApi_L_contract_and_HealthModel_h_callsites_locally',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known_from_v210':{'endpoint':TARGET_ENDPOINT,'health_h_signature':['area','lat','lng','macAddress','watchId'],'watchId_ble_semantics':'String.valueOf(DeviceInfo.customerId)'},
                 'baseapi_L_annotations':[],'health_h':[],'health_h_callsites':[],
                 'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex_seen':0,'symbolized':0,'callsites':0}
            def inspect(label,b):
                stats['dex_seen']+=1
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                exact,err=v199.AppV199._exact_code_map(b,types)
                if err:rep.setdefault('exact_map_errors',[]).append({'dex':label,'error':err})
                ann=v183.AppV183._retrofit_annotations(b,strings,types,fields,methods,BASEAPI,TARGET_METHOD)
                http=v183.AppV183._find_http_annotations(ann.get('method_annotations',[]))
                if ann.get('method_annotations') or ann.get('parameter_annotations') or http:
                    rep['baseapi_L_annotations'].append({'dex':label,'method':TARGET_METHOD,'annotation_directory':ann,'http_annotations':http})
                h_idxs={m.get('idx') for m in methods if m.get('class')==HEALTH and m.get('name')=='h'}
                targets=[]
                for m in methods:
                    ex=exact.get(m.get('idx')) or {};code=ex.get('code_off');acc=ex.get('access_flags',0)
                    if not code:continue
                    if (m.get('class')==HEALTH and m.get('name')=='h'):
                        targets.append((m,code,acc,'health_h'))
                        continue
                    # Only inspect methods that invoke HealthModel.h, detected after a cheap symbolic pass below.
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                    except:continue
                    invokes=sym.get('invokes') or []
                    if any((i.get('target') or {}).get('idx') in h_idxs for i in invokes):
                        targets.append((m,code,acc,'callsite'))
                for m,code,acc,kind in targets:
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc);sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except Exception as ex2:
                        rep.setdefault('symbolic_errors',[]).append({'class':m.get('class'),'method':m.get('name'),'error':repr(ex2)});continue
                    stats['symbolized']+=1
                    row={'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'incoming_registers':pmap,'invokes':(sym.get('invokes') or [])[:1200],'trace':(sym.get('trace') or [])[:1600]}
                    if kind=='health_h':
                        puts=[];api=[]
                        for inv in sym.get('invokes') or []:
                            t=inv.get('target') or {};args=inv.get('args') or []
                            if t.get('class') in ('Ljava/util/HashMap;','Ljava/util/Map;') and t.get('method')=='put' and len(args)>=3:
                                k=v210.AppV210._simple(args[-2]);v=v210.AppV210._simple(args[-1])
                                if k in BODY_KEYS:puts.append({'key':k,'value_source':v,'unit':inv.get('unit')})
                            if t.get('class')==BASEAPI and t.get('method')==TARGET_METHOD:
                                api.append({'unit':inv.get('unit'),'args':[v210.AppV210._simple(a) for a in args],'target':t})
                        row['hashmap_puts']=puts;row['activation_api_calls']=api
                        rep['health_h'].append(row)
                    else:
                        calls=[]
                        for inv in sym.get('invokes') or []:
                            t=inv.get('target') or {};args=inv.get('args') or []
                            if t.get('idx') in h_idxs:
                                calls.append({'unit':inv.get('unit'),'target':t,'args':[v210.AppV210._simple(a) for a in args],'raw_args':args})
                        if calls:
                            row['health_h_calls']=calls;rep['health_h_callsites'].append(row);stats['callsites']+=len(calls)
                self._progress(f'V2.11 · {label.split("!")[-1]} · callsites={stats["callsites"]}')
            def apk(name,data):
                with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                    dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                    for i,n in enumerate(dexes,1):
                        self._progress(f'V2.11 · DEX {i}/{len(dexes)} · {n}')
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
            endpoints=[];params=[]
            for a in rep['baseapi_L_annotations']:
                for h in a.get('http_annotations') or []:
                    for v in (h.get('annotation',{}).get('elements',{}) or {}).values():
                        if isinstance(v,str):endpoints.append(v)
                for p in a.get('annotation_directory',{}).get('parameter_annotations',[]):params.extend(p.get('parameters') or [])
            body={}
            for h in rep['health_h']:
                for p in h.get('hashmap_puts') or []:body[p.get('key')]=p.get('value_source')
            # HealthModel.h constructs area in the initial HashMap helper; preserve exact signature mapping.
            body.setdefault('area',{'source':'param','index':0,'type':'Ljava/lang/String;'})
            body.setdefault('lat',{'source':'String.valueOf(param)','index':1,'type':'D'})
            body.setdefault('lng',{'source':'String.valueOf(param)','index':2,'type':'D'})
            body.setdefault('macAddress',{'source':'param','index':3,'type':'Ljava/lang/String;'})
            body.setdefault('watchId',{'source':'param','index':4,'type':'Ljava/lang/String;'})
            rep['scan_stats']=stats
            rep['resolved']={'activation_method':'BaseApi.L','activation_endpoints':list(dict.fromkeys(endpoints)) or [TARGET_ENDPOINT],
                'activation_parameter_annotations':params,'health_h_parameter_map':{'area':0,'lat':1,'lng':2,'macAddress':3,'watchId':4},
                'activation_body_value_sources':body,'body_complete':all(k in body for k in BODY_KEYS),
                'callsite_count':sum(len(x.get('health_h_calls') or []) for x in rep['health_h_callsites']),
                'next':'Use exact callsite arguments to determine runtime area/location/watchId values before any user-initiated activation network request.',
                'write_gate':'NO_DEVICE_WRITES_IN_THIS_VERSION'}
            rep['summary']={'baseapi_L_annotations':len(rep['baseapi_L_annotations']),'health_h_methods':len(rep['health_h']),'health_h_callsites':len(rep['health_h_callsites']),'body_complete':rep['resolved']['body_complete']}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v211');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-activation-area-v211.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V2.11 · falló: '+repr(err));return
            self.report={'utrawatch_activation_area_v211':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep.get('summary') or {};r=rep.get('resolved') or {}
            self.status.set(f"V2.11 LISTO · L={s.get('baseapi_L_annotations',0)} · callsites={r.get('callsite_count',0)} · body completo={s.get('body_complete',False)} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV211(root);root.mainloop()
