import json,os,locale,urllib.request,urllib.error,uuid
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk
import app as base
import app_v190 as v190
import app_v145 as v145

base.APP_VERSION='1.91.0'
BASE_URL='https://wr.watchhealth.com.cn/app-halfwit/'
GUEST_ENDPOINT='app-user/touristLogin'
FW_ENDPOINT='app-device/checkForUpdate'

class AppV191(v190.AppV190):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.91')
        self._clean_v191();self._install_v191();self._restore_location_button()
        self.status.set('V1.91 lista · crea sesión invitado oficial y consulta metadata de firmware. Sin descarga ni OTA.')

    def _clean_v191(self):
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

    def _install_v191(self):
        top=self.root.winfo_children()[0]
        self.v191_button=ttk.Button(top,text='CREAR SESIÓN + CONSULTAR FIRMWARE',command=self.query_guest_firmware)
        sib=top.winfo_children()
        try:self.v191_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v191_button.place(x=8,y=8)

    @staticmethod
    def _lang():
        try:
            x=(locale.getdefaultlocale()[0] or 'es').split('_')[0].lower()
            return x or 'es'
        except:return 'es'

    def _device_id_path(self):
        return os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','utrawatch-guest-device-id.txt')

    def _stable_guest_device_id(self):
        p=self._device_id_path()
        try:
            v=open(p,'r',encoding='utf-8').read().strip()
            if len(v)>=8:return v
        except:pass
        # Android's ANDROID_ID is represented as a stable hex-like identifier.
        # Reloj Lab creates its own persistent appDeviceId for the official guest endpoint;
        # it does not read identifiers or credentials from another app/device.
        v=uuid.uuid4().hex[:16]
        os.makedirs(os.path.dirname(p),exist_ok=True)
        with open(p,'w',encoding='utf-8') as f:f.write(v)
        return v

    @staticmethod
    def _request_json(url,body,headers=None,timeout=20):
        raw=json.dumps(body,separators=(',',':'),ensure_ascii=False).encode('utf-8')
        h={'Content-Type':'application/json','Accept':'application/json','User-Agent':'UtraWatch/RelojLab-1.91'}
        if headers:h.update(headers)
        req=urllib.request.Request(url,data=raw,headers=h,method='POST')
        out={'url':url,'method':'POST','request_body':body,'request_headers':{k:('***' if k.lower()=='access-token' else v) for k,v in h.items()}}
        try:
            with urllib.request.urlopen(req,timeout=timeout) as resp:
                data=resp.read(2*1024*1024)
                out['http_status']=getattr(resp,'status',None);out['content_type']=resp.headers.get('Content-Type')
                out['response_text']=data.decode('utf-8','replace')
        except urllib.error.HTTPError as ex:
            out['http_status']=ex.code
            try:out['response_text']=ex.read(2*1024*1024).decode('utf-8','replace')
            except:out['response_text']=repr(ex)
        except Exception as ex:
            out['error']=repr(ex);return out
        try:out['response_json']=json.loads(out.get('response_text') or '')
        except:pass
        return out

    @staticmethod
    def _find_token(obj):
        if isinstance(obj,dict):
            for k,v in obj.items():
                if str(k).lower()=='token' and isinstance(v,str) and v.strip():return v.strip()
            for v in obj.values():
                t=AppV191._find_token(v)
                if t:return t
        elif isinstance(obj,list):
            for v in obj:
                t=AppV191._find_token(v)
                if t:return t
        return None

    def query_guest_firmware(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V1.91 · falta validación BK3288.');return
        self.face_guard_enabled=False
        self.status.set('V1.91 · creando sesión invitado oficial…')
        def work():
            app_device_id=self._stable_guest_device_id()
            guest_body={'appDeviceId':app_device_id}
            guest=self._request_json(BASE_URL+GUEST_ENDPOINT,guest_body)
            token=self._find_token(guest.get('response_json'))
            firmware=str((validation.get('observed') or {}).get('firmware',{}).get('text') or v145.EXPECTED.get('firmware') or '0.0.1')
            fw=None
            if token:
                self._progress('V1.91 · sesión invitado OK · consultando checkForUpdate…')
                fw_body={'currentFirmware':firmware,'language':self._lang()}
                fw=self._request_json(BASE_URL+FW_ENDPOINT,fw_body,{'access-token':token})
            guest_ok=bool(guest.get('http_status') and 200<=guest['http_status']<300 and token)
            fw_ok=bool(fw and fw.get('http_status') and 200<=fw['http_status']<300)
            safe_guest=dict(guest)
            if 'response_json' in safe_guest:
                # Keep response structure for diagnostics but never persist an active token.
                def redact(x):
                    if isinstance(x,dict):return {k:('***REDACTED***' if str(k).lower()=='token' else redact(v)) for k,v in x.items()}
                    if isinstance(x,list):return [redact(v) for v in x]
                    return x
                safe_guest['response_json']=redact(safe_guest['response_json'])
            if token and isinstance(safe_guest.get('response_text'),str):safe_guest['response_text']=safe_guest['response_text'].replace(token,'***REDACTED***')
            rep={'app_version':'1.91.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'create_official_utrawatch_guest_session_then_query_official_firmware_metadata_without_firmware_download_or_ota_write',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,
                 'contract':{'base_url':BASE_URL,'guest_endpoint':GUEST_ENDPOINT,'guest_body_keys':['appDeviceId'],'firmware_endpoint':FW_ENDPOINT,'firmware_body_keys':['currentFirmware','language'],'firmware_header':'access-token'},
                 'identity':{'source':'Reloj Lab persistent guest identifier matching appDeviceId format','appDeviceId':app_device_id,'path':self._device_id_path()},
                 'guest_attempt':safe_guest,'firmware_attempt':fw,
                 'resolved':{'guest_session_succeeded':guest_ok,'guest_http_status':guest.get('http_status'),'token_received':bool(token),
                             'firmware_metadata_succeeded':fw_ok,'firmware_http_status':fw.get('http_status') if fw else None,
                             'firmware_response_json':fw.get('response_json') if fw else None,
                             'next':'Parse returned HardwareVersion/file metadata and validate the official firmware file size/hash/header before any OTA write.' if fw_ok else 'Use the guest/login and firmware HTTP responses to refine exact server framing while keeping OTA disabled.',
                             'write_gate':'KEEP_OTA_DISABLED_UNTIL_OFFICIAL_FIRMWARE_METADATA_AND_FILE_VALIDATION_SUCCEED'},
                 'safety':{'network_requests':1+(1 if token else 0),'credential_collection':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v191');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-guest-firmware-v191.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.91 · falló: '+repr(err));return
            self.report={'utrawatch_guest_firmware_v191':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            r=rep['resolved'];self.status.set(f"V1.91 LISTO · guest HTTP={r.get('guest_http_status')} · firmware HTTP={r.get('firmware_http_status')} · metadata={r.get('firmware_metadata_succeeded')} · OTA=0 · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV191(root);root.mainloop()
