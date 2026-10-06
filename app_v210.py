import io,json,os,zipfile,struct
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v209 as v209
import app_v183 as v183
import app_v199 as v199
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='2.10.0'
BASEAPI='Lcom/wtwd/cocousa/api/BaseApi;'
APP='Lcom/wtwd/cocousa/ui/module/application/Application;'
KEY='PREF_KEY_WATCH_ID'
BODY_KEYS=('area','lat','lng','macAddress','watchId')
TARGET_ENDPOINT='app-device/activationDevice'

class AppV210(v209.AppV209):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V2.10')
        self._clean_v210();self._install_v210();self._restore_location_button()
        self.status.set('V2.10 lista · corrige WATCH_ID=customerId y cierra el body exacto de activationDevice. Sin red ni OTA.')

    def _clean_v210(self):
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

    def _install_v210(self):
        top=self.root.winfo_children()[0]
        self.v210_button=ttk.Button(top,text='CERRAR BODY ACTIVATION EXACTO',command=self.resolve_activation_body)
        sib=top.winfo_children()
        try:self.v210_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v210_button.place(x=8,y=8)

    @staticmethod
    def _simple(x):
        if not isinstance(x,dict):return x
        k=x.get('kind')
        if k in ('string','const'):return x.get('value')
        if k=='param':return {'source':'param','index':x.get('index'),'type':x.get('type')}
        if k in ('field','static_field'):
            f=x.get('field') or {}
            return {'source':'field','class':f.get('class'),'name':f.get('name'),'type':f.get('type')}
        if k=='call_result':
            c=x.get('call') or {}
            return {'source':'call','class':c.get('class'),'method':c.get('method'),'args':[AppV210._simple(v) for v in (x.get('args') or [])]}
        if k=='expr':
            return {'source':'expr','op':x.get('op'),'left':AppV210._simple(x.get('left')),'right':AppV210._simple(x.get('right'))}
        return {'source':k or 'expr','raw':x}

    @staticmethod
    def _code_refs_any_string(b,code_off,string_idxs):
        hits=set()
        if not code_off or not string_idxs:return hits
        try:
            size=struct.unpack_from('<I',b,code_off+12)[0]
            data=b[code_off+16:code_off+16+size*2];units=len(data)//2
            for i in range(units):
                u=struct.unpack_from('<H',data,i*2)[0];op=u&0xff
                if op==0x1a and i+1<units:
                    idx=struct.unpack_from('<H',data,(i+1)*2)[0]
                    if idx in string_idxs:hits.add(idx)
                elif op==0x1b and i+2<units:
                    idx=struct.unpack_from('<I',data,(i+1)*2)[0]
                    if idx in string_idxs:hits.add(idx)
        except:pass
        return hits

    def resolve_activation_body(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V2.10 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V2.10 · cerrando endpoint, body y origen exacto de WATCH_ID…')
        def work():
            rep={'app_version':'2.10.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'resolve_exact_activationDevice_retrofit_method_body_value_sources_and_correct_watchId_semantics_locally',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'v209_correction':{'DeviceInfo.b_field':'customerId','UserDeviceInfo.e_field':'watchId','ble_pref_watch_id_semantics':'PREF_KEY_WATCH_ID is populated from String.valueOf(DeviceInfo.customerId) in Application.h'},
                 'baseapi_activation_methods':[],'activation_body_producers':[],'watchid_writer':[],'scan_stats':{},
                 'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex_seen':0,'methods_checked_raw':0,'body_candidates':0,'symbolized':0}
            def inspect(label,b):
                stats['dex_seen']+=1
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                exact,err=v199.AppV199._exact_code_map(b,types)
                if err:rep.setdefault('exact_map_errors',[]).append({'dex':label,'error':err})
                # Resolve every BaseApi method annotation, then keep only activationDevice.
                for m in methods:
                    if m.get('class')!=BASEAPI:continue
                    ann=v183.AppV183._retrofit_annotations(b,strings,types,fields,methods,BASEAPI,m.get('name'))
                    http=v183.AppV183._find_http_annotations(ann.get('method_annotations',[]))
                    txt=json.dumps({'http':http,'params':ann.get('parameter_annotations',[])},ensure_ascii=False)
                    if TARGET_ENDPOINT.lower() in txt.lower() or 'activationdevice' in txt.lower():
                        rep['baseapi_activation_methods'].append({'dex':label,'method':m,'annotation_directory':ann,'http_annotations':http})
                wanted_values=set(BODY_KEYS+(KEY,TARGET_ENDPOINT))
                idx_to_value={i:s for i,s in enumerate(strings) if s in wanted_values}
                value_to_idx={s:i for i,s in idx_to_value.items()}
                idxs=set(idx_to_value)
                target_api_idxs={x.get('method',{}).get('idx') for x in rep['baseapi_activation_methods'] if x.get('dex')==label}
                for m in methods:
                    ex=exact.get(m.get('idx')) or {};code=ex.get('code_off');acc=ex.get('access_flags',0)
                    if not code:continue
                    stats['methods_checked_raw']+=1
                    hits=self._code_refs_any_string(b,code,idxs)
                    vals=[idx_to_value[i] for i in hits if i in idx_to_value]
                    is_writer=(m.get('class')==APP and m.get('name')=='h')
                    likely_body=len(set(vals)&set(BODY_KEYS))>=2
                    if not (is_writer or likely_body):continue
                    stats['body_candidates']+=1
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc);sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except Exception as ex2:
                        rep.setdefault('symbolic_errors',[]).append({'class':m.get('class'),'method':m.get('name'),'error':repr(ex2)});continue
                    stats['symbolized']+=1
                    puts=[];api_calls=[];watchid_pref_writes=[]
                    for inv in sym.get('invokes') or []:
                        t=inv.get('target') or {};args=inv.get('args') or []
                        if t.get('class') in ('Ljava/util/HashMap;','Ljava/util/Map;') and t.get('method')=='put' and len(args)>=3:
                            key=self._simple(args[-2]);val=self._simple(args[-1])
                            if key in BODY_KEYS:puts.append({'unit':inv.get('unit'),'key':key,'value_source':val,'raw_args':args})
                        if t.get('class')==BASEAPI and (t.get('idx') in target_api_idxs or target_api_idxs==set()):
                            api_calls.append({'unit':inv.get('unit'),'target':t,'args':[self._simple(a) for a in args]})
                        if t.get('class')=='Lcom/wtwd/cocousa/utils/PrefUtil;' and t.get('method')=='h':
                            simp=[self._simple(a) for a in args]
                            if KEY in simp:watchid_pref_writes.append({'unit':inv.get('unit'),'args':simp,'raw_args':args})
                    row={'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'raw_string_hits':vals,'incoming_registers':pmap,'hashmap_puts':puts,'activation_api_calls':api_calls,'watchid_pref_writes':watchid_pref_writes,'invokes':(sym.get('invokes') or [])[:500]}
                    if is_writer:rep['watchid_writer'].append(row)
                    if puts or api_calls:rep['activation_body_producers'].append(row)
                self._progress(f'V2.10 · {label.split("!")[-1]} · body={len(rep["activation_body_producers"])}')
            def apk(name,data):
                with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                    dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                    for i,n in enumerate(dexes,1):
                        self._progress(f'V2.10 · DEX {i}/{len(dexes)} · {n}')
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
            body={}
            for row in rep['activation_body_producers']:
                for p in row.get('hashmap_puts') or []:body[p.get('key')]=p.get('value_source')
            endpoints=[];params=[];api_methods=[]
            for row in rep['baseapi_activation_methods']:
                api_methods.append((row.get('method') or {}).get('name'))
                for h in row.get('http_annotations') or []:
                    for v in (h.get('annotation',{}).get('elements',{}) or {}).values():
                        if isinstance(v,str):endpoints.append(v)
                for p in row.get('annotation_directory',{}).get('parameter_annotations',[]):params.extend(p.get('parameters') or [])
            rep['scan_stats']=stats
            rep['resolved']={'corrected_ble_watchid_source':'String.valueOf(DeviceInfo.b()) = String.valueOf(DeviceInfo.customerId)',
                'account_watchid_source':'UserDeviceInfo.e() = UserDeviceInfo.watchId',
                'activation_baseapi_methods':list(dict.fromkeys([x for x in api_methods if x])),
                'activation_endpoints':list(dict.fromkeys(endpoints)) or [TARGET_ENDPOINT],
                'activation_parameter_annotations':params,
                'activation_body_value_sources':body,'activation_body_keys_found':sorted(body.keys()),
                'body_complete':all(k in body for k in BODY_KEYS),
                'next':'If all five body values and the endpoint are proven, use the selected watch plus explicit location values for one user-initiated activation request; still do not download firmware or write OTA in this version.',
                'write_gate':'NO_DEVICE_WRITES_IN_THIS_VERSION'}
            rep['summary']={'activation_api_methods':len(rep['baseapi_activation_methods']),'body_producers':len(rep['activation_body_producers']),'body_keys_found':len(body),'watchid_writer_methods':len(rep['watchid_writer']),'body_complete':rep['resolved']['body_complete']}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v210');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-activation-body-v210.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V2.10 · falló: '+repr(err));return
            self.report={'utrawatch_activation_body_v210':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep.get('summary') or {}
            self.status.set(f"V2.10 LISTO · API={s.get('activation_api_methods',0)} · body={s.get('body_keys_found',0)}/5 · completo={s.get('body_complete',False)} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV210(root);root.mainloop()
