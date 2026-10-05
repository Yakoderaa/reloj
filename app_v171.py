import io, json, os, zipfile
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, filedialog
import app as base
import app_v170 as v170
import app_v166 as v166
import app_v145 as v145

base.APP_VERSION='1.71.0'
BASE_API='Lcom/wtwd/cocousa/api/BaseApi;'
FOCUS=('i','y')

class AppV171(v170.AppV170):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.71')
        self._clean_v171(); self._install_v171()
        self.status.set('V1.71 lista · extrae parámetros Retrofit exactos de check/download y candidatos de URL base. Sin red ni escrituras OTA.')

    def _clean_v171(self):
        keep=('buscar relojes','buscar dispositivos','buscar disp','buscar actualización','buscar actualizacion','buscar actualizaciones')
        def walk(w):
            for c in list(w.winfo_children()):
                try:
                    if isinstance(c,(ttk.Button,tk.Button)):
                        t=str(c.cget('text') or '').lower()
                        if not any(x in t for x in keep):
                            try:c.pack_forget()
                            except Exception:pass
                            try:c.grid_remove()
                            except Exception:pass
                            try:c.place_forget()
                            except Exception:pass
                    else: walk(c)
                except Exception: pass
        walk(self.root)

    def _install_v171(self):
        top=self.root.winfo_children()[0]
        self.v171_button=ttk.Button(top,text='EXTRAER CONTRATO HTTP EXACTO',command=self.extract_http_contract)
        sib=top.winfo_children()
        try:self.v171_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except Exception:self.v171_button.place(x=8,y=8)

    @classmethod
    def _all_annotations(cls,b,strings,types,methods):
        methods_out={}; params_out={}
        csz,coff=v166.u32(b,96),v166.u32(b,100)
        for i in range(csz):
            o=coff+i*32
            try: ad=v166.u32(b,o+20)
            except Exception: continue
            if not ad or ad+16>len(b): continue
            try:
                _,fs,ms,ps=(v166.u32(b,ad+j*4) for j in range(4)); p=ad+16+fs*8
                for _ in range(ms):
                    mid=v166.u32(b,p); aset=v166.u32(b,p+4); p+=8
                    methods_out[mid]=cls._annotation_set(b,aset,strings,types)
                for _ in range(ps):
                    mid=v166.u32(b,p); roff=v166.u32(b,p+4); p+=8
                    arr=[]
                    if roff and roff+4<=len(b):
                        n=v166.u32(b,roff)
                        for j in range(min(n,100)):
                            so=v166.u32(b,roff+4+j*4)
                            arr.append(cls._annotation_set(b,so,strings,types) if so else [])
                    params_out[mid]=arr
            except Exception: continue
        return methods_out,params_out

    def extract_http_contract(self):
        ready,validation,vpath=self._ready_report()
        if not ready:
            self.status.set('V1.71 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.71 · extrayendo contrato HTTP exacto de firmware…')
        def work():
            rep={'app_version':'1.71.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'extract_exact_retrofit_parameter_annotations_base_url_candidates_and_download_url_contract_without_network_or_ota_writes',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'focus_methods':[],'base_url_candidates':[],'firmware_strings':[],'hardware_version_fields':[],
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            seen_urls=set();seen_fw=set()
            def inspect(label,b):
                try: strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex: rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                ma,pa=self._all_annotations(b,strings,types,methods)
                for f in fields:
                    if f['class']=='Lcom/wtwd/cocousa/entity/device/HardwareVersion;': rep['hardware_version_fields'].append(f)
                for s in strings:
                    sl=s.lower()
                    if ('http://' in sl or 'https://' in sl) and len(s)<1000:
                        if s not in seen_urls: seen_urls.add(s);rep['base_url_candidates'].append(s)
                    if any(k in sl for k in ('checkforupdate','firmware','upgrade','.fot','.img','.bin','ota/','filepath')) and len(s)<1000:
                        if s not in seen_fw: seen_fw.add(s);rep['firmware_strings'].append(s)
                encmap={mid:(code,kind,acc) for _,mid,code,kind,acc in enc}
                for m in methods:
                    if m['class']==BASE_API and m['name'] in FOCUS:
                        code,kind,acc=encmap.get(m['idx'],(0,None,None)); d=self._details(b,code,strings,methods,fields)
                        rep['focus_methods'].append({'dex':label,'class':m['class'],'method':m['name'],'method_idx':m['idx'],'proto':m.get('proto'),'kind':kind,'access_flags':acc,'method_annotations':ma.get(m['idx'],[]),'parameter_annotations':pa.get(m['idx'],[]),**d})
            def inspect_apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')):inspect(name+'!'+n,z.read(n))
                except Exception as ex:rep.setdefault('errors',[]).append({'apk':name,'error':repr(ex)})
            if zipfile.is_zipfile(chosen):
                with zipfile.ZipFile(chosen,'r') as z:
                    apks=[n for n in z.namelist() if n.lower().endswith('.apk')]
                    if apks:
                        for n in apks:
                            if 'com.wtwd.utrawatch' in n.lower() or 'base' in n.lower():inspect_apk(n,z.read(n))
                    else:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')):inspect(n,z.read(n))
            else:
                with open(chosen,'rb') as f:inspect_apk(os.path.basename(chosen),f.read())
            rep['base_url_candidates']=rep['base_url_candidates'][:500]
            rep['firmware_strings']=rep['firmware_strings'][:1000]
            rep['focus_methods']=rep['focus_methods'][:20]
            rep['hardware_version_fields']=rep['hardware_version_fields'][:100]
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v171');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-http-contract-v171.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.71 · falló: '+repr(err));return
            self.report={'http_contract_v171':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except Exception:pass
            self.status.set(f"V1.71 LISTO · foco={len(rep['focus_methods'])} · URLs={len(rep['base_url_candidates'])} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV171(root);root.mainloop()
