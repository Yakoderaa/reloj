import io,json,os,zipfile,re
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v179 as v179
import app_v178 as v178
import app_v145 as v145
import app_v166 as v166

base.APP_VERSION='1.80.0'

CMD=v179.CMD
DATA=v179.DATA
MGR=v179.MGR
ZK=v179.ZK
BLE=v179.BLE
GATTCB=v179.GATTCB
HW=v179.HW
HWM=v179.HWM
HWVER='Lcom/wtwd/cocousa/entity/device/HardwareVersion;'

class AppV180(v179.AppV179):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.80')
        self._clean_v180();self._install_v180()
        self.status.set('V1.80 lista · resuelve parámetros Dalvik, plantillas de bytes OTA y rastrea la fuente oficial del firmware. Sin red ni escrituras.')

    def _clean_v180(self):
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

    def _install_v180(self):
        top=self.root.winfo_children()[0]
        self.v180_button=ttk.Button(top,text='CERRAR CONTRATO OTA + FIRMWARE',command=self.close_ota_contract)
        sib=top.winfo_children()
        try:self.v180_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v180_button.place(x=8,y=8)

    @staticmethod
    def _param_map(b,code_off,method,access_flags):
        try:
            regs_size=v166.u16(b,code_off)
            ins_size=v166.u16(b,code_off+2)
        except:return {}
        proto=method.get('proto') or {}
        args=list(proto.get('args') or [])
        incoming=[]
        is_static=bool(int(access_flags or 0)&0x8)
        if not is_static:incoming.append(('this',method.get('class')))
        for idx,t in enumerate(args):
            incoming.append((idx,t))
            if t in ('J','D'):incoming.append((str(idx)+':wide',t))
        start=max(0,regs_size-ins_size)
        out={}
        for off,item in enumerate(incoming[:ins_size]):
            reg=start+off
            if item[0]=='this':out[reg]={'kind':'this','type':item[1]}
            elif isinstance(item[0],int):out[reg]={'kind':'param','index':item[0],'type':item[1]}
            else:out[reg]={'kind':'param-wide','index':item[0],'type':item[1]}
        return out

    @classmethod
    def _rewrite_unknown_regs(cls,obj,pmap):
        if isinstance(obj,list):return [cls._rewrite_unknown_regs(x,pmap) for x in obj]
        if not isinstance(obj,dict):return obj
        if obj.get('kind')=='reg' and obj.get('value')=='unknown' and obj.get('reg') in pmap:
            return dict(pmap[obj['reg']],reg=obj.get('reg'))
        return {k:cls._rewrite_unknown_regs(v,pmap) for k,v in obj.items()}

    @staticmethod
    def _byte_token(x):
        if not isinstance(x,dict):return {'kind':'unknown','value':x}
        k=x.get('kind')
        if k=='const':
            v=int(x.get('value',0));return {'kind':'byte','signed':v,'u8':v&255,'hex':f'{v&255:02x}'}
        if k=='param':return {'kind':'param','index':x.get('index'),'type':x.get('type')}
        if k=='field':
            f=x.get('field') or {};return {'kind':'field','class':f.get('class'),'name':f.get('name'),'type':f.get('type')}
        if k=='static_field':
            f=x.get('field') or {};return {'kind':'static_field','class':f.get('class'),'name':f.get('name'),'type':f.get('type')}
        if k=='call_result':
            c=x.get('call') or {}
            if c.get('class')==CMD and c.get('method')=='a':
                a=(x.get('args') or [{}])[-1]
                return {'kind':'generated_command','selector':AppV180._byte_token(a)}
            return {'kind':'call_result','class':c.get('class'),'method':c.get('method')}
        if k=='expr':return {'kind':'expr','op':x.get('op'),'left':AppV180._byte_token(x.get('left',{})),'right':x.get('right')}
        return {'kind':k or 'unknown','value':x.get('value')}

    @classmethod
    def _templates(cls,row):
        trace=row.get('trace') or []
        out=[]
        buf=[]
        stream=[]
        for ev in trace:
            if ev.get('kind')!='invoke':continue
            inv=ev.get('invoke') or {};t=inv.get('target') or {};args=inv.get('args') or []
            c,m=t.get('class'),t.get('method')
            if c=='Ljava/nio/ByteBuffer;' and m=='put' and len(args)>=2:
                buf.append(cls._byte_token(args[-1]))
            elif c in ('Ljava/io/ByteArrayOutputStream;','Ljava/io/OutputStream;') and m=='write' and len(args)>=2:
                stream.append(cls._byte_token(args[-1]))
            elif c==BLE and m in ('a','a0'):
                seq=stream[:] if stream else buf[:]
                out.append({'unit':inv.get('unit'),'sink':m,'bytes_or_tokens':seq,'arg':cls._byte_token(args[-1]) if args else None})
                stream=[];buf=[]
        if stream:out.append({'unit':None,'sink':'pending_stream','bytes_or_tokens':stream})
        if buf:out.append({'unit':None,'sink':'pending_buffer','bytes_or_tokens':buf})
        return out

    @staticmethod
    def _candidate_string(s):
        q=str(s or '')
        low=q.lower()
        keys=('http://','https://','.fot','.img','.bin','firmware','upgrade','update','ota/','/ota','hardwareversion','hardware_version','versioninfo','download','fileurl','file_url')
        return any(k in low for k in keys)

    def close_ota_contract(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V1.80 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.80 · resolviendo parámetros, bytes y fuente oficial de firmware…')
        def work():
            rep={'app_version':'1.80.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'resolve_dalvik_parameter_registers_concrete_ota_byte_templates_exact_start_chain_and_official_firmware_source_identity',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known_from_v179':{'critical_methods':38,'command_bytes_evidence':3,'start_sequence_evidence':9,'ble_handoff_evidence':9,'state_transition_evidence':15},
                 'resolved_methods':[],'command_templates':[],'exact_start_edges':[],'firmware_source_methods':[],'firmware_string_candidates':[],
                 'hardware_version_methods':[],'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            focus={CMD,DATA,MGR,ZK,BLE,GATTCB,HW,HWM,HWVER}
            seen_strings=set();seen_edges=set()
            class_terms=('update','upgrade','firmware','hardware','version','download','ota','api','service')
            def inspect(label,b):
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                em={mid:(code,kind,acc) for _,mid,code,kind,acc in enc}
                for s in strings:
                    if self._candidate_string(s) and s not in seen_strings:
                        seen_strings.add(s);rep['firmware_string_candidates'].append({'dex':label,'value':s})
                for m in methods:
                    cls,name=m.get('class'),m.get('name')
                    low=(cls or '').lower()
                    if cls not in focus and not any(t in low for t in class_terms):continue
                    code,kind,acc=em.get(m['idx'],(0,None,None))
                    if not code:continue
                    if cls not in focus and not any(t in low for t in ('update','upgrade','firmware','hardware','download','ota')):continue
                    s=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                    pmap=self._param_map(b,code,m,acc)
                    s=self._rewrite_unknown_regs(s,pmap)
                    row={'dex':label,'class':cls,'method':name,'method_idx':m['idx'],'proto':m.get('proto'),'kind':kind,'access_flags':acc,
                         'code_off':code,'incoming_registers':pmap,**s}
                    relevant_strings=[]
                    for ev in s.get('trace',[]):
                        if ev.get('kind')=='string' and self._candidate_string(ev.get('value')):
                            relevant_strings.append(ev.get('value'))
                    templates=self._templates(row)
                    if cls in focus:
                        row['command_templates']=templates
                        rep['resolved_methods'].append(row)
                    if templates:
                        for t in templates:rep['command_templates'].append({'dex':label,'class':cls,'method':name,**t})
                    for inv in s.get('invokes',[]):
                        t=inv.get('target') or {}
                        if t.get('class') in focus and cls in focus:
                            key=(label,m['idx'],inv.get('unit'),t.get('idx'))
                            if key not in seen_edges:
                                seen_edges.add(key)
                                rep['exact_start_edges'].append({'dex':label,'from_class':cls,'from_method':name,'unit':inv.get('unit'),
                                    'to_class':t.get('class'),'to_method':t.get('method'),'to_proto':t.get('proto'),'args':inv.get('args')})
                    if cls==HWVER:rep['hardware_version_methods'].append(row)
                    networkish=[]
                    for inv in s.get('invokes',[]):
                        t=inv.get('target') or {};tl=((t.get('class') or '')+' '+(t.get('method') or '')).lower()
                        if any(x in tl for x in ('retrofit','okhttp','download','api','service','upgrade','update','firmware')):
                            networkish.append(inv)
                    if relevant_strings or networkish:
                        rep['firmware_source_methods'].append({'dex':label,'class':cls,'method':name,'proto':m.get('proto'),
                            'incoming_registers':pmap,'strings':relevant_strings,'networkish_calls':networkish[:80],
                            'returns':s.get('returns',[])[:20],'critical_field_writes':s.get('critical_field_writes',[])[:30]})
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
            for k,lim in [('resolved_methods',140),('command_templates',120),('exact_start_edges',350),('firmware_source_methods',100),('firmware_string_candidates',350),('hardware_version_methods',80)]:
                rep[k]=rep[k][:lim]
            complete=[x for x in rep['command_templates'] if x.get('sink') in ('a','a0') and x.get('bytes_or_tokens')]
            rep['summary']={'resolved_methods':len(rep['resolved_methods']),'command_templates':len(rep['command_templates']),
                            'direct_ble_templates':len(complete),'exact_start_edges':len(rep['exact_start_edges']),
                            'firmware_source_methods':len(rep['firmware_source_methods']),'firmware_string_candidates':len(rep['firmware_string_candidates']),
                            'hardware_version_methods':len(rep['hardware_version_methods']),
                            'next':'Use concrete OTA templates plus exact official firmware source/version identity. Firmware writes remain disabled until image hardware/version/header/checksum are validated.'}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v180');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-ota-contract-firmware-v180.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.80 · falló: '+repr(err));return
            self.report={'ota_contract_firmware_v180':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep['summary'];self.status.set(f"V1.80 LISTO · templates={s['command_templates']} · edges={s['exact_start_edges']} · fuentes={s['firmware_source_methods']} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV180(root);root.mainloop()
