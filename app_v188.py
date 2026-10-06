import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v187 as v187
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='1.88.0'
BASEAPI=v187.BASEAPI
ACCESSINFO=v187.ACCESSINFO

class AppV188(v187.AppV187):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.88')
        self._clean_v188();self._install_v188();self._restore_location_button()
        self.status.set('V1.88 lista · resuelve origen de appDeviceId y AccessInfo exacto. Sin red ni OTA.')

    def _clean_v188(self):
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

    def _install_v188(self):
        top=self.root.winfo_children()[0]
        self.v188_button=ttk.Button(top,text='RESOLVER appDeviceId + ACCESSINFO',command=self.resolve_exact_guest_contract)
        sib=top.winfo_children()
        try:self.v188_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v188_button.place(x=8,y=8)

    @staticmethod
    def _interesting(cls,name=''):
        q=(str(cls or '')+' '+str(name or '')).lower()
        if not (str(cls or '').lower().startswith('lcom/wtwd/cocousa/') or str(cls or '').lower().startswith('lcom/wtwd/')):return False
        return any(k in q for k in ('welcome','deviceid','device_id','androidid','android_id','tourist','accessinfo','login','startup','application','manager'))

    def resolve_exact_guest_contract(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V1.88 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.88 · rastreando origen exacto de appDeviceId…')
        def work():
            rep={'app_version':'1.88.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'resolve_exact_appDeviceId_producer_and_AccessInfo_field_getter_contract_without_network_credentials_or_ota',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'appdeviceid_sites':[],'accessinfo_fields':[],'accessinfo_methods':[],'tourist_sites':[],'relevant_strings':[],
                 'scan_stats':{},'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'credential_collection':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex':0,'methods_total':0,'methods_symbolic':0};seen_s=set();seen_site=set()
            def inspect(label,b):
                stats['dex']+=1
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                for f in fields:
                    try:
                        if f.get('class')==ACCESSINFO:rep['accessinfo_fields'].append({'dex':label,'idx':f.get('idx'),'name':f.get('name'),'type':f.get('type')})
                    except:pass
                for s in strings:
                    low=str(s).lower()
                    if any(k in low for k in ('appdeviceid','deviceid','device_id','androidid','android_id','getuniquedeviceid','touristlogin')) and s not in seen_s:
                        seen_s.add(s);rep['relevant_strings'].append({'dex':label,'value':s})
                em={mid:(code,kind,acc) for _,mid,code,kind,acc in enc};stats['methods_total']+=len(methods)
                targets=[m for m in methods if m.get('class')==ACCESSINFO or self._interesting(m.get('class'),m.get('name'))]
                self._progress(f'V1.88 · {label} · {len(targets)} métodos dirigidos…')
                for pos,m in enumerate(targets):
                    code,kind,acc=em.get(m.get('idx'),(0,None,None))
                    if not code:continue
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc);sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except:continue
                    stats['methods_symbolic']+=1
                    row={'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'incoming_registers':pmap,
                         'invokes':sym.get('invokes',[])[:220],'field_writes':sym.get('critical_field_writes',[])[:120],'returns':sym.get('returns',[])[:60]}
                    txt=json.dumps(row,ensure_ascii=False).lower()
                    if m.get('class')==ACCESSINFO:rep['accessinfo_methods'].append(row)
                    if 'appdeviceid' in txt or 'getuniquedeviceid' in txt or 'android_id' in txt or 'androidid' in txt:
                        key=(label,m.get('idx'))
                        if key not in seen_site:
                            seen_site.add(key);rep['appdeviceid_sites'].append(row)
                    for inv in sym.get('invokes',[]):
                        t=inv.get('target') or {}
                        if t.get('class')==BASEAPI and t.get('method')=='B':
                            rep['tourist_sites'].append({**row,'tourist_invoke':inv});break
                    if pos and pos%100==0:self._progress(f'V1.88 · {label} · {pos}/{len(targets)}…')
            def apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                        for i,n in enumerate(dexes,1):
                            self._progress(f'V1.88 · DEX {i}/{len(dexes)} · {n}')
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
            field_map={x.get('name'):x.get('type') for x in rep['accessinfo_fields']}
            getter_map=[]
            for m in rep['accessinfo_methods']:
                for r in m.get('returns',[]):
                    v=r.get('value') or {};f=v.get('field') or {}
                    if f.get('class')==ACCESSINFO:
                        getter_map.append({'method':m.get('method'),'method_idx':m.get('method_idx'),'field':f.get('name'),'type':f.get('type')})
            rep['scan_stats']=stats
            rep['resolved']={'tourist_call_sites':len(rep['tourist_sites']),'appdeviceid_related_methods':len(rep['appdeviceid_sites']),
                             'accessinfo_field_map':field_map,'accessinfo_getter_map':getter_map,
                             'request_body_exact':{'appDeviceId':'value supplied by WelcomeModel touristLogin call path'},
                             'manual_access_token_required':False,
                             'next':'Use the exact appDeviceId producer and AccessInfo getter mapping to validate the official session contract before any network or firmware action.',
                             'write_gate':'KEEP_OTA_DISABLED_UNTIL_OFFICIAL_FIRMWARE_METADATA_AND_FILE_VALIDATION_SUCCEED'}
            rep['summary']={'appdeviceid_sites':len(rep['appdeviceid_sites']),'tourist_sites':len(rep['tourist_sites']),'accessinfo_fields':len(rep['accessinfo_fields']),
                            'accessinfo_methods':len(rep['accessinfo_methods']),'methods_symbolic':stats['methods_symbolic']}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v188');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-exact-guest-contract-v188.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.88 · falló: '+repr(err));return
            self.report={'utrawatch_exact_guest_contract_v188':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep['summary'];self.status.set(f"V1.88 LISTO · appDeviceId={s['appdeviceid_sites']} métodos · tourist={s['tourist_sites']} · AccessInfo={s['accessinfo_fields']} campos · OTA=0 · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV188(root);root.mainloop()
