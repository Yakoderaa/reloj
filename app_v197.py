import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v196 as v196
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='1.97.0'
BASEAPI='Lcom/wtwd/cocousa/api/BaseApi;'
TARGET_METHOD='L'
TARGET_ENDPOINT='app-device/activationDevice'

class AppV197(v196.AppV196):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.97')
        self._clean_v197();self._install_v197();self._restore_location_button()
        self.status.set('V1.97 lista · resuelve el contrato exacto de activationDevice. Sin red ni OTA.')

    def _clean_v197(self):
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

    def _install_v197(self):
        top=self.root.winfo_children()[0]
        self.v197_button=ttk.Button(top,text='RESOLVER BODY ACTIVATION',command=self.resolve_activation_contract)
        sib=top.winfo_children()
        try:self.v197_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v197_button.place(x=8,y=8)

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
            return {'source':'call','class':c.get('class'),'method':c.get('method'),'args':[AppV197._simple(v) for v in (x.get('args') or [])]}
        return {'source':k or 'expr','raw':x}

    def resolve_activation_contract(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V1.97 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.97 · resolviendo body y fuentes de activationDevice…')
        def work():
            rep={'app_version':'1.97.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'resolve_exact_activationDevice_request_fields_value_sources_and_call_order_without_network_or_ota',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known_state':{'guest_session_ok':True,'userBindDevice_ok':True,'checkForUpdate_server_code':4001},
                 'endpoint':TARGET_ENDPOINT,'baseapi_method':TARGET_METHOD,'call_sites':[],'field_classes':{},'scan_stats':{},
                 'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex':0,'methods_symbolic':0,'activation_call_sites':0}
            def inspect(label,b):
                stats['dex']+=1
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                em={mid:(code,kind,acc) for _,mid,code,kind,acc in enc}
                target_idxs={m.get('idx') for m in methods if m.get('class')==BASEAPI and m.get('name')==TARGET_METHOD}
                candidates=[m for m in methods if str(m.get('class') or '').startswith('Lcom/wtwd/cocousa/') and any(k in (str(m.get('class'))+' '+str(m.get('name'))).lower() for k in ('device','watch','bluetooth','scan','connect','home','model','presenter','manager'))]
                self._progress(f'V1.97 · {label} · {len(candidates)} métodos candidatos…')
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
                        if t.get('class')==BASEAPI and (t.get('idx') in target_idxs or t.get('method')==TARGET_METHOD):target_calls.append(inv)
                    if not target_calls:continue
                    stats['activation_call_sites']+=1
                    puts=[]
                    for inv in sym.get('invokes',[]):
                        t=inv.get('target') or {};args=inv.get('args') or []
                        if t.get('class') in ('Ljava/util/HashMap;','Ljava/util/Map;') and t.get('method')=='put' and len(args)>=3:
                            puts.append({'unit':inv.get('unit'),'key':self._simple(args[-2]),'value':self._simple(args[-1]),'raw_args':args})
                    row={'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'incoming_registers':pmap,
                         'activation_calls':target_calls,'hashmap_puts':puts,'invokes':sym.get('invokes',[])[:320],
                         'field_reads':sym.get('critical_field_reads',[])[:120],'field_writes':sym.get('critical_field_writes',[])[:120],
                         'returns':sym.get('returns',[])[:80]}
                    rep['call_sites'].append(row)
                    for p in puts:
                        v=p.get('value')
                        if isinstance(v,dict) and v.get('source')=='field':
                            rep['field_classes'].setdefault(v.get('class') or '?',[]).append({'key':p.get('key'),'field':v.get('name'),'type':v.get('type')})
                    if pos and pos%100==0:self._progress(f'V1.97 · {label} · {pos}/{len(candidates)}…')
            def apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                        for i,n in enumerate(dexes,1):
                            self._progress(f'V1.97 · DEX {i}/{len(dexes)} · {n}')
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
            keys={}
            ordered=[]
            for row in rep['call_sites']:
                for p in row.get('hashmap_puts',[]):
                    k=p.get('key')
                    if isinstance(k,str):
                        keys[k]=p.get('value')
                        ordered.append({'key':k,'value_source':p.get('value'),'class':row.get('class'),'method':row.get('method')})
            rep['scan_stats']=stats
            rep['resolved']={'activation_body_keys':sorted(keys.keys()),'activation_value_sources':keys,'ordered_puts':ordered,
                             'activation_call_sites':stats['activation_call_sites'],
                             'ready_for_exact_activation_request':bool(keys and stats['activation_call_sites']),
                             'next':'Map any remaining getter/field sources to the real selected watch values before one explicit activation request; keep firmware and OTA disabled.',
                             'write_gate':'KEEP_OTA_DISABLED_UNTIL_OFFICIAL_FIRMWARE_FILE_VALIDATION_SUCCEEDS'}
            rep['summary']={'call_sites':len(rep['call_sites']),'activation_call_sites':stats['activation_call_sites'],'body_keys':len(keys),'methods_symbolic':stats['methods_symbolic']}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v197');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-activation-contract-v197.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.97 · falló: '+repr(err));return
            self.report={'utrawatch_activation_contract_v197':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            r=rep.get('resolved') or {}
            self.status.set(f"V1.97 LISTO · activation call-sites={r.get('activation_call_sites',0)} · claves={len(r.get('activation_body_keys',[]))} · red/OTA=0 · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV197(root);root.mainloop()
