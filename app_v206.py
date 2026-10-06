import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v205 as v205
import app_v199 as v199
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='2.06.0'
DM='Lcom/wtwd/cocousa/manager/DeviceManager;'
HEALTH='Lcom/wtwd/cocousa/ui/module/main/health/HealthModel;'
PRES='Lcom/wtwd/cocousa/ui/module/main/health/HealthPresenter;'
H1='Lcom/wtwd/cocousa/ui/module/main/health/HealthModel$1;'

class AppV206(v205.AppV205):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V2.06')
        self._clean_v206();self._install_v206();self._restore_location_button()
        self.status.set('V2.06 lista · resuelve DeviceManager.j() y el valor de area sin red ni OTA.')

    def _clean_v206(self):
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
                    else: walk(c)
                except:pass
        walk(self.root)

    def _install_v206(self):
        top=self.root.winfo_children()[0]
        self.v206_button=ttk.Button(top,text='CERRAR WATCHID + AREA',command=self.resolve_watchid_area)
        sib=top.winfo_children()
        try:self.v206_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v206_button.place(x=8,y=8)

    def resolve_watchid_area(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V2.06 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V2.06 · resolviendo DeviceManager.j/d y area…')
        def work():
            rep={'app_version':'2.06.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'resolve_exact_DeviceManager_watchId_mac_getters_and_activation_area_value_locally',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known':{'location_flow_closed_v205':True,'activation_body':['area','lat','lng','macAddress','watchId']},
                 'target_methods':[],'device_manager_getters':[],'area_evidence':[],'interesting_strings':[],
                 'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            wanted={(DM,'d'),(DM,'j'),(PRES,'S0'),(HEALTH,'h'),(HEALTH,'j')}
            def inspect(label,b):
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                exact,err=v199.AppV199._exact_code_map(b,types)
                if err:rep.setdefault('exact_map_errors',[]).append({'dex':label,'error':err})
                targets=[m for m in methods if (m.get('class'),m.get('name')) in wanted or m.get('class')==H1]
                for m in targets:
                    ex=exact.get(m.get('idx')) or {};code=ex.get('code_off');acc=ex.get('access_flags',0)
                    if not code:continue
                    self._progress(f'V2.06 · {m.get("class","").split("/")[-1]}{m.get("name")}')
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc)
                        sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except Exception as ex2:
                        rep.setdefault('symbolic_errors',[]).append({'class':m.get('class'),'method':m.get('name'),'error':repr(ex2)});continue
                    row={'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'code_off':code,'incoming_registers':pmap,'invokes':sym.get('invokes') or [],'trace':(sym.get('trace') or [])[:2800]}
                    rep['target_methods'].append(row)
                    if m.get('class')==DM and m.get('name') in ('d','j'):
                        rep['device_manager_getters'].append(row)
                    txt=json.dumps(row,ensure_ascii=False)
                    for key in ('WEATHER','weather','area','GPS','watchId','macAddress','PREF_KEY','deviceId','watch'):
                        if key in txt:rep['area_evidence'].append({'class':m.get('class'),'method':m.get('name'),'keyword':key})
                for s in strings:
                    sv=str(s)
                    if any(k.lower() in sv.lower() for k in ('weather','area','watchid','macaddress','gps','pref_key_hardware','deviceid')):
                        rep['interesting_strings'].append(sv)
                rep['interesting_strings']=list(dict.fromkeys(rep['interesting_strings']))[:300]
            def apk(name,data):
                with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                    dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                    for i,n in enumerate(dexes,1):
                        self._progress(f'V2.06 · DEX {i}/{len(dexes)} · {n}')
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
            rep['resolved']={'device_manager_d_found':any(x.get('method')=='d' for x in rep['device_manager_getters']),
                'device_manager_j_found':any(x.get('method')=='j' for x in rep['device_manager_getters']),
                'location_flow_closed':True,
                'next':'Use exact getter evidence plus selected BLE identity and explicit location values to prepare one activationDevice request; keep firmware and OTA writes disabled.',
                'write_gate':'NO_DEVICE_WRITES_IN_THIS_VERSION'}
            rep['summary']={'target_methods':len(rep['target_methods']),'device_manager_getters':len(rep['device_manager_getters']),'area_evidence':len(rep['area_evidence']),'interesting_strings':len(rep['interesting_strings'])}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v206');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-watchid-area-v206.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V2.06 · falló: '+repr(err));return
            self.report={'utrawatch_watchid_area_v206':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep.get('summary') or {}
            self.status.set(f"V2.06 LISTO · getters={s.get('device_manager_getters',0)} · area={s.get('area_evidence',0)} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV206(root);root.mainloop()
