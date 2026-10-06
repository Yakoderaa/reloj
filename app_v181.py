import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v180 as v180
import app_v179 as v179
import app_v145 as v145

base.APP_VERSION='1.81.0'
BASEAPI='Lcom/wtwd/cocousa/api/BaseApi;'
HWM=v179.HWM
HW=v179.HW
HWVER=v180.HWVER
BLEMAN='Lcom/wtwd/cocousa/ble/BleManager;'

class AppV181(v180.AppV180):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.81')
        self._clean_v181();self._install_v181()
        self.status.set('V1.81 lista · resuelve petición oficial de firmware, respuesta y handoff exacto al OTA. Sin red ni escrituras.')

    def _clean_v181(self):
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

    def _install_v181(self):
        top=self.root.winfo_children()[0]
        self.v181_button=ttk.Button(top,text='RESOLVER FIRMWARE OFICIAL',command=self.resolve_firmware_contract)
        sib=top.winfo_children()
        try:self.v181_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v181_button.place(x=8,y=8)

    @staticmethod
    def _is_fw_string(s):
        q=str(s or '').lower()
        keys=('currentfirmware','hardwareversion','firmware','upgrade','ota/','.fot','.img','.bin','download','fileurl','file_url','md5','checksum','version','app-halfwit','watchhealth','pref_key_hardware_version')
        return any(k in q for k in keys)

    def resolve_firmware_contract(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V1.81 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.81 · resolviendo request, response, URL/archivo y handoff OTA…')
        def work():
            rep={'app_version':'1.81.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'resolve_exact_official_firmware_request_response_identity_file_metadata_and_safe_ota_handoff_from_utrawatch_apk',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known_from_v180':{'resolved_methods':133,'command_templates':11,'direct_ble_templates':5,'exact_start_edges':174,'firmware_source_methods':100,'hardware_version_methods':5},
                 'base_api_methods':[],'hardware_model_methods':[],'hardware_presenter_methods':[],'hardware_version_methods':[],
                 'callback_methods':[],'firmware_strings':[],'request_calls':[],'response_calls':[],'ble_handoff_calls':[],
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            seen_strings=set()
            def inspect(label,b):
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                em={mid:(code,kind,acc) for _,mid,code,kind,acc in enc}
                for s in strings:
                    if self._is_fw_string(s) and s not in seen_strings:
                        seen_strings.add(s);rep['firmware_strings'].append({'dex':label,'value':s})
                for m in methods:
                    cls,name=m.get('class'),m.get('name')
                    selected=(cls in (BASEAPI,HWM,HW,HWVER,BLEMAN) or cls.startswith(HWM[:-1]+'$') or cls.startswith(HW[:-1]+'$'))
                    if not selected:continue
                    code,kind,acc=em.get(m['idx'],(0,None,None))
                    if not code:continue
                    s=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                    pmap=self._param_map(b,code,m,acc)
                    s=self._rewrite_unknown_regs(s,pmap)
                    rel_strings=[]
                    for ev in s.get('trace',[]):
                        if ev.get('kind')=='string' and self._is_fw_string(ev.get('value')):rel_strings.append(ev.get('value'))
                    invokes=s.get('invokes',[])
                    row={'dex':label,'class':cls,'method':name,'method_idx':m['idx'],'proto':m.get('proto'),'kind':kind,'access_flags':acc,
                         'code_off':code,'incoming_registers':pmap,'strings':rel_strings,'invokes':invokes[:180],
                         'critical_field_writes':s.get('critical_field_writes',[])[:80],'returns':s.get('returns',[])[:40],
                         'command_templates':self._templates({'trace':s.get('trace',[])})}
                    if cls==BASEAPI:rep['base_api_methods'].append(row)
                    elif cls==HWM:rep['hardware_model_methods'].append(row)
                    elif cls==HW:rep['hardware_presenter_methods'].append(row)
                    elif cls==HWVER:rep['hardware_version_methods'].append(row)
                    elif cls.startswith(HWM[:-1]+'$') or cls.startswith(HW[:-1]+'$'):rep['callback_methods'].append(row)
                    for inv in invokes:
                        t=inv.get('target') or {};tc=t.get('class') or '';tm=t.get('method') or ''
                        call={'dex':label,'from_class':cls,'from_method':name,'unit':inv.get('unit'),'to_class':tc,'to_method':tm,'to_proto':t.get('proto'),'args':inv.get('args')}
                        low=(tc+' '+tm).lower()
                        if tc==BASEAPI or any(x in low for x in ('okhttp','retrofit','requestbody','download')):rep['request_calls'].append(call)
                        if cls.startswith(HWM[:-1]+'$') or cls.startswith(HW[:-1]+'$') or any(x in low for x in ('response','hardwareversion')):rep['response_calls'].append(call)
                        if tc==BLEMAN and tm=='H':rep['ble_handoff_calls'].append(call)
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
            for k,lim in [('base_api_methods',120),('hardware_model_methods',80),('hardware_presenter_methods',120),('hardware_version_methods',80),('callback_methods',160),('firmware_strings',500),('request_calls',200),('response_calls',300),('ble_handoff_calls',80)]:rep[k]=rep[k][:lim]
            rep['summary']={'base_api_methods':len(rep['base_api_methods']),'hardware_model_methods':len(rep['hardware_model_methods']),
                            'hardware_presenter_methods':len(rep['hardware_presenter_methods']),'hardware_version_methods':len(rep['hardware_version_methods']),
                            'callback_methods':len(rep['callback_methods']),'firmware_strings':len(rep['firmware_strings']),
                            'request_calls':len(rep['request_calls']),'response_calls':len(rep['response_calls']),'ble_handoff_calls':len(rep['ble_handoff_calls']),
                            'v180_proof':'HardwareUpdateModel builds currentFirmware + PREF_KEY_HARDWARE_VERSION + language request through BaseApi.i; HardwareUpdateModel.h(String) hands bytes to BleManager.H.',
                            'next':'Resolve exact BaseApi.i endpoint/transport and response HardwareVersion file metadata, then validate an official image header/checksum before enabling any OTA write.'}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v181');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-official-firmware-contract-v181.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.81 · falló: '+repr(err));return
            self.report={'official_firmware_contract_v181':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep['summary'];self.status.set(f"V1.81 LISTO · API={s['base_api_methods']} · request={s['request_calls']} · response={s['response_calls']} · handoff={s['ble_handoff_calls']} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV181(root);root.mainloop()
