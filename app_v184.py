import json,os,locale,urllib.request,urllib.error
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,simpledialog
import app as base
import app_v183 as v183
import app_v145 as v145

base.APP_VERSION='1.84.0'
BASE_URL='https://wr.watchhealth.com.cn/app-halfwit/'
ENDPOINT='app-device/checkForUpdate'

class AppV184(v183.AppV183):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.84')
        self._clean_v184();self._install_v184()
        self.status.set('V1.84 lista · consulta oficial de firmware con el contrato exacto de UtraWatch. OTA bloqueado.')

    def _clean_v184(self):
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

    def _install_v184(self):
        top=self.root.winfo_children()[0]
        self.v184_button=ttk.Button(top,text='CONSULTAR FIRMWARE OFICIAL',command=self.query_official_firmware)
        sib=top.winfo_children()
        try:self.v184_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v184_button.place(x=8,y=8)

    @staticmethod
    def _lang():
        try:
            x=(locale.getdefaultlocale()[0] or 'es').split('_')[0].lower()
            return x or 'es'
        except:return 'es'

    def query_official_firmware(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V1.84 · falta validación BK3288.');return
        token=simpledialog.askstring('UtraWatch access-token','Pegá el access-token oficial de UtraWatch.\nSe usará sólo para consultar checkForUpdate.',show='*',parent=self.root)
        if token is None:return
        token=token.strip()
        self.face_guard_enabled=False
        self.status.set('V1.84 · consultando metadata oficial…')
        def work():
            firmware=str((validation.get('observed') or {}).get('firmware',{}).get('text') or v145.EXPECTED.get('firmware') or '0.0.1')
            body={'currentFirmware':firmware,'language':self._lang()}
            raw=json.dumps(body,separators=(',',':'),ensure_ascii=False).encode('utf-8')
            headers={'Content-Type':'application/json','Accept':'application/json','User-Agent':'UtraWatch/RelojLab-1.84','access-token':token}
            req=urllib.request.Request(BASE_URL+ENDPOINT,data=raw,headers=headers,method='POST')
            attempt={'url':BASE_URL+ENDPOINT,'method':'POST','token_present':bool(token),'request_body':body}
            try:
                with urllib.request.urlopen(req,timeout=20) as resp:
                    data=resp.read(1024*1024)
                    attempt['http_status']=getattr(resp,'status',None)
                    attempt['content_type']=resp.headers.get('Content-Type')
                    attempt['response_text']=data.decode('utf-8','replace')
                    try:attempt['response_json']=json.loads(attempt['response_text'])
                    except:pass
            except urllib.error.HTTPError as ex:
                attempt['http_status']=ex.code
                try:attempt['response_text']=ex.read(1024*1024).decode('utf-8','replace')
                except:attempt['response_text']=repr(ex)
                try:attempt['response_json']=json.loads(attempt['response_text'])
                except:pass
            except Exception as ex:attempt['error']=repr(ex)
            ok=bool(attempt.get('http_status') and 200<=attempt['http_status']<300)
            rep={'app_version':'1.84.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'perform_authenticated_official_firmware_metadata_request_using_exact_v183_retrofit_contract_without_firmware_download_or_ota_write',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,
                 'contract':{'base_url':BASE_URL,'endpoint':ENDPOINT,'method':'POST','header':'access-token','body_keys':['currentFirmware','language']},
                 'attempt':attempt,
                 'resolved':{'request_succeeded':ok,'http_status':attempt.get('http_status'),'response_json':attempt.get('response_json'),
                             'next':'Parse official HardwareVersion response, identify returned firmware file, then validate size/hash/header before download or OTA.' if ok else 'Use the HTTP/body result to refine authentication or request framing.'},
                 'safety':{'network_requests':1,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v184');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-official-request-v184.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.84 · falló: '+repr(err));return
            self.report={'utrawatch_official_request_v184':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            r=rep['resolved'];self.status.set(f"V1.84 LISTO · HTTP={r.get('http_status')} · éxito={r.get('request_succeeded')} · OTA=0 · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV184(root);root.mainloop()
