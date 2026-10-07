import io,json,os,zipfile,re,hashlib
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v223 as v223
import app_v199 as v199
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='2.24.0'
BASEMODEL='Lcom/wtwd/cocousa/ui/base/model/BaseModel;'
BASEAPI='Lcom/wtwd/cocousa/api/BaseApi;'
WELCOME='Lcom/wtwd/cocousa/ui/module/account/welcome/WelcomeModel;'
NEEDLES=('app-user/touristLogin','appDeviceId','watchhealth','app-halfwit')

class AppV224(v223.AppV223):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V2.24')
        self._clean_v224();self._install_v224();self._restore_location_button()
        self.status.set('V2.24 lista · cierra el cuerpo HTTP exacto del login invitado antes de tocar la red.')

    def _clean_v224(self):
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

    def _install_v224(self):
        top=self.root.winfo_children()[0]
        self.v224_button=ttk.Button(top,text='CERRAR CUERPO LOGIN',command=self.trace_body)
        sib=top.winfo_children()
        try:self.v224_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v224_button.place(x=8,y=8)

    @staticmethod
    def _ascii_strings(data,minlen=4):
        return [m.group().decode('utf-8','ignore') for m in re.finditer(rb'[\\x20-\\x7e]{%d,}'%minlen,data)]

    def trace_body(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V2.24 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V2.24 · trazando BaseModel.b + BaseApi.B + endpoint…')
        def work():
            rep={'app_version':'2.24.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'resolve_exact_guest_login_http_body_transform_and_BaseApi_B_endpoint_locally_before_first_network_request',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known_from_v223':{'android_to_appDeviceId_chain_complete':True,'guest_id_persistent':True,'BaseApi_method':'B'},
                 'methods':[],'raw_hits':[],'url_candidates':[],
                 'safety':{'network_requests':0,'guest_login_requests':0,'activation_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex_seen':0,'symbolized':0,'targets':0}
            def inspect(label,b):
                stats['dex_seen']+=1
                ss=self._ascii_strings(b)
                for s in ss:
                    sl=s.lower()
                    if any(n.lower() in sl for n in NEEDLES):
                        rep['raw_hits'].append({'dex':label,'text':s[:500]})
                    if ('http://' in sl or 'https://' in sl) and ('watchhealth' in sl or 'app-halfwit' in sl):
                        rep['url_candidates'].append(s[:500])
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                exact,err=v199.AppV199._exact_code_map(b,types)
                if err:rep.setdefault('exact_map_errors',[]).append({'dex':label,'error':err})
                for m in methods:
                    cls=m.get('class');name=m.get('name'); target=(cls==BASEMODEL and name=='b') or (cls==WELCOME and name=='e') or (cls==BASEAPI and name=='B')
                    if not target:continue
                    ex=exact.get(m.get('idx')) or {};code=ex.get('code_off');acc=ex.get('access_flags',0)
                    if not code:continue
                    stats['targets']+=1
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc);sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except Exception as ex2:rep.setdefault('symbolic_errors',[]).append({'class':cls,'method':name,'error':repr(ex2)});continue
                    rep['methods'].append({'dex':label,'class':cls,'method':name,'method_idx':m.get('idx'),'proto':m.get('proto'),'incoming_registers':pmap,'trace':(sym.get('trace') or [])[:4200]})
                    stats['symbolized']+=1
            def apk(name,data):
                with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                    dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                    for i,n in enumerate(dexes,1):
                        self._progress(f'V2.24 · DEX {i}/{len(dexes)} · {n}');inspect(name+'!'+n,z.read(n))
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
            rep['raw_hits']=sorted({x['dex']+'|'+x['text'] for x in rep['raw_hits']})
            rep['url_candidates']=sorted(set(rep['url_candidates']))
            txt=json.dumps(rep['methods'],ensure_ascii=False)
            rep['scan_stats']=stats
            rep['resolved']={
              'guest_endpoint_raw_present':any('app-user/touristLogin' in x for x in rep['raw_hits']),
              'base_url_candidate_present':any('app-halfwit' in x.lower() for x in rep['url_candidates']),
              'BaseModel_b_traced':any(r['class']==BASEMODEL and r['method']=='b' for r in rep['methods']),
              'WelcomeModel_e_traced':any(r['class']==WELCOME and r['method']=='e' for r in rep['methods']),
              'BaseApi_B_code_present':any(r['class']==BASEAPI and r['method']=='B' for r in rep['methods']),
              'requestbody_marker':('RequestBody' in txt),
              'network_gate':'NO_NETWORK_IN_THIS_VERSION',
              'next':'If BaseModel.b transform and endpoint/base URL are explicit, next version performs exactly one guest-login request, logs only HTTP status and token presence/length/fingerprint, then stops before activation/download/OTA.',
              'write_gate':'NO_DEVICE_WRITES'
            }
            rep['summary']={'targets':stats['targets'],'symbolized':stats['symbolized'],'guest_endpoint':rep['resolved']['guest_endpoint_raw_present'],'base_url':rep['resolved']['base_url_candidate_present'],'body_traced':rep['resolved']['BaseModel_b_traced']}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v224');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-login-body-v224.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V2.24 · falló: '+repr(err));return
            self.report={'utrawatch_login_body_v224':rep};self.show()
            try:self.root.clipboard_clear();self.root.clipboard_append(json.dumps(rep,ensure_ascii=False,indent=2));self.root.update_idletasks()
            except:pass
            s=rep.get('summary') or {};self.status.set(f"V2.24 LISTO · endpoint={s.get('guest_endpoint')} · base={s.get('base_url')} · body={s.get('body_traced')} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV224(root);root.mainloop()
