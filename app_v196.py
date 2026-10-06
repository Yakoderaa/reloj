import json,os,locale,urllib.request,urllib.error
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk
import app as base
import app_v195 as v195
import app_v145 as v145

base.APP_VERSION='1.96.0'
BASE_URL='https://wr.watchhealth.com.cn/app-halfwit/'
GUEST_ENDPOINT='app-user/touristLogin'
BIND_ENDPOINT='app-device/userBindDevice'
FW_ENDPOINT='app-device/checkForUpdate'

class AppV196(v195.AppV195):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.96')
        self._clean_v196();self._install_v196();self._restore_location_button()
        self.status.set('V1.96 lista · sesión invitado → vinculación oficial → consulta de firmware. Sin descarga ni OTA.')

    def _clean_v196(self):
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

    def _install_v196(self):
        top=self.root.winfo_children()[0]
        self.v196_button=ttk.Button(top,text='VINCULAR RELOJ + CONSULTAR FIRMWARE',command=self.bind_and_query)
        sib=top.winfo_children()
        try:self.v196_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v196_button.place(x=8,y=8)

    @staticmethod
    def _lang():
        try:return ((locale.getdefaultlocale()[0] or 'es').split('_')[0].lower() or 'es')
        except:return 'es'

    def _device_id_path(self):
        return os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','utrawatch-guest-device-id.txt')

    def _guest_device_id(self):
        p=self._device_id_path()
        try:
            v=open(p,'r',encoding='utf-8').read().strip()
            if v:return v
        except:pass
        return None

    @staticmethod
    def _request_json(url,body,headers=None,timeout=20):
        raw=json.dumps(body,separators=(',',':'),ensure_ascii=False).encode('utf-8')
        h={'Content-Type':'application/json','Accept':'application/json','User-Agent':'UtraWatch/RelojLab-1.96'}
        if headers:h.update(headers)
        req=urllib.request.Request(url,data=raw,headers=h,method='POST')
        shown_headers={k:('***' if k.lower()=='access-token' else v) for k,v in h.items()}
        out={'url':url,'method':'POST','request_body':body,'request_headers':shown_headers}
        try:
            with urllib.request.urlopen(req,timeout=timeout) as resp:
                data=resp.read(2*1024*1024)
                out['http_status']=getattr(resp,'status',None)
                out['content_type']=resp.headers.get('Content-Type')
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
    def _session_values(obj):
        token=None;user_id=None
        if isinstance(obj,dict):
            for k,v in obj.items():
                lk=str(k).lower()
                if lk=='token' and isinstance(v,str) and v.strip():token=v.strip()
                elif lk=='userid' and isinstance(v,(int,float,str)) and str(v).strip():user_id=v
            if token is None or user_id is None:
                for v in obj.values():
                    t,u=AppV196._session_values(v)
                    token=token or t;user_id=user_id if user_id is not None else u
        elif isinstance(obj,list):
            for v in obj:
                t,u=AppV196._session_values(v)
                token=token or t;user_id=user_id if user_id is not None else u
        return token,user_id

    @staticmethod
    def _redact_attempt(attempt,token=None):
        out=dict(attempt or {})
        def redact(x):
            if isinstance(x,dict):return {k:('***REDACTED***' if str(k).lower()=='token' else redact(v)) for k,v in x.items()}
            if isinstance(x,list):return [redact(v) for v in x]
            return x
        if 'response_json' in out:out['response_json']=redact(out['response_json'])
        if token and isinstance(out.get('response_text'),str):out['response_text']=out['response_text'].replace(token,'***REDACTED***')
        return out

    def bind_and_query(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V1.96 · falta validación BK3288.');return
        selected=self.selected or {}
        address=selected.get('address') or getattr(selected.get('device'),'address',None)
        name=selected.get('name') or getattr(selected.get('device'),'name',None)
        if not address or not name:
            self.status.set('V1.96 · primero usá Buscar relojes y seleccioná el reloj exacto.');return
        app_device_id=self._guest_device_id()
        if not app_device_id:
            self.status.set('V1.96 · falta el identificador invitado persistente; ejecutá V1.91 una vez o reinstalá conservando LocalAppData.');return
        self.face_guard_enabled=False
        self.status.set('V1.96 · creando sesión invitado oficial…')
        def work():
            guest=self._request_json(BASE_URL+GUEST_ENDPOINT,{'appDeviceId':app_device_id})
            token,user_id=self._session_values(guest.get('response_json'))
            bind=None;fw=None
            if token and user_id is not None:
                self._progress('V1.96 · sesión OK · vinculando el reloj seleccionado…')
                bind_body={'macAddress':str(address),'name':str(name),'userId':user_id}
                bind=self._request_json(BASE_URL+BIND_ENDPOINT,bind_body,{'access-token':token})
                self._progress('V1.96 · vinculación respondida · consultando checkForUpdate…')
                firmware=str((validation.get('observed') or {}).get('firmware',{}).get('text') or v145.EXPECTED.get('firmware') or '0.0.1')
                fw=self._request_json(BASE_URL+FW_ENDPOINT,{'currentFirmware':firmware,'language':self._lang()},{'access-token':token})
            rep={'app_version':'1.96.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'create_guest_session_bind_the_exact_selected_watch_once_then_query_firmware_metadata_without_firmware_download_or_ota',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,
                 'selected_watch':{'address':str(address),'name':str(name)},
                 'contract':{'guest_endpoint':GUEST_ENDPOINT,'bind_endpoint':BIND_ENDPOINT,'firmware_endpoint':FW_ENDPOINT,'bind_body_keys':['macAddress','name','userId']},
                 'guest_attempt':self._redact_attempt(guest,token),
                 'bind_attempt':self._redact_attempt(bind,token) if bind else None,
                 'firmware_attempt':self._redact_attempt(fw,token) if fw else None,
                 'resolved':{'guest_session_succeeded':bool(token and user_id is not None),
                             'user_id_received':user_id is not None,
                             'bind_http_status':bind.get('http_status') if bind else None,
                             'bind_response_json':bind.get('response_json') if bind else None,
                             'firmware_http_status':fw.get('http_status') if fw else None,
                             'firmware_response_json':fw.get('response_json') if fw else None,
                             'next':'If firmware metadata now contains HardwareVersion/file metadata, validate the official file before any OTA. If the server still blocks, use the exact bind/check responses to refine only the required registration step.',
                             'write_gate':'KEEP_OTA_DISABLED_UNTIL_OFFICIAL_FIRMWARE_FILE_VALIDATION_SUCCEEDS'},
                 'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':1+(1 if bind else 0)+(1 if fw else 0),'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v196');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-bind-check-v196.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.96 · falló: '+repr(err));return
            self.report={'utrawatch_bind_check_v196':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            r=rep.get('resolved') or {}
            self.status.set(f"V1.96 LISTO · bind HTTP={r.get('bind_http_status')} · firmware HTTP={r.get('firmware_http_status')} · OTA=0 · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV196(root);root.mainloop()
