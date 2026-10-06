import io,json,os,zipfile,re
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v181 as v181
import app_v180 as v180
import app_v179 as v179
import app_v145 as v145

base.APP_VERSION='1.82.0'
BASEAPI=v181.BASEAPI
HWM=v181.HWM
HW=v181.HW
HWVER=v181.HWVER
BLEMAN=v181.BLEMAN

class AppV182(v181.AppV181):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.82')
        self._clean_v182();self._install_v182()
        self.status.set('V1.82 lista · resuelve endpoint oficial, getters HardwareVersion y metadatos OTA. Sin red ni escrituras.')

    def _clean_v182(self):
        keep=('buscar relojes','buscar dispositivos','buscar disp','buscar actualización','buscar actualizacion','buscar actualizaciones')
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

    def _install_v182(self):
        top=self.root.winfo_children()[0]
        self.v182_button=ttk.Button(top,text='RESOLVER ENDPOINT + METADATOS OTA',command=self.resolve_endpoint_metadata)
        sib=top.winfo_children()
        try:self.v182_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v182_button.place(x=8,y=8)

    @staticmethod
    def _endpoint_candidate(s):
        q=str(s or '').strip(); low=q.lower()
        if not q or len(q)>500:return False
        if low in ('app-device/checkforupdate','/app-device/checkforupdate'):return True
        if ('app-device' in low and ('update' in low or 'firmware' in low)):return True
        if ('checkforupdate' in low or 'check_for_update' in low):return True
        if (low.startswith(('http://','https://','/')) or '/' in low) and any(k in low for k in ('firmware','hardware','upgrade','update','ota')):return True
        return False

    @staticmethod
    def _metadata_string(s):
        low=str(s or '').lower()
        keys=('currentfirmware','hardwareversion','devicefirmwareversion','firmware','fileurl','file_url','downloadurl','download_url','md5','checksum','sha1','sha256','filesize','file_size','size','version','ota/','.fot','.img','.bin','pref_key_hardware_version')
        return any(k in low for k in keys)

    @staticmethod
    def _field_from_value(v):
        if not isinstance(v,dict):return None
        if v.get('kind') in ('field','static_field'):
            f=v.get('field') or {}
            return {'class':f.get('class'),'name':f.get('name'),'type':f.get('type')}
        for k in ('value','object','left','right'):
            x=v.get(k)
            if isinstance(x,dict):
                r=AppV182._field_from_value(x)
                if r:return r
        return None

    def resolve_endpoint_metadata(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V1.82 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.82 · resolviendo endpoint, HardwareVersion y contrato de archivo OTA…')
        def work():
            rep={'app_version':'1.82.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'resolve_exact_official_firmware_endpoint_hardwareversion_backing_fields_file_roles_and_pre_download_validation_contract',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'endpoint_candidates':[],'metadata_strings':[],'hardware_version_fields':[],'hardware_version_getters':[],
                 'hardware_version_uses':[],'baseapi_i':[],'download_path_evidence':[],'ble_handoff':[],
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            seen_ep=set();seen_meta=set();seen_field=set();seen_use=set()
            def inspect(label,b):
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                em={mid:(code,kind,acc) for _,mid,code,kind,acc in enc}
                for s in strings:
                    if self._endpoint_candidate(s) and s not in seen_ep:
                        seen_ep.add(s);rep['endpoint_candidates'].append({'dex':label,'value':s})
                    if self._metadata_string(s) and s not in seen_meta:
                        seen_meta.add(s);rep['metadata_strings'].append({'dex':label,'value':s})
                for f in fields:
                    try:fc=f.get('class');fn=f.get('name');ft=f.get('type')
                    except:continue
                    if fc==HWVER:
                        key=(fc,fn,ft)
                        if key not in seen_field:
                            seen_field.add(key);rep['hardware_version_fields'].append({'dex':label,'class':fc,'name':fn,'type':ft})
                for m in methods:
                    cls,name=m.get('class'),m.get('name'); code,kind,acc=em.get(m['idx'],(0,None,None))
                    if not code:continue
                    selected=(cls in (BASEAPI,HWM,HW,HWVER) or cls.startswith(HWM[:-1]+'$') or cls.startswith(HW[:-1]+'$'))
                    if not selected:continue
                    s=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                    pmap=v180.AppV180._param_map(b,code,m,acc)
                    s=v180.AppV180._rewrite_unknown_regs(s,pmap)
                    row={'dex':label,'class':cls,'method':name,'method_idx':m['idx'],'proto':m.get('proto'),'code_off':code,
                         'incoming_registers':pmap,'returns':s.get('returns',[])[:30],'invokes':s.get('invokes',[])[:220],
                         'critical_field_writes':s.get('critical_field_writes',[])[:80]}
                    if cls==BASEAPI and name=='i':rep['baseapi_i'].append(row)
                    if cls==HWVER:
                        backing=[]
                        for rr in s.get('returns',[]):
                            f=self._field_from_value(rr.get('value') if isinstance(rr,dict) else rr)
                            if f and f not in backing:backing.append(f)
                        row['backing_fields']=backing
                        rep['hardware_version_getters'].append(row)
                    if cls in (HWM,HW) or cls.startswith(HWM[:-1]+'$') or cls.startswith(HW[:-1]+'$'):
                        invs=s.get('invokes',[])
                        for inv in invs:
                            t=inv.get('target') or {}
                            if t.get('class')==HWVER:
                                key=(label,m['idx'],inv.get('unit'),t.get('method'))
                                if key in seen_use:continue
                                seen_use.add(key)
                                context=[]
                                for other in invs:
                                    ou=other.get('unit')
                                    if isinstance(ou,int) and isinstance(inv.get('unit'),int) and abs(ou-inv.get('unit'))<=18:
                                        ot=other.get('target') or {}
                                        context.append({'unit':ou,'class':ot.get('class'),'method':ot.get('method'),'args':other.get('args')})
                                rep['hardware_version_uses'].append({'dex':label,'from_class':cls,'from_method':name,'unit':inv.get('unit'),
                                    'getter':t.get('method'),'getter_proto':t.get('proto'),'context':context[:40]})
                            if t.get('class')==BLEMAN and t.get('method')=='H':
                                rep['ble_handoff'].append({'dex':label,'from_class':cls,'from_method':name,'unit':inv.get('unit'),'args':inv.get('args')})
                    if cls==HW and name=='t1':
                        strs=[]
                        for ev in s.get('trace',[]):
                            if ev.get('kind')=='string' and str(ev.get('value')) in ('ota/','.fot','.img','PREF_KEY_ZK_OTA','/'):
                                strs.append(ev.get('value'))
                        rep['download_path_evidence'].append({'dex':label,'method':'t1','strings':strs,'invokes':s.get('invokes',[])[:260]})
            def apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')):inspect(name+'!'+n,z.read(n))
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
            eps=[x['value'] for x in rep['endpoint_candidates']]
            exact=[x for x in eps if 'checkforupdate' in x.lower() or ('app-device' in x.lower() and 'update' in x.lower())]
            getter_map={}
            for g in rep['hardware_version_getters']:
                if g.get('backing_fields'):getter_map[g['method']]=g['backing_fields']
            roles={}
            for u in rep['hardware_version_uses']:
                g=u.get('getter');txt=json.dumps(u.get('context',[]),ensure_ascii=False).lower()
                hints=roles.setdefault(g,set())
                if '.fot' in txt or '.img' in txt:hints.add('firmware_filename_stem_or_version')
                if 'fileinputstream' in txt or 'available' in txt:hints.add('downloaded_file_validation_or_size')
                if 'ihardwareupdateview' in txt:hints.add('displayed_update_metadata')
            rep['resolved']={'exact_endpoint_candidates':exact,'getter_to_backing_field':getter_map,
                             'getter_role_hints':{k:sorted(v) for k,v in roles.items()},
                             'official_local_extensions':['.fot','.img'],
                             'ota_directory_prefix':'ota/',
                             'write_gate':'KEEP_OTA_DISABLED_UNTIL_OFFICIAL_FILE_HEADER_SIZE_AND_HASH_ARE_VALIDATED'}
            rep['summary']={'endpoint_candidates':len(rep['endpoint_candidates']),'exact_endpoint_candidates':len(exact),
                            'hardware_version_fields':len(rep['hardware_version_fields']),'hardware_version_getters':len(rep['hardware_version_getters']),
                            'hardware_version_uses':len(rep['hardware_version_uses']),'ble_handoff_calls':len(rep['ble_handoff']),
                            'next':'Use the exact endpoint plus resolved HardwareVersion fields to make the official metadata request/download, validate file identity/header/size/hash, and only then enable OTA writes.'}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v182');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-endpoint-metadata-v182.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.82 · falló: '+repr(err));return
            self.report={'official_endpoint_metadata_v182':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep['summary'];self.status.set(f"V1.82 LISTO · endpoint exacto={s['exact_endpoint_candidates']} · campos={s['hardware_version_fields']} · getters={s['hardware_version_getters']} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV182(root);root.mainloop()
