import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v174 as v174
import app_v145 as v145

base.APP_VERSION='1.75.0'

class AppV175(v174.AppV174):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.75')
        self._clean_v175();self._install_v175()
        self.status.set('V1.75 lista · mapea transporte OTA BLE exacto desde UtraWatch. Sin red ni escrituras.')
    def _clean_v175(self):
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
    def _install_v175(self):
        top=self.root.winfo_children()[0]
        self.v175_button=ttk.Button(top,text='MAPEAR OTA BLE EXACTA',command=self.map_ota_ble)
        sib=top.winfo_children()
        try:self.v175_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v175_button.place(x=8,y=8)
    def map_ota_ble(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V1.75 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.75 · buscando clases, eventos y paquetes OTA BLE…')
        def work():
            rep={'app_version':'1.75.0','generated_utc':datetime.now(timezone.utc).isoformat(),'goal':'map_exact_ble_ota_transport_from_utrawatch_without_network_or_device_writes','validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,'ota_methods':[],'ota_strings':[],'ota_fields':[],'hardware_update_methods':[],'event_methods':[],'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            seen_s=set()
            def row(label,m,code,kind,acc,d):return {'dex':label,'class':m['class'],'method':m['name'],'method_idx':m['idx'],'proto':m.get('proto'),'kind':kind,'access_flags':acc,'code_off':code,'strings':d.get('strings',[]),'calls':d.get('calls',[]),'fields':d.get('fields',[]),'consts':d.get('consts',[]),'raw_code_hex':d.get('raw_code_hex','')}
            def inspect(label,b):
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                em={mid:(code,kind,acc) for _,mid,code,kind,acc in enc}
                for s in strings:
                    sl=s.lower()
                    if any(k in sl for k in ('ota','firmware','upgrade','update','zkbluetooth','ffc1','ffc2','f000ffc0')) and s not in seen_s:
                        seen_s.add(s);rep['ota_strings'].append(s)
                for f in fields:
                    text=(str(f.get('class',''))+' '+str(f.get('name',''))+' '+str(f.get('type',''))).lower()
                    if any(k in text for k in ('ota','firmware','upgrade','update','zkbluetooth')):rep['ota_fields'].append({'dex':label,**f})
                for m in methods:
                    code,kind,acc=em.get(m['idx'],(0,None,None))
                    if not code:continue
                    cls=m['class'];name=m['name'];key=(cls+' '+name).lower()
                    if not any(k in key for k in ('ota','firmware','upgrade','update','zkbluetooth')):continue
                    d=self._details(b,code,strings,methods,fields);r=row(label,m,code,kind,acc,d);rep['ota_methods'].append(r)
                    if 'hardwareupdatemodel' in cls.lower():rep['hardware_update_methods'].append(r)
                    if 'event' in cls.lower():rep['event_methods'].append(r)
            def apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data)) as z:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')):inspect(name+'!'+n,z.read(n))
                except Exception as ex:rep.setdefault('errors',[]).append({'apk':name,'error':repr(ex)})
            if zipfile.is_zipfile(chosen):
                with zipfile.ZipFile(chosen) as z:
                    apks=[n for n in z.namelist() if n.lower().endswith('.apk')]
                    if apks:
                        for n in apks:
                            if 'com.wtwd.utrawatch' in n.lower() or 'base' in n.lower():apk(n,z.read(n))
                    else:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')):inspect(n,z.read(n))
            else:
                with open(chosen,'rb') as f:apk(os.path.basename(chosen),f.read())
            for k,lim in [('ota_methods',500),('hardware_update_methods',200),('event_methods',200)]:
                seen=set();out=[]
                for x in rep[k]:
                    q=(x['dex'],x['method_idx'])
                    if q not in seen:seen.add(q);out.append(x)
                rep[k]=out[:lim]
            rep['summary']={'ota_method_count':len(rep['ota_methods']),'hardware_update_method_count':len(rep['hardware_update_methods']),'event_method_count':len(rep['event_methods']),'ota_string_count':len(rep['ota_strings']),'next':'Use this map to identify the exact BLE command sequence, chunk framing, acknowledgements and completion event before any device-side write is enabled.'}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v175');os.makedirs(folder,exist_ok=True);out=os.path.join(folder,'utrawatch-ota-ble-map-v175.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.75 · falló: '+repr(err));return
            self.report={'ota_ble_map_v175':rep};self.show()
            try:t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep['summary'];self.status.set(f"V1.75 LISTO · OTA={s['ota_method_count']} · HW={s['hardware_update_method_count']} · eventos={s['event_method_count']} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV175(root);root.mainloop()
