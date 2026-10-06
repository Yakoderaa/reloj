import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v193 as v193
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='1.94.0'
SCANINFO='Lcom/wtwd/cocousa/entity/device/ScanDeviceInfo;'
USERMAN='Lcom/wtwd/cocousa/manager/UserManager;'
ACCESSINFO='Lcom/wtwd/cocousa/entity/user/AccessInfo;'

class AppV194(v193.AppV193):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.94')
        self._clean_v194();self._install_v194();self._restore_location_button()
        self.status.set('V1.94 lista · resuelve exactamente los valores usados por userBindDevice. Sin red ni OTA.')

    def _clean_v194(self):
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

    def _install_v194(self):
        top=self.root.winfo_children()[0]
        self.v194_button=ttk.Button(top,text='RESOLVER VALORES DE ALTA',command=self.resolve_bind_values)
        sib=top.winfo_children()
        try:self.v194_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v194_button.place(x=8,y=8)

    def resolve_bind_values(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V1.94 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.94 · resolviendo getters de ScanDeviceInfo y UserManager…')
        def work():
            rep={'app_version':'1.94.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'resolve_exact_scanDeviceInfo_getter_field_mapping_and_userManager_accessInfo_sources_for_userBindDevice_without_network_or_ota',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'scan_device_info':{'fields':[],'methods':[]},'user_manager':{'fields':[],'methods':[]},'access_info':{'fields':[],'methods':[]},
                 'scan_stats':{},'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex':0,'methods_symbolic':0}
            def inspect(label,b):
                stats['dex']+=1
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                for f in fields:
                    cls=f.get('class')
                    row={'dex':label,'idx':f.get('idx'),'class':cls,'name':f.get('name'),'type':f.get('type')}
                    if cls==SCANINFO:rep['scan_device_info']['fields'].append(row)
                    elif cls==USERMAN:rep['user_manager']['fields'].append(row)
                    elif cls==ACCESSINFO:rep['access_info']['fields'].append(row)
                em={mid:(code,kind,acc) for _,mid,code,kind,acc in enc}
                targets=[m for m in methods if m.get('class') in (SCANINFO,USERMAN,ACCESSINFO)]
                self._progress(f'V1.94 · {label} · {len(targets)} métodos exactos…')
                for m in targets:
                    code,kind,acc=em.get(m.get('idx'),(0,None,None))
                    if not code:continue
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc);sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except Exception as ex:
                        rep.setdefault('symbolic_errors',[]).append({'dex':label,'method_idx':m.get('idx'),'error':repr(ex)});continue
                    stats['methods_symbolic']+=1
                    row={'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'incoming_registers':pmap,
                         'field_reads':sym.get('critical_field_reads',[])[:80],'field_writes':sym.get('critical_field_writes',[])[:80],
                         'invokes':sym.get('invokes',[])[:180],'returns':sym.get('returns',[])[:80]}
                    if m.get('class')==SCANINFO:rep['scan_device_info']['methods'].append(row)
                    elif m.get('class')==USERMAN:rep['user_manager']['methods'].append(row)
                    else:rep['access_info']['methods'].append(row)
            def apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                        for i,n in enumerate(dexes,1):
                            self._progress(f'V1.94 · DEX {i}/{len(dexes)} · {n}')
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

            getter_map={}
            for m in rep['scan_device_info']['methods']:
                proto=m.get('proto') or {}
                if proto.get('args'):continue
                if proto.get('return')!='Ljava/lang/String;':continue
                text=json.dumps(m,ensure_ascii=False)
                hits=[]
                for f in rep['scan_device_info']['fields']:
                    if f.get('name') and ('"name": "'+str(f.get('name'))+'"') in text:hits.append(f.get('name'))
                getter_map[str(m.get('method'))]={'method_idx':m.get('method_idx'),'field_candidates':sorted(set(hits)),'returns':m.get('returns')}

            access_fields={str(f.get('name')):f.get('type') for f in rep['access_info']['fields']}
            user_methods={}
            for m in rep['user_manager']['methods']:
                if m.get('method') in ('a','c','e','d'):
                    user_methods[str(m.get('method'))]={'proto':m.get('proto'),'returns':m.get('returns'),'invokes':m.get('invokes')}

            rep['scan_stats']=stats
            rep['resolved']={
                'userBindDevice_body_keys_from_v193':['macAddress','name','userId'],
                'name_expression_from_v193':'ScanDeviceInfo.c() + "_" + ScanDeviceInfo.a()',
                'mac_expression_from_v193':'ScanDeviceInfo.b()',
                'userId_expression_from_v193':'UserManager.c().e()',
                'scanDeviceInfo_string_getter_map':getter_map,
                'accessInfo_field_map':access_fields,
                'userManager_methods':user_methods,
                'ready_for_single_registration_request':bool(getter_map.get('a') and getter_map.get('b') and getter_map.get('c') and access_fields.get('userId')),
                'next':'Use the resolved getter/field mapping to construct one exact official userBindDevice request, then retry checkForUpdate. Keep firmware/OTA writes disabled.',
                'write_gate':'KEEP_OTA_DISABLED_UNTIL_OFFICIAL_FIRMWARE_METADATA_AND_FILE_VALIDATION_SUCCEED'}
            rep['summary']={'scan_fields':len(rep['scan_device_info']['fields']),'scan_methods':len(rep['scan_device_info']['methods']),
                            'user_manager_methods':len(rep['user_manager']['methods']),'access_info_fields':len(rep['access_info']['fields']),
                            'methods_symbolic':stats['methods_symbolic']}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v194');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-bind-values-v194.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.94 · falló: '+repr(err));return
            self.report={'utrawatch_bind_values_v194':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            r=rep['resolved'];self.status.set(f"V1.94 LISTO · getters={len(r.get('scanDeviceInfo_string_getter_map',{}))} · ready={r.get('ready_for_single_registration_request')} · red/OTA=0 · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV194(root);root.mainloop()
