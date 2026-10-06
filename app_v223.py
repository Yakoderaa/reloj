import io,json,os,zipfile,secrets,hashlib
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v222 as v222
import app_v199 as v199
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='2.23.0'
BASEAPI='Lcom/wtwd/cocousa/api/BaseApi;'
WELCOME='Lcom/wtwd/cocousa/ui/module/account/welcome/WelcomeFragment;'
WELCOMEMODEL='Lcom/wtwd/cocousa/ui/module/account/welcome/WelcomeModel;'

class AppV223(v222.AppV222):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V2.23')
        self._clean_v223();self._install_v223();self._restore_location_button()
        self.status.set('V2.23 lista · cierra el contrato exacto de touristLogin y prepara un ID invitado nuevo. Sin red ni OTA.')

    def _clean_v223(self):
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

    def _install_v223(self):
        top=self.root.winfo_children()[0]
        self.v223_button=ttk.Button(top,text='CERRAR TOURISTLOGIN EXACTO',command=self.trace_guest)
        sib=top.winfo_children()
        try:self.v223_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v223_button.place(x=8,y=8)

    @staticmethod
    def _folder():
        p=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v223');os.makedirs(p,exist_ok=True);return p

    @classmethod
    def _guest_preview(cls):
        path=os.path.join(cls._folder(),'guest-device-id.json')
        created=False
        try:
            if os.path.exists(path):
                with open(path,'r',encoding='utf-8') as f:o=json.load(f)
                v=str(o.get('appDeviceId') or '').strip().lower()
                if len(v)==16 and all(c in '0123456789abcdef' for c in v):
                    return {'created_now':False,'path':path,'length':16,'format':'16 lowercase hex','fingerprint_sha256_12':hashlib.sha256(v.encode()).hexdigest()[:12],'raw_logged':False}
        except:pass
        v=secrets.token_hex(8);created=True
        with open(path,'w',encoding='utf-8') as f:json.dump({'appDeviceId':v,'created_utc':datetime.now(timezone.utc).isoformat(),'source':'fresh RelojLab guest identifier; no phone identifier reused'},f,ensure_ascii=False,indent=2)
        return {'created_now':created,'path':path,'length':16,'format':'16 lowercase hex','fingerprint_sha256_12':hashlib.sha256(v.encode()).hexdigest()[:12],'raw_logged':False}

    def trace_guest(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V2.23 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        try:self.root.clipboard_clear();self.root.update_idletasks()
        except:pass
        self.face_guard_enabled=False
        self.status.set('V2.23 · resolviendo BaseApi.B + WelcomeFragment → WelcomeModel.e…')
        def work():
            rep={'app_version':'2.23.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'resolve_exact_touristLogin_retrofit_contract_and_android_id_to_appDeviceId_chain_locally',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known_from_v222':{'appDeviceId_source':'WelcomeFragment.appIMEi <- Settings.Secure android_id','call':'WelcomeFragment.onClick -> WelcomeModel.e(appIMEi)','body':'WelcomeModel.e puts appDeviceId=param0'},
                 'guest_id_preview':self._guest_preview(),'methods':[],
                 'safety':{'network_requests':0,'guest_login_requests':0,'activation_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex_seen':0,'target_methods':0,'symbolized':0}
            def inspect(label,b):
                stats['dex_seen']+=1
                if b'touristLogin' not in b and b'WelcomeFragment' not in b:return
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                exact,err=v199.AppV199._exact_code_map(b,types)
                if err:rep.setdefault('exact_map_errors',[]).append({'dex':label,'error':err})
                for m in methods:
                    cls=m.get('class');name=m.get('name');ex=exact.get(m.get('idx')) or {};code=ex.get('code_off');acc=ex.get('access_flags',0)
                    if not code:continue
                    target=(cls==BASEAPI and name=='B') or (cls==WELCOME and name in ('N1','onClick')) or (cls==WELCOMEMODEL and name=='e')
                    if not target:continue
                    stats['target_methods']+=1
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc);sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except Exception as ex2:rep.setdefault('symbolic_errors',[]).append({'class':cls,'method':name,'error':repr(ex2)});continue
                    rep['methods'].append({'dex':label,'class':cls,'method':name,'method_idx':m.get('idx'),'proto':m.get('proto'),'incoming_registers':pmap,'trace':(sym.get('trace') or [])[:3600]})
                    stats['symbolized']+=1
            def apk(name,data):
                with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                    for n in z.namelist():
                        if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')):inspect(name+'!'+n,z.read(n))
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
            txt=json.dumps(rep['methods'],ensure_ascii=False)
            rep['scan_stats']=stats
            rep['resolved']={'touristLogin_literal_present':'touristLogin' in txt,'appDeviceId_present':'appDeviceId' in txt,'android_id_present':'android_id' in txt,
                             'android_to_appDeviceId_chain_complete':('android_id' in txt and 'appIMEi' in txt and 'appDeviceId' in txt),
                             'network_gate':'NO_NETWORK_IN_THIS_VERSION','next':'If BaseApi.B and the android_id -> appIMEi -> appDeviceId chain are both explicit, the next version can perform exactly one guest-login request with this fresh persistent guest identifier and stop before activation/download/OTA.','write_gate':'NO_DEVICE_WRITES'}
            rep['summary']={'target_methods':stats['target_methods'],'symbolized':stats['symbolized'],'chain_complete':rep['resolved']['android_to_appDeviceId_chain_complete']}
            out=os.path.join(self._folder(),'utrawatch-touristlogin-contract-v223.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V2.23 · falló: '+repr(err));return
            self.report={'utrawatch_touristlogin_contract_v223':rep};self.show()
            try:self.root.clipboard_clear();self.root.clipboard_append(json.dumps(rep,ensure_ascii=False,indent=2));self.root.update_idletasks()
            except:pass
            s=rep.get('summary') or {};self.status.set(f"V2.23 LISTO · métodos={s.get('target_methods')} · chain={s.get('chain_complete')} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV223(root);root.mainloop()
