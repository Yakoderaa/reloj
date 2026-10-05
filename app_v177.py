import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v176 as v176
import app_v145 as v145

base.APP_VERSION='1.77.0'

CMD='Lcom/bluetrum/fota/bluetooth/a;'
DATA='Lcom/bluetrum/fota/bluetooth/b;'
MGR='Lcom/bluetrum/fota/bluetooth/h;'
ZK='Lcom/wtwd/cocousa/ble/ZKBleOtaManager;'
BLE='Lcom/wtwd/cocousa/ble/BleConnectService;'
LISTENER='Lcom/wtwd/cocousa/ble/BleConnectService$ZKBleOtaDataListener;'
HW='Lcom/wtwd/cocousa/ui/module/main/device/update/HardwareUpdatePresenter;'

class AppV177(v176.AppV176):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.77')
        self._clean_v177();self._install_v177()
        self.status.set('V1.77 lista · extrae framing, chunking, estados y handoff OTA exactos. Sin red ni escrituras.')

    def _clean_v177(self):
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
                    else: walk(c)
                except: pass
        walk(self.root)

    def _install_v177(self):
        top=self.root.winfo_children()[0]
        self.v177_button=ttk.Button(top,text='EXTRAER FRAMING OTA',command=self.extract_ota_framing)
        sib=top.winfo_children()
        try:self.v177_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v177_button.place(x=8,y=8)

    def extract_ota_framing(self):
        ready,validation,vpath=self._ready_report()
        if not ready:
            self.status.set('V1.77 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.77 · extrayendo generador de comandos, proveedor de bloques y puente BLE…')
        def work():
            rep={
                'app_version':'1.77.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                'goal':'recover_exact_bluetrum_command_framing_data_chunking_state_ack_and_ble_handoff_without_network_or_device_writes',
                'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                'known_from_v176':{
                    'ota_write_characteristic':'0000b003-0000-1000-8000-00805f9b34fb',
                    'write_bridge':'BleConnectService.a([B) -> BluetoothGattCharacteristic.setValue/setWriteType -> BluetoothGatt.writeCharacteristic',
                    'notify_bridge':'BleConnectService$5.onCharacteristicChanged -> ZKBleOtaManager/Bluetrum h.u([B)',
                    'manager_fields':['allowedUpdate','dataProvider','commandGenerator','isDeviceReady'],
                    'zk_default_mtu':23
                },
                'command_generator_methods':[],'data_provider_methods':[],'manager_methods':[],'zk_methods':[],
                'ble_bridge_methods':[],'listener_methods':[],'hardware_handoff_methods':[],
                'cross_edges':[],'fields_by_class':{},'strings_of_interest':[],
                'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}
            }
            seen_edges=set();seen_strings=set()
            focus_classes={CMD,DATA,MGR,ZK,LISTENER}
            ble_names={'a','a0','I','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y'}
            hw_names={'t1','u1','v1','X0','O'}
            def row(label,m,code,kind,acc,d):
                return {'dex':label,'class':m['class'],'method':m['name'],'method_idx':m['idx'],'proto':m.get('proto'),
                        'kind':kind,'access_flags':acc,'code_off':code,'strings':d.get('strings',[]),
                        'calls':d.get('calls',[]),'fields':d.get('fields',[]),'consts':d.get('consts',[]),
                        'raw_code_hex':d.get('raw_code_hex','')}
            def inspect(label,b):
                try: strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:
                    rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                em={mid:(code,kind,acc) for _,mid,code,kind,acc in enc}
                byidx={m['idx']:m for m in methods}
                buckets={CMD:'command_generator_methods',DATA:'data_provider_methods',MGR:'manager_methods',ZK:'zk_methods',LISTENER:'listener_methods'}
                for cls in (CMD,DATA,MGR,ZK,BLE,LISTENER,HW):
                    fs=[{'dex':label,**f} for f in fields if f.get('class')==cls]
                    if fs: rep['fields_by_class'].setdefault(cls,[]).extend(fs)
                for s in strings:
                    sl=s.lower()
                    if any(k in sl for k in ('ota','firmware','upgrade','startaddress','blocksize','packetsize','allowedupdate','checksum','crc','md5','ready','progress','writezkdata','升级','固件')):
                        if s not in seen_strings:
                            seen_strings.add(s);rep['strings_of_interest'].append(s)
                chosen_methods=[]
                for m in methods:
                    cls,name=m['class'],m['name']
                    if cls in focus_classes or (cls==BLE and name in ble_names) or (cls==HW and name in hw_names):
                        chosen_methods.append(m)
                for m in chosen_methods:
                    code,kind,acc=em.get(m['idx'],(0,None,None))
                    if not code:continue
                    d=self._details(b,code,strings,methods,fields);rr=row(label,m,code,kind,acc,d)
                    cls,name=m['class'],m['name']
                    if cls in buckets: rep[buckets[cls]].append(rr)
                    elif cls==BLE: rep['ble_bridge_methods'].append(rr)
                    elif cls==HW: rep['hardware_handoff_methods'].append(rr)
                    for c in d.get('calls',[]):
                        tc=c.get('class'); tm=c.get('method'); tid=c.get('idx')
                        if tc in {CMD,DATA,MGR,ZK,BLE,LISTENER,HW}:
                            e=(label,m['idx'],tid)
                            if e not in seen_edges:
                                seen_edges.add(e);rep['cross_edges'].append({
                                    'dex':label,'from_class':cls,'from_method':name,'from_idx':m['idx'],
                                    'to_class':tc,'to_method':tm,'to_idx':tid,'to_proto':c.get('proto')})
            def apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')):
                                inspect(name+'!'+n,z.read(n))
                except Exception as ex: rep.setdefault('errors',[]).append({'apk':name,'error':repr(ex)})
            if zipfile.is_zipfile(chosen):
                with zipfile.ZipFile(chosen,'r') as z:
                    apks=[n for n in z.namelist() if n.lower().endswith('.apk')]
                    if apks:
                        preferred=[n for n in apks if 'com.wtwd.utrawatch' in n.lower() or os.path.basename(n).lower().startswith(('base','master'))]
                        for n in (preferred or apks[:1]): apk(n,z.read(n))
                    else:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')): inspect(n,z.read(n))
            else:
                with open(chosen,'rb') as f: apk(os.path.basename(chosen),f.read())
            for k in ('command_generator_methods','data_provider_methods','manager_methods','zk_methods','ble_bridge_methods','listener_methods','hardware_handoff_methods','cross_edges','strings_of_interest'):
                rep[k]=rep[k][:500]
            for cls in list(rep['fields_by_class']): rep['fields_by_class'][cls]=rep['fields_by_class'][cls][:200]
            rep['summary']={
                'command_generator_methods':len(rep['command_generator_methods']),
                'data_provider_methods':len(rep['data_provider_methods']),
                'manager_methods':len(rep['manager_methods']),
                'zk_methods':len(rep['zk_methods']),
                'ble_bridge_methods':len(rep['ble_bridge_methods']),
                'listener_methods':len(rep['listener_methods']),
                'hardware_handoff_methods':len(rep['hardware_handoff_methods']),
                'cross_edges':len(rep['cross_edges']),
                'next':'Resolve exact command bytes, data-provider offsets/lengths, ACK/state transitions and the presenter-to-manager start call. Only after those are proven should a read-only/live OTA preflight be considered.'
            }
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v177');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-ota-framing-v177.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f: json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.77 · falló: '+repr(err));return
            self.report={'ota_framing_v177':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep['summary'];self.status.set(f"V1.77 LISTO · cmd={s['command_generator_methods']} · data={s['data_provider_methods']} · mgr={s['manager_methods']} · edges={s['cross_edges']} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV177(root);root.mainloop()
