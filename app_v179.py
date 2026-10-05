import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v178 as v178
import app_v145 as v145
import app_v166 as v166

base.APP_VERSION='1.79.0'

CMD='Lcom/bluetrum/fota/bluetooth/a;'
DATA='Lcom/bluetrum/fota/bluetooth/b;'
MGR='Lcom/bluetrum/fota/bluetooth/h;'
ZK='Lcom/wtwd/cocousa/ble/ZKBleOtaManager;'
BLE='Lcom/wtwd/cocousa/ble/BleConnectService;'
GATTCB='Lcom/wtwd/cocousa/ble/BleConnectService$5;'
HW='Lcom/wtwd/cocousa/ui/module/main/device/update/HardwareUpdatePresenter;'
HWM='Lcom/wtwd/cocousa/ui/module/main/device/update/HardwareUpdateModel;'

class AppV179(v178.AppV178):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.79')
        self._clean_v179();self._install_v179()
        self.status.set('V1.79 lista · reconstruye argumentos reales, bytes de comando y secuencia de arranque OTA. Sin red ni escrituras.')

    def _clean_v179(self):
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

    def _install_v179(self):
        top=self.root.winfo_children()[0]
        self.v179_button=ttk.Button(top,text='RECONSTRUIR SECUENCIA OTA',command=self.reconstruct_ota_sequence)
        sib=top.winfo_children()
        try:self.v179_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v179_button.place(x=8,y=8)

    @staticmethod
    def _invoke_regs(units,i,op):
        try:
            w=units[i]
            if 0x6e<=op<=0x72:
                count=(w>>12)&0xf;g=(w>>8)&0xf;x=units[i+2]
                regs=[x&0xf,(x>>4)&0xf,(x>>8)&0xf,(x>>12)&0xf,g]
                return regs[:count]
            if 0x74<=op<=0x78:
                count=(w>>8)&0xff;start=units[i+2]
                return list(range(start,start+count))
        except:pass
        return []

    @staticmethod
    def _signed(v,bits):
        top=1<<(bits-1);return v-(1<<bits) if v&top else v

    @classmethod
    def _symbolic(cls,b,code_off,strings,types,methods,fields):
        out={'trace':[],'invokes':[],'command_generator_calls':[],'ble_write_calls':[],'critical_field_writes':[],'returns':[],'decode_errors':[]}
        if not code_off or code_off+16>len(b):return out
        try:
            n=v166.u32(b,code_off+12);p=code_off+16
            units=[v166.u16(b,p+i*2) for i in range(min(n,(len(b)-p)//2))]
        except Exception as ex:out['decode_errors'].append(repr(ex));return out
        regs={};last_result=None;i=0
        interesting_fields={'allowedUpdate','isDeviceReady','isZKUpdating','_needIdentification','mBlockSize','mPacketSize','mStartAddress','dataProvider','commandGenerator','zkWriteCharacteristic','isStartUpgrade','upgradeIndex','file','listFileData','zkBleOtaManager'}
        def val(r):return regs.get(r,{'kind':'reg','reg':r,'value':'unknown'})
        def setr(r,x):regs[r]=x
        while i<len(units):
            w=units[i];op=w&0xff
            if op==0x00 and (w>>8):
                ident=w
                try:
                    if ident==0x0100 and i+1<len(units):width=4+2*units[i+1]
                    elif ident==0x0200 and i+1<len(units):width=2+4*units[i+1]
                    elif ident==0x0300 and i+3<len(units):
                        ew=units[i+1];sz=units[i+2]|(units[i+3]<<16);width=4+((ew*sz+1)//2)
                    else:width=1
                except:width=1
                i+=max(1,width);continue
            width=cls._width(op)
            ev={'unit':i,'op':hex(op)}
            try:
                if op==0x01:
                    a=(w>>8)&0xf;breg=(w>>12)&0xf;setr(a,val(breg));ev.update({'kind':'move','dst':a,'src':breg,'value':val(a)})
                elif op==0x02 and i+1<len(units):
                    a=(w>>8)&0xff;breg=units[i+1];setr(a,val(breg));ev.update({'kind':'move','dst':a,'src':breg,'value':val(a)})
                elif op==0x03 and i+2<len(units):
                    a=units[i+1];breg=units[i+2];setr(a,val(breg));ev.update({'kind':'move','dst':a,'src':breg,'value':val(a)})
                elif op in (0x0a,0x0b,0x0c):
                    a=(w>>8)&0xff;setr(a,last_result or {'kind':'result','value':'unknown'});ev.update({'kind':'move-result','dst':a,'value':val(a)})
                elif op==0x12:
                    a=(w>>8)&0xf;lit=cls._signed((w>>12)&0xf,4);setr(a,{'kind':'const','value':lit});ev.update({'kind':'const','dst':a,'value':lit})
                elif op==0x13 and i+1<len(units):
                    a=(w>>8)&0xff;lit=cls._signed(units[i+1],16);setr(a,{'kind':'const','value':lit});ev.update({'kind':'const','dst':a,'value':lit})
                elif op==0x14 and i+2<len(units):
                    a=(w>>8)&0xff;lit=cls._signed(units[i+1]|(units[i+2]<<16),32);setr(a,{'kind':'const','value':lit});ev.update({'kind':'const','dst':a,'value':lit})
                elif op==0x15 and i+1<len(units):
                    a=(w>>8)&0xff;lit=cls._signed(units[i+1]<<16,32);setr(a,{'kind':'const','value':lit});ev.update({'kind':'const','dst':a,'value':lit})
                elif op in (0x1a,0x1b):
                    a=(w>>8)&0xff;si=units[i+1] if op==0x1a else units[i+1]|(units[i+2]<<16);s=strings[si] if si<len(strings) else str(si);setr(a,{'kind':'string','value':s});ev.update({'kind':'string','dst':a,'value':s})
                elif op==0x22 and i+1<len(units):
                    a=(w>>8)&0xff;ti=units[i+1];t=types[ti] if ti<len(types) else str(ti);setr(a,{'kind':'new','type':t});ev.update({'kind':'new','dst':a,'type':t})
                elif 0x52<=op<=0x58 and i+1<len(units):
                    a=(w>>8)&0xf;obj=(w>>12)&0xf;fi=units[i+1];f=fields[fi] if fi<len(fields) else {'idx':fi};x={'kind':'field','field':f,'object':val(obj)};setr(a,x);ev.update({'kind':'iget','dst':a,'obj':obj,'field':f})
                elif 0x59<=op<=0x5f and i+1<len(units):
                    a=(w>>8)&0xf;obj=(w>>12)&0xf;fi=units[i+1];f=fields[fi] if fi<len(fields) else {'idx':fi};ev.update({'kind':'iput','src':a,'obj':obj,'field':f,'value':val(a)})
                    if f.get('name') in interesting_fields:out['critical_field_writes'].append(dict(ev))
                elif 0x60<=op<=0x66 and i+1<len(units):
                    a=(w>>8)&0xff;fi=units[i+1];f=fields[fi] if fi<len(fields) else {'idx':fi};setr(a,{'kind':'static_field','field':f});ev.update({'kind':'sget','dst':a,'field':f})
                elif 0x67<=op<=0x6d and i+1<len(units):
                    a=(w>>8)&0xff;fi=units[i+1];f=fields[fi] if fi<len(fields) else {'idx':fi};ev.update({'kind':'sput','src':a,'field':f,'value':val(a)})
                    if f.get('name') in interesting_fields:out['critical_field_writes'].append(dict(ev))
                elif op==0x8d:
                    a=(w>>8)&0xf;breg=(w>>12)&0xf;x=val(breg)
                    if x.get('kind')=='const':
                        q=x['value']&0xff;q=q-256 if q&0x80 else q;x={'kind':'const','value':q}
                    setr(a,x);ev.update({'kind':'int-to-byte','dst':a,'src':breg,'value':x})
                elif op==0xd8 and i+1<len(units):
                    a=(w>>8)&0xff;x=units[i+1];breg=x&0xff;lit=cls._signed((x>>8)&0xff,8);src=val(breg)
                    z={'kind':'expr','op':'add','left':src,'right':lit}
                    if src.get('kind')=='const':z={'kind':'const','value':src['value']+lit}
                    setr(a,z);ev.update({'kind':'add-lit8','dst':a,'src':breg,'lit':lit,'value':z})
                elif (0x6e<=op<=0x72 or 0x74<=op<=0x78) and i+1<len(units):
                    mi=units[i+1];m=methods[mi] if mi<len(methods) else {'idx':mi};rr=cls._invoke_regs(units,i,op);args=[val(r) for r in rr]
                    inv={'unit':i,'opcode':hex(op),'target':{'idx':mi,'class':m.get('class'),'method':m.get('name'),'proto':m.get('proto')},'arg_regs':rr,'args':args}
                    out['invokes'].append(inv);ev={'unit':i,'op':hex(op),'kind':'invoke','invoke':inv}
                    last_result={'kind':'call_result','call':inv['target'],'args':args}
                    if m.get('class')==CMD and m.get('name')=='a':out['command_generator_calls'].append(inv)
                    if m.get('class')==BLE and m.get('name') in ('a','a0'):out['ble_write_calls'].append(inv)
                elif op in (0x0f,0x10,0x11):
                    a=(w>>8)&0xff;x=val(a);ev.update({'kind':'return','reg':a,'value':x});out['returns'].append({'unit':i,'value':x})
            except Exception as ex:out['decode_errors'].append({'unit':i,'error':repr(ex)})
            if ev.get('kind') in ('const','string','move-result','iget','iput','sget','sput','int-to-byte','add-lit8','invoke','return'):
                out['trace'].append(ev)
            i+=max(1,width)
        for k,lim in [('trace',1200),('invokes',500),('command_generator_calls',100),('ble_write_calls',100),('critical_field_writes',200),('returns',50)]:out[k]=out[k][:lim]
        return out

    def reconstruct_ota_sequence(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V1.79 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.79 · reconstruyendo bytes, argumentos y handoff OTA…')
        def work():
            rep={'app_version':'1.79.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'symbolically_reconstruct_exact_ota_command_arguments_start_sequence_and_ble_handoff_from_real_dalvik_invokes',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known_from_v178':{'exact_cross_edges':152,'write_paths':1,'notify_paths':1,'hardware_start_paths':5,'command_paths':11,'state_methods':19},
                 'critical_methods':[],'command_bytes_evidence':[],'start_sequence_evidence':[],'ble_handoff_evidence':[],'state_transition_evidence':[],
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            wanted={
                CMD:{'<clinit>','a'}, DATA:{'<init>'},
                MGR:{'A','B','C','D','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z'},
                ZK:{'<init>','n','p','q','r','s','t','u','v','w','x','y'},
                BLE:{'a','a0','I','s','V'}, GATTCB:{'onCharacteristicChanged'},
                HW:{'O','X0','t1','u1','v1'}, HWM:{'h','i'}
            }
            def inspect(label,b):
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                em={mid:(code,kind,acc) for _,mid,code,kind,acc in enc}
                for m in methods:
                    cls,name=m.get('class'),m.get('name')
                    if cls not in wanted or name not in wanted[cls]:continue
                    code,kind,acc=em.get(m['idx'],(0,None,None))
                    if not code:continue
                    s=self._symbolic(b,code,strings,types,methods,fields)
                    row={'dex':label,'class':cls,'method':name,'method_idx':m['idx'],'proto':m.get('proto'),'kind':kind,'access_flags':acc,'code_off':code,**s}
                    rep['critical_methods'].append(row)
                    if s['command_generator_calls'] or cls==CMD:rep['command_bytes_evidence'].append(row)
                    if cls in (HW,HWM) or (cls==BLE and name in ('I','s')):rep['start_sequence_evidence'].append(row)
                    if s['ble_write_calls'] or (cls==BLE and name in ('a','a0')) or cls==GATTCB:rep['ble_handoff_evidence'].append(row)
                    if cls in (MGR,ZK) and (s['critical_field_writes'] or name in ('A','B','C','j','n','o','p','q','r','t','u','w')):rep['state_transition_evidence'].append(row)
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
            for k,lim in [('critical_methods',80),('command_bytes_evidence',25),('start_sequence_evidence',20),('ble_handoff_evidence',15),('state_transition_evidence',35)]:rep[k]=rep[k][:lim]
            rep['summary']={'critical_methods':len(rep['critical_methods']),'command_bytes_evidence':len(rep['command_bytes_evidence']),'start_sequence_evidence':len(rep['start_sequence_evidence']),'ble_handoff_evidence':len(rep['ble_handoff_evidence']),'state_transition_evidence':len(rep['state_transition_evidence']),'next':'Resolve concrete command byte values and the exact presenter/manager start chain from symbolic register arguments. Do not write OTA until an exact official image for this hardware is identified and validated.'}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v179');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-ota-sequence-v179.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.79 · falló: '+repr(err));return
            self.report={'ota_sequence_v179':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep['summary'];self.status.set(f"V1.79 LISTO · críticos={s['critical_methods']} · comandos={s['command_bytes_evidence']} · arranque={s['start_sequence_evidence']} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV179(root);root.mainloop()
