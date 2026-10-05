import io, json, os, struct, zipfile
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, filedialog
import app as base
import app_v165 as v165
import app_v145 as v145

base.APP_VERSION="1.66.0"

def u16(b,o): return struct.unpack_from('<H',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def uleb(b,o):
    v=0; sh=0
    for _ in range(5):
        x=b[o]; o+=1; v|=(x&0x7f)<<sh
        if not x&0x80: return v,o
        sh+=7
    return v,o

class AppV166(v165.AppV165):
    def __init__(self,root):
        super().__init__(root); root.title('Reloj Lab V1.66')
        self._clean_v166(); self._install_v166()
        self.status.set('V1.66 lista · extrae clases, métodos, strings y llamadas del SDK Bluetrum FOTA sin escribir firmware.')

    def _clean_v166(self):
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

    def _install_v166(self):
        top=self.root.winfo_children()[0]
        self.v166_button=ttk.Button(top,text='EXTRAER PROTOCOLO BLUETRUM FOTA',command=self.extract_bluetrum)
        sib=top.winfo_children()
        try:self.v166_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except Exception:self.v166_button.place(x=8,y=8)

    @staticmethod
    def _dex_model(b):
        if len(b)<112 or not b.startswith(b'dex\n'): raise ValueError('DEX inválido')
        ssz,soff=u32(b,56),u32(b,60); tsz,toff=u32(b,64),u32(b,68); msz,moff=u32(b,88),u32(b,92); csz,coff=u32(b,96),u32(b,100)
        strings=[]
        for i in range(ssz):
            p=u32(b,soff+i*4); _,p=uleb(b,p); q=b.find(b'\0',p,min(len(b),p+20000)); q=len(b) if q<0 else q
            strings.append(b[p:q].decode('utf-8','replace'))
        types=[strings[u32(b,toff+i*4)] for i in range(tsz)]
        methods=[]
        for i in range(msz):
            ci=u16(b,moff+i*8); ni=u32(b,moff+i*8+4)
            methods.append({'idx':i,'class':types[ci] if ci<len(types) else str(ci),'name':strings[ni] if ni<len(strings) else str(ni)})
        classes=[]; encoded=[]
        for i in range(csz):
            o=coff+i*32; ci=u32(b,o); cdo=u32(b,o+24); desc=types[ci] if ci<len(types) else str(ci); classes.append(desc)
            if not cdo: continue
            try:
                p=cdo; sf,p=uleb(b,p); inf,p=uleb(b,p); dm,p=uleb(b,p); vm,p=uleb(b,p)
                for _ in range(sf+inf): _,p=uleb(b,p); _,p=uleb(b,p)
                mid=-1
                for _ in range(dm+vm):
                    d,p=uleb(b,p); mid+=d; acc,p=uleb(b,p); code,p=uleb(b,p)
                    if 0<=mid<len(methods): encoded.append((desc,mid,code))
            except Exception: pass
        return strings,types,methods,classes,encoded

    @staticmethod
    def _refs_in_code(b,code_off,strings,methods):
        out_s=[]; out_m=[]
        if not code_off or code_off+16>len(b): return out_s,out_m
        try:
            n=u32(b,code_off+12); p=code_off+16; units=[u16(b,p+i*2) for i in range(min(n,(len(b)-p)//2))]
        except Exception:return out_s,out_m
        for i,w in enumerate(units):
            op=w&0xff
            if op==0x1a and i+1<len(units):
                idx=units[i+1]
                if idx<len(strings): out_s.append(strings[idx])
            elif op==0x1b and i+2<len(units):
                idx=units[i+1]|(units[i+2]<<16)
                if idx<len(strings): out_s.append(strings[idx])
            elif op in (0x6e,0x6f,0x70,0x71,0x72,0x74,0x75,0x76,0x77,0x78) and i+1<len(units):
                idx=units[i+1]
                if idx<len(methods): out_m.append(methods[idx])
        def uniq(items,key):
            seen=set(); r=[]
            for x in items:
                k=key(x)
                if k not in seen: seen.add(k); r.append(x)
            return r
        return uniq(out_s,lambda x:x),uniq(out_m,lambda x:(x['class'],x['name']))

    def extract_bluetrum(self):
        ready,validation,vpath=self._ready_report()
        if not ready:
            self.status.set('V1.66 · falta validación BK3288.'); return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen: return
        self.face_guard_enabled=False; self.status.set('V1.66 · extrayendo protocolo Bluetrum FOTA…')
        def work():
            rep={'app_version':'1.66.0','generated_utc':datetime.now(timezone.utc).isoformat(),'goal':'extract_bluetrum_fota_classes_methods_strings_and_calls','validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,'dex':[],'bluetrum_classes':[],'bluetrum_methods':[],'external_calls_into_bluetrum':[],'protocol_strings':[],'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            def inspect(label,b):
                try: strings,types,methods,classes,enc=self._dex_model(b)
                except Exception as ex: rep['dex'].append({'name':label,'error':repr(ex)}); return
                targets={i for i,m in enumerate(methods) if m['class'].startswith('Lcom/bluetrum/fota/')}
                rep['dex'].append({'name':label,'size':len(b),'classes':len(classes),'methods':len(methods),'bluetrum_method_count':len(targets)})
                for c in classes:
                    if c.startswith('Lcom/bluetrum/fota/') and c not in rep['bluetrum_classes']: rep['bluetrum_classes'].append(c)
                for desc,mid,code in enc:
                    ss,mm=self._refs_in_code(b,code,strings,methods); me=methods[mid]
                    if mid in targets:
                        row={'dex':label,'class':me['class'],'method':me['name'],'code_off':code,'strings':[x for x in ss if len(x)<1200][:150],'calls':[{'class':x['class'],'method':x['name']} for x in mm[:150]]}
                        rep['bluetrum_methods'].append(row)
                        for x in row['strings']:
                            xl=x.lower()
                            if any(k in xl for k in ('fota','ota','dfu','firmware','uuid','service','characteristic','version','crc','packet','upgrade','bluetooth')) and x not in rep['protocol_strings']: rep['protocol_strings'].append(x)
                    else:
                        hits=[x for x in mm if x['idx'] in targets]
                        if hits: rep['external_calls_into_bluetrum'].append({'dex':label,'caller_class':me['class'],'caller_method':me['name'],'calls':[{'class':x['class'],'method':x['name']} for x in hits]})
            def inspect_apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')): inspect(name+'!'+n,z.read(n))
                except Exception: pass
            if zipfile.is_zipfile(chosen):
                with zipfile.ZipFile(chosen,'r') as z:
                    apks=[n for n in z.namelist() if n.lower().endswith('.apk')]
                    if apks:
                        for n in apks:
                            if 'com.wtwd.utrawatch' in n.lower() or 'base' in n.lower(): inspect_apk(n,z.read(n))
                    else:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')): inspect(n,z.read(n))
            else:
                with open(chosen,'rb') as f: inspect_apk(os.path.basename(chosen),f.read())
            rep['bluetrum_methods']=rep['bluetrum_methods'][:1500]; rep['external_calls_into_bluetrum']=rep['external_calls_into_bluetrum'][:1500]; rep['protocol_strings']=rep['protocol_strings'][:1500]
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v166'); os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-bluetrum-fota-v166.json'); rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f: json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err: self.status.set('V1.66 · falló: '+repr(err)); return
            self.report={'bluetrum_fota_v166':rep}; self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2); self.root.clipboard_clear(); self.root.clipboard_append(t); self.root.update_idletasks()
            except Exception: pass
            self.status.set(f"V1.66 LISTO · clases={len(rep['bluetrum_classes'])} · métodos={len(rep['bluetrum_methods'])} · callers={len(rep['external_calls_into_bluetrum'])} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk(); AppV166(root); root.mainloop()
