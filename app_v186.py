import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v185 as v185
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='1.86.0'
BASEAPI=v185.BASEAPI

class AppV186(v185.AppV185):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.86')
        self._clean_v186();self._install_v186();self._restore_location_button()
        self.status.set('V1.86 lista · análisis auth rápido + Buscar ubicación restaurado. Sin red ni OTA.')

    def _clean_v186(self):
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

    def _restore_location_button(self):
        found=[]
        def walk(w):
            for c in list(w.winfo_children()):
                try:
                    if isinstance(c,(ttk.Button,tk.Button)):
                        t=str(c.cget('text') or '').lower()
                        if 'ubic' in t:found.append(c)
                    walk(c)
                except:pass
        walk(self.root)
        for b in found:
            try:
                if not b.winfo_manager():
                    parent=b.master
                    b.pack(side='left',padx=4)
            except:pass

    def _install_v186(self):
        top=self.root.winfo_children()[0]
        self.v186_button=ttk.Button(top,text='RESOLVER AUTH RÁPIDO',command=self.resolve_auth_fast)
        sib=top.winfo_children()
        try:self.v186_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v186_button.place(x=8,y=8)

    def _progress(self,text):
        try:self.root.after(0,lambda:self.status.set(text))
        except:pass

    @staticmethod
    def _interesting_class(cls):
        q=str(cls or '').lower()
        if not (q.startswith('lcom/wtwd/cocousa/') or q.startswith('lcom/wtwd/')):return False
        return any(k in q for k in ('login','signin','sign_in','auth','account','user','token','session','base/model','application'))

    def resolve_auth_fast(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V1.86 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.86 · abriendo UtraWatch…')
        def work():
            rep={'app_version':'1.86.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'fast_targeted_reconstruction_of_utrawatch_auth_contract_without_full_app_symbolic_scan',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'baseapi_auth_contracts':[],'auth_strings':[],'token_pref_uses':[],'candidate_hosts':[],'scan_stats':{},
                 'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'credential_collection':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            seen_s=set();seen_h=set();seen_use=set();stats={'dex':0,'methods_total':0,'methods_symbolic':0}
            def inspect(label,b):
                stats['dex']+=1;self._progress(f'V1.86 · leyendo {label} · strings/anotaciones…')
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                for s in strings:
                    if self._auth_text(s) and s not in seen_s:
                        seen_s.add(s);rep['auth_strings'].append({'dex':label,'value':s})
                    low=str(s).lower()
                    if low.startswith(('http://','https://')) and any(x in low for x in ('watchhealth','halfwit','cocousa','utra')) and s not in seen_h:
                        seen_h.add(s);rep['candidate_hosts'].append({'dex':label,'value':s})
                ann=self._retrofit_annotations(b,strings,types,fields,methods,BASEAPI,None)
                for row in ann.get('method_annotations',[]):
                    m=row.get('method') or {};anns=row.get('annotations') or []
                    text=json.dumps(anns,ensure_ascii=False).lower()
                    if self._auth_text(text):
                        params=[]
                        for pr in ann.get('parameter_annotations',[]):
                            pm=pr.get('method') or {}
                            if pm.get('idx')==m.get('idx'):params=pr.get('parameters') or [];break
                        rep['baseapi_auth_contracts'].append({'dex':label,'method':m,'annotations':anns,'parameters':params})
                em={mid:(code,kind,acc) for _,mid,code,kind,acc in enc};stats['methods_total']+=len(methods)
                targets=[]
                for m in methods:
                    cls=str(m.get('class') or '')
                    if self._interesting_class(cls):targets.append(m)
                self._progress(f'V1.86 · {label} · análisis dirigido {len(targets)} métodos…')
                for pos,m in enumerate(targets):
                    code,kind,acc=em.get(m.get('idx'),(0,None,None))
                    if not code:continue
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc);sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except:continue
                    stats['methods_symbolic']+=1
                    txt=json.dumps(sym,ensure_ascii=False).lower()
                    if 'access-token' in txt or 'pref_key_access_token' in txt or 'accesstoken' in txt:
                        key=(label,m.get('idx'))
                        if key in seen_use:continue
                        seen_use.add(key)
                        rep['token_pref_uses'].append({'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),
                            'incoming_registers':pmap,'invokes':sym.get('invokes',[])[:100],'field_writes':sym.get('critical_field_writes',[])[:50],'returns':sym.get('returns',[])[:20]})
                    if pos and pos%100==0:self._progress(f'V1.86 · {label} · {pos}/{len(targets)} métodos…')
            def apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                        for i,n in enumerate(dexes,1):
                            self._progress(f'V1.86 · DEX {i}/{len(dexes)} · {n}')
                            inspect(name+'!'+n,z.read(n))
                except Exception as ex:rep.setdefault('errors',[]).append({'apk':name,'error':repr(ex)})
            if zipfile.is_zipfile(chosen):
                with zipfile.ZipFile(chosen,'r') as z:
                    apks=[n for n in z.namelist() if n.lower().endswith('.apk')]
                    if apks:
                        preferred=[n for n in apks if 'com.wtwd.utrawatch' in n.lower() or os.path.basename(n).lower().startswith(('base','master'))]
                        chosen_apks=preferred or apks[:1]
                        for i,n in enumerate(chosen_apks,1):
                            self._progress(f'V1.86 · APK {i}/{len(chosen_apks)} · {os.path.basename(n)}')
                            apk(n,z.read(n))
                    else:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')):inspect(n,z.read(n))
            else:
                with open(chosen,'rb') as f:apk(os.path.basename(chosen),f.read())
            candidates=[]
            for x in rep['baseapi_auth_contracts']:
                for a in x.get('annotations',[]):
                    for v in (a.get('elements') or {}).values():
                        if isinstance(v,str) and self._auth_text(v):candidates.append(v)
            rep['scan_stats']=stats
            rep['resolved']={'auth_endpoint_candidates':sorted(set(candidates)),'manual_access_token_required':False,
                'next':'Use the targeted auth evidence to implement an explicit user-driven UtraWatch sign-in flow, then query official firmware metadata.',
                'write_gate':'KEEP_OTA_DISABLED_UNTIL_OFFICIAL_FIRMWARE_METADATA_AND_FILE_VALIDATION_SUCCEED'}
            rep['summary']={'baseapi_auth_contracts':len(rep['baseapi_auth_contracts']),'auth_strings':len(rep['auth_strings']),
                'token_pref_uses':len(rep['token_pref_uses']),'candidate_hosts':len(rep['candidate_hosts']),'methods_symbolic':stats['methods_symbolic']}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v186');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-auth-fast-v186.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.86 · falló: '+repr(err));return
            self.report={'utrawatch_auth_fast_v186':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep['summary'];self.status.set(f"V1.86 LISTO · contratos={s['baseapi_auth_contracts']} · prefs={s['token_pref_uses']} · métodos={s['methods_symbolic']} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV186(root);root.mainloop()
