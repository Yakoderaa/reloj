import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v192 as v192
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='1.93.0'
BASEAPI='Lcom/wtwd/cocousa/api/BaseApi;'
TARGET_METHODS={'L':'app-device/activationDevice','m':'app-device/userBindDevice'}

class AppV193(v192.AppV192):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.93')
        self._clean_v193();self._install_v193();self._restore_location_button()
        self.status.set('V1.93 lista · cierra el body exacto de activationDevice/userBindDevice. Sin red ni OTA.')

    def _clean_v193(self):
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

    def _install_v193(self):
        top=self.root.winfo_children()[0]
        self.v193_button=ttk.Button(top,text='CERRAR BODY DE ALTA',command=self.resolve_registration_body)
        sib=top.winfo_children()
        try:self.v193_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v193_button.place(x=8,y=8)

    @staticmethod
    def _simple_value(x):
        if not isinstance(x,dict):return x
        k=x.get('kind')
        if k in ('string','const'):return x.get('value')
        if k=='param':return {'source':'param','index':x.get('index'),'type':x.get('type')}
        if k in ('field','static_field'):
            f=x.get('field') or {}
            return {'source':'field','class':f.get('class'),'name':f.get('name'),'type':f.get('type')}
        if k=='call_result':
            c=x.get('call') or {}
            return {'source':'call','class':c.get('class'),'method':c.get('method'),'args':[AppV193._simple_value(v) for v in (x.get('args') or [])]}
        return {'source':k or 'expr','raw':x}

    def resolve_registration_body(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V1.93 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.93 · cerrando body exacto de alta/vinculación…')
        def work():
            rep={'app_version':'1.93.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'resolve_exact_request_body_fields_and_sources_for_activationDevice_and_userBindDevice_before_any_network_retry',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known_server_block':{'code':4001,'message':'请先在web端平台入库'},
                 'target_endpoints':TARGET_METHODS,'call_sites':[],'resolved_bodies':{},'scan_stats':{},
                 'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex':0,'methods_symbolic':0,'target_call_sites':0}
            def inspect(label,b):
                stats['dex']+=1
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                em={mid:(code,kind,acc) for _,mid,code,kind,acc in enc}
                target_idxs={m.get('idx'):m.get('name') for m in methods if m.get('class')==BASEAPI and m.get('name') in TARGET_METHODS}
                candidates=[m for m in methods if str(m.get('class') or '').startswith('Lcom/wtwd/cocousa/') and any(k in (str(m.get('class'))+' '+str(m.get('name'))).lower() for k in ('device','bluetooth','watch','manager'))]
                self._progress(f'V1.93 · {label} · {len(candidates)} métodos candidatos…')
                for pos,m in enumerate(candidates):
                    code,kind,acc=em.get(m.get('idx'),(0,None,None))
                    if not code:continue
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc);sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except:continue
                    stats['methods_symbolic']+=1
                    target_calls=[]
                    for inv in sym.get('invokes',[]):
                        t=inv.get('target') or {}
                        if t.get('class')==BASEAPI and t.get('idx') in target_idxs:
                            target_calls.append(inv)
                    if not target_calls:continue
                    stats['target_call_sites']+=1
                    puts=[]
                    for inv in sym.get('invokes',[]):
                        t=inv.get('target') or {};args=inv.get('args') or []
                        if t.get('class')=='Ljava/util/HashMap;' and t.get('method')=='put' and len(args)>=3:
                            puts.append({'unit':inv.get('unit'),'key':self._simple_value(args[-2]),'value':self._simple_value(args[-1]),'raw_args':args})
                    row={'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'incoming_registers':pmap,
                         'target_calls':target_calls,'hashmap_puts':puts,'invokes':sym.get('invokes',[])[:260],'returns':sym.get('returns',[])[:60]}
                    rep['call_sites'].append(row)
                    for tc in target_calls:
                        endpoint=TARGET_METHODS.get((tc.get('target') or {}).get('method'))
                        if endpoint:
                            d=rep['resolved_bodies'].setdefault(endpoint,{'call_sites':0,'keys':{},'all_puts':[]})
                            d['call_sites']+=1;d['all_puts'].extend(puts)
                            for p in puts:
                                if isinstance(p.get('key'),str):d['keys'][p['key']]=p.get('value')
                    if pos and pos%100==0:self._progress(f'V1.93 · {label} · {pos}/{len(candidates)}…')
            def apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                        for i,n in enumerate(dexes,1):
                            self._progress(f'V1.93 · DEX {i}/{len(dexes)} · {n}')
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
            for ep,d in rep['resolved_bodies'].items():
                d['body_keys']=sorted(d.get('keys',{}).keys())
                d['confidence']='high' if d['body_keys'] and d.get('call_sites',0)>0 else 'incomplete'
            activation=rep['resolved_bodies'].get('app-device/activationDevice',{})
            bind=rep['resolved_bodies'].get('app-device/userBindDevice',{})
            rep['scan_stats']=stats
            rep['resolved']={'activation_body_keys':activation.get('body_keys',[]),'bind_body_keys':bind.get('body_keys',[]),
                             'activation_call_sites':activation.get('call_sites',0),'bind_call_sites':bind.get('call_sites',0),
                             'preferred_next_endpoint':'app-device/activationDevice' if activation.get('body_keys') else ('app-device/userBindDevice' if bind.get('body_keys') else None),
                             'next':'Use only a body whose keys and value sources are fully resolved for one official registration request, then retry checkForUpdate; keep firmware/OTA writes disabled.',
                             'write_gate':'KEEP_OTA_DISABLED_UNTIL_OFFICIAL_FIRMWARE_METADATA_AND_FILE_VALIDATION_SUCCEED'}
            rep['summary']={'call_sites':len(rep['call_sites']),'methods_symbolic':stats['methods_symbolic'],'target_call_sites':stats['target_call_sites'],'resolved_endpoints':len(rep['resolved_bodies'])}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v193');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-registration-body-v193.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.93 · falló: '+repr(err));return
            self.report={'utrawatch_registration_body_v193':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            r=rep.get('resolved') or {}
            self.status.set(f"V1.93 LISTO · activation={len(r.get('activation_body_keys',[]))} claves · bind={len(r.get('bind_body_keys',[]))} claves · red/OTA=0 · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV193(root);root.mainloop()
