import io,json,os,zipfile,struct
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v182 as v182
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='1.83.0'
BASEAPI=v182.BASEAPI
HWM=v182.HWM
HW=v182.HW
HWVER=v182.HWVER

class AppV183(v182.AppV182):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.83')
        self._clean_v183();self._install_v183()
        self.status.set('V1.83 lista · lee anotaciones Retrofit reales y reconstruye el contrato oficial de checkForUpdate. Sin red ni OTA.')

    def _clean_v183(self):
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

    def _install_v183(self):
        top=self.root.winfo_children()[0]
        self.v183_button=ttk.Button(top,text='RECONSTRUIR LLAMADA OFICIAL',command=self.resolve_retrofit_contract)
        sib=top.winfo_children()
        try:self.v183_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v183_button.place(x=8,y=8)

    @staticmethod
    def _u32(b,o):
        return struct.unpack_from('<I',b,o)[0]

    @staticmethod
    def _uleb(b,o):
        val=0;shift=0
        for _ in range(5):
            x=b[o];o+=1;val|=(x&0x7f)<<shift
            if not (x&0x80):return val,o
            shift+=7
        return val,o

    @classmethod
    def _encoded_value(cls,b,o,strings,types,fields,methods):
        head=b[o];o+=1;vt=head&0x1f;arg=head>>5
        def raw(n):
            nonlocal o
            v=0
            for i in range(n):v|=b[o+i]<<(8*i)
            o+=n;return v
        if vt==0x1e:return None,o
        if vt==0x1f:return bool(arg),o
        if vt==0x1c:
            n,o=cls._uleb(b,o);arr=[]
            for _ in range(n):
                v,o=cls._encoded_value(b,o,strings,types,fields,methods);arr.append(v)
            return arr,o
        if vt==0x1d:
            a,o=cls._encoded_annotation(b,o,strings,types,fields,methods);return a,o
        n=arg+1;idx=raw(n)
        if vt==0x17:return strings[idx] if idx<len(strings) else {'string_idx':idx},o
        if vt==0x18:return types[idx] if idx<len(types) else {'type_idx':idx},o
        if vt in (0x19,0x1b):return fields[idx] if idx<len(fields) else {'field_idx':idx},o
        if vt==0x1a:return methods[idx] if idx<len(methods) else {'method_idx':idx},o
        return idx,o

    @classmethod
    def _encoded_annotation(cls,b,o,strings,types,fields,methods):
        ti,o=cls._uleb(b,o);n,o=cls._uleb(b,o);els={}
        for _ in range(n):
            ni,o=cls._uleb(b,o);name=strings[ni] if ni<len(strings) else str(ni)
            val,o=cls._encoded_value(b,o,strings,types,fields,methods);els[name]=val
        return {'type':types[ti] if ti<len(types) else str(ti),'elements':els},o

    @classmethod
    def _annotation_set(cls,b,off,strings,types,fields,methods):
        if not off or off+4>len(b):return []
        out=[]
        try:
            n=cls._u32(b,off);p=off+4
            for i in range(n):
                ao=cls._u32(b,p+i*4)
                if ao and ao<len(b):
                    ann,_=cls._encoded_annotation(b,ao+1,strings,types,fields,methods)
                    ann['visibility']=b[ao];out.append(ann)
        except Exception as ex:return [{'decode_error':repr(ex),'offset':off}]
        return out

    @classmethod
    def _retrofit_annotations(cls,b,strings,types,fields,methods,target_class,target_method=None):
        out={'class_annotations':[],'field_annotations':[],'method_annotations':[],'parameter_annotations':[],'errors':[]}
        try:
            csz=cls._u32(b,0x60);coff=cls._u32(b,0x64)
            for i in range(csz):
                q=coff+i*32;ci=cls._u32(b,q);ctype=types[ci] if ci<len(types) else None
                if ctype!=target_class:continue
                aoff=cls._u32(b,q+20)
                if not aoff:return out
                class_off=cls._u32(b,aoff);fsz=cls._u32(b,aoff+4);msz=cls._u32(b,aoff+8);psz=cls._u32(b,aoff+12)
                if class_off:out['class_annotations']=cls._annotation_set(b,class_off,strings,types,fields,methods)
                p=aoff+16
                for _ in range(fsz):
                    fi=cls._u32(b,p);so=cls._u32(b,p+4);p+=8
                    f=fields[fi] if fi<len(fields) else {'idx':fi}
                    out['field_annotations'].append({'field':f,'annotations':cls._annotation_set(b,so,strings,types,fields,methods)})
                for _ in range(msz):
                    mi=cls._u32(b,p);so=cls._u32(b,p+4);p+=8
                    m=methods[mi] if mi<len(methods) else {'idx':mi}
                    if target_method is None or m.get('name')==target_method:
                        out['method_annotations'].append({'method':m,'annotations':cls._annotation_set(b,so,strings,types,fields,methods)})
                for _ in range(psz):
                    mi=cls._u32(b,p);ro=cls._u32(b,p+4);p+=8
                    m=methods[mi] if mi<len(methods) else {'idx':mi}
                    if target_method is not None and m.get('name')!=target_method:continue
                    sets=[]
                    if ro:
                        cnt=cls._u32(b,ro);rp=ro+4
                        for j in range(cnt):
                            so=cls._u32(b,rp+j*4);sets.append({'parameter_index':j,'annotations':cls._annotation_set(b,so,strings,types,fields,methods)})
                    out['parameter_annotations'].append({'method':m,'parameters':sets})
                return out
        except Exception as ex:out['errors'].append(repr(ex))
        return out

    @staticmethod
    def _find_http_annotations(rows):
        hits=[]
        for row in rows:
            for a in row.get('annotations',[]):
                t=str(a.get('type','')).lower();e=a.get('elements',{})
                if 'retrofit2/http/' in t or any(x in t for x in ('/post;','/get;','/body;','/field;','/query;','/header;')):
                    hits.append({'method':row.get('method'),'annotation':a})
        return hits

    def resolve_retrofit_contract(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V1.83 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.83 · leyendo @POST/@GET, parámetros Retrofit y mapeo exacto de HardwareVersion…')
        def work():
            rep={'app_version':'1.83.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'decode_dex_annotation_directory_to_reconstruct_exact_retrofit_firmware_check_request_and_response_contract',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'baseapi_contracts':[],'hardwareversion_annotations':[],'model_request_calls':[],'url_candidates':[],
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            seen_urls=set()
            def inspect(label,b):
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                for s in strings:
                    low=str(s).lower()
                    if (low.startswith('http://') or low.startswith('https://')) and s not in seen_urls:
                        seen_urls.add(s);rep['url_candidates'].append({'dex':label,'value':s})
                ann=self._retrofit_annotations(b,strings,types,fields,methods,BASEAPI,'i')
                mh=self._find_http_annotations(ann.get('method_annotations',[]))
                if mh or ann.get('parameter_annotations'):
                    rep['baseapi_contracts'].append({'dex':label,'target_class':BASEAPI,'target_method':'i','annotation_directory':ann,'http_annotations':mh})
                hv=self._retrofit_annotations(b,strings,types,fields,methods,HWVER,None)
                if hv.get('field_annotations') or hv.get('class_annotations'):
                    rep['hardwareversion_annotations'].append({'dex':label,'annotation_directory':hv})
                em={mid:(code,kind,acc) for _,mid,code,kind,acc in enc}
                for m in methods:
                    cls,name=m.get('class'),m.get('name');code,kind,acc=em.get(m['idx'],(0,None,None))
                    if cls!=HWM or not code:continue
                    s=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                    pmap=v180.AppV180._param_map(b,code,m,acc);s=v180.AppV180._rewrite_unknown_regs(s,pmap)
                    for inv in s.get('invokes',[]):
                        t=inv.get('target') or {}
                        if t.get('class')==BASEAPI and t.get('method')=='i':
                            rep['model_request_calls'].append({'dex':label,'from_method':name,'unit':inv.get('unit'),'target':t,'args':inv.get('args'),'incoming_registers':pmap})
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
            endpoint=[];param_contract=[]
            for c in rep['baseapi_contracts']:
                for h in c.get('http_annotations',[]):
                    a=h.get('annotation',{});els=a.get('elements',{})
                    vals=[]
                    for v in els.values():
                        if isinstance(v,str):vals.append(v)
                    endpoint.extend([v for v in vals if 'checkforupdate' in v.lower() or 'app-device' in v.lower()])
                for p in c.get('annotation_directory',{}).get('parameter_annotations',[]):param_contract.extend(p.get('parameters',[]))
            response_keys=[]
            for h in rep['hardwareversion_annotations']:
                for fa in h.get('annotation_directory',{}).get('field_annotations',[]):
                    row={'field':(fa.get('field') or {}).get('name'),'annotations':fa.get('annotations',[])};response_keys.append(row)
            rep['resolved']={'endpoint_candidates':sorted(set(endpoint)),'parameter_contract':param_contract,'response_field_annotations':response_keys,
                             'known_endpoint_from_v182':'app-device/checkForUpdate','official_local_extensions':['.fot','.img'],
                             'write_gate':'KEEP_OTA_DISABLED_UNTIL_EXACT_REQUEST_SUCCEEDS_AND_DOWNLOADED_FILE_PASSES_SIZE_HASH_HEADER_CHECKS'}
            rep['summary']={'baseapi_contracts':len(rep['baseapi_contracts']),'model_request_calls':len(rep['model_request_calls']),
                            'hardwareversion_annotation_sets':len(rep['hardwareversion_annotations']),'resolved_endpoints':len(rep['resolved']['endpoint_candidates']),
                            'next':'Use decoded Retrofit method/parameter annotations and model arguments to perform one official metadata request; download only the returned official file and validate size/hash/header before any BLE OTA write.'}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v183');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-retrofit-contract-v183.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.83 · falló: '+repr(err));return
            self.report={'utrawatch_retrofit_contract_v183':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep['summary'];self.status.set(f"V1.83 LISTO · contratos={s['baseapi_contracts']} · llamadas={s['model_request_calls']} · endpoints={s['resolved_endpoints']} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV183(root);root.mainloop()
