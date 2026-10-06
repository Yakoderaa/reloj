import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v191 as v191
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='1.92.0'
BASEAPI='Lcom/wtwd/cocousa/api/BaseApi;'

class AppV192(v191.AppV191):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.92')
        self._clean_v192();self._install_v192();self._restore_location_button()
        self.status.set('V1.92 lista · busca el alta/registro del reloj previa a checkForUpdate. Sin red ni OTA.')

    def _clean_v192(self):
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

    def _install_v192(self):
        top=self.root.winfo_children()[0]
        self.v192_button=ttk.Button(top,text='RESOLVER ALTA DEL RELOJ',command=self.resolve_device_registration)
        sib=top.winfo_children()
        try:self.v192_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v192_button.place(x=8,y=8)

    @staticmethod
    def _candidate_text(s):
        q=str(s or '').lower()
        keys=('app-device/','device/','bind','binding','register','registration','adddevice','add-device','deviceadd','insert','warehouse','stock','storage','inventory','watchid','deviceid','device_id','mac','firmware','hardware')
        return any(k in q for k in keys)

    def resolve_device_registration(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V1.92 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.92 · buscando flujo de alta del reloj antes de checkForUpdate…')
        def work():
            rep={'app_version':'1.92.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'resolve_exact_utrawatch_device_registration_or_inventory_flow_required_before_checkForUpdate_without_network_or_ota',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'server_error_from_v191':{'code':4001,'message':'请先在web端平台入库','meaning':'device/watch must be registered or stocked in platform before firmware lookup'},
                 'baseapi_device_contracts':[],'candidate_strings':[],'call_sites':[],'scan_stats':{},
                 'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            seen_s=set();stats={'dex':0,'methods_total':0,'methods_symbolic':0,'candidate_methods':0}
            def inspect(label,b):
                stats['dex']+=1;self._progress(f'V1.92 · {label} · leyendo Retrofit y strings…')
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                for s in strings:
                    if self._candidate_text(s) and s not in seen_s:
                        seen_s.add(s);rep['candidate_strings'].append({'dex':label,'value':s})
                ann=self._retrofit_annotations(b,strings,types,fields,methods,BASEAPI,None)
                candidate_method_ids=set()
                for row in ann.get('method_annotations',[]):
                    m=row.get('method') or {}; anns=row.get('annotations') or []
                    text=json.dumps(anns,ensure_ascii=False).lower()
                    if self._candidate_text(text):
                        params=[]
                        for pr in ann.get('parameter_annotations',[]):
                            pm=pr.get('method') or {}
                            if pm.get('idx')==m.get('idx'):params=pr.get('parameters') or [];break
                        rep['baseapi_device_contracts'].append({'dex':label,'method':m,'annotations':anns,'parameters':params})
                        if m.get('idx') is not None:candidate_method_ids.add(m.get('idx'))
                em={mid:(code,kind,acc) for _,mid,code,kind,acc in enc};stats['methods_total']+=len(methods)
                targets=[]
                for m in methods:
                    cls=str(m.get('class') or '')
                    if not cls.startswith('Lcom/wtwd/cocousa/'):continue
                    q=(cls+' '+str(m.get('name') or '')).lower()
                    if any(k in q for k in ('device','bind','watch','hardware','firmware','main/device','manager')):targets.append(m)
                stats['candidate_methods']+=len(targets)
                self._progress(f'V1.92 · {label} · analizando {len(targets)} métodos relacionados…')
                for pos,m in enumerate(targets):
                    code,kind,acc=em.get(m.get('idx'),(0,None,None))
                    if not code:continue
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc);sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except:continue
                    stats['methods_symbolic']+=1
                    hits=[]
                    for inv in sym.get('invokes',[]):
                        t=inv.get('target') or {}
                        if t.get('class')==BASEAPI and (t.get('idx') in candidate_method_ids):hits.append(inv)
                    text=json.dumps(sym,ensure_ascii=False).lower()
                    if hits or ('app-device/' in text and any(k in text for k in ('bind','register','device','watchid','deviceid','mac'))):
                        rep['call_sites'].append({'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'incoming_registers':pmap,
                                                  'matching_baseapi_invokes':hits[:20],'invokes':sym.get('invokes',[])[:220],
                                                  'field_writes':sym.get('critical_field_writes',[])[:120],'returns':sym.get('returns',[])[:40]})
                    if pos and pos%120==0:self._progress(f'V1.92 · {label} · {pos}/{len(targets)} métodos…')
            def apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                        for i,n in enumerate(dexes,1):
                            self._progress(f'V1.92 · DEX {i}/{len(dexes)} · {n}')
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
            endpoints=[]
            for row in rep['baseapi_device_contracts']:
                for a in row.get('annotations',[]):
                    for v in (a.get('elements') or {}).values():
                        if isinstance(v,str) and ('app-device/' in v or 'device/' in v):endpoints.append(v)
            rep['scan_stats']=stats
            rep['resolved']={'endpoint_candidates':sorted(set(endpoints)),
                             'registration_contracts_found':len(rep['baseapi_device_contracts']),
                             'call_sites_found':len(rep['call_sites']),
                             'next':'Use the strongest registration/bind endpoint and its exact body fields in the next version, then retry checkForUpdate. Keep firmware/OTA writes disabled.',
                             'write_gate':'KEEP_OTA_DISABLED_UNTIL_OFFICIAL_FIRMWARE_METADATA_AND_FILE_VALIDATION_SUCCEED'}
            rep['summary']={'contracts':len(rep['baseapi_device_contracts']),'call_sites':len(rep['call_sites']),'candidate_strings':len(rep['candidate_strings']),'methods_symbolic':stats['methods_symbolic']}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v192');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-device-registration-v192.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.92 · falló: '+repr(err));return
            self.report={'utrawatch_device_registration_v192':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep['summary'];self.status.set(f"V1.92 LISTO · contratos={s['contracts']} · llamadas={s['call_sites']} · OTA=0 · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV192(root);root.mainloop()
