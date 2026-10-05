import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v177 as v177
import app_v145 as v145
import app_v166 as v166

base.APP_VERSION='1.78.0'

CMD='Lcom/bluetrum/fota/bluetooth/a;'
DATA='Lcom/bluetrum/fota/bluetooth/b;'
MGR='Lcom/bluetrum/fota/bluetooth/h;'
ZK='Lcom/wtwd/cocousa/ble/ZKBleOtaManager;'
BLE='Lcom/wtwd/cocousa/ble/BleConnectService;'
GATTCB='Lcom/wtwd/cocousa/ble/BleConnectService$5;'
HW='Lcom/wtwd/cocousa/ui/module/main/device/update/HardwareUpdatePresenter;'
HWM='Lcom/wtwd/cocousa/ui/module/main/device/update/HardwareUpdateModel;'

class AppV178(v177.AppV177):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.78')
        self._clean_v178();self._install_v178()
        self.status.set('V1.78 lista · decodifica Dalvik instrucción por instrucción para eliminar llamadas falsas y cerrar el flujo OTA. Sin red ni escrituras.')

    def _clean_v178(self):
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

    def _install_v178(self):
        top=self.root.winfo_children()[0]
        self.v178_button=ttk.Button(top,text='DECODIFICAR OTA EXACTO',command=self.decode_exact_ota)
        sib=top.winfo_children()
        try:self.v178_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v178_button.place(x=8,y=8)

    @staticmethod
    def _width(op):
        if op in (0x02,0x05,0x08,0x13,0x15,0x16,0x19,0x1a,0x1c,0x1f,0x20,0x22,0x23,0x29): return 2
        if op in (0x03,0x06,0x09,0x14,0x17,0x1b,0x24,0x25,0x26,0x2a,0x2b,0x2c): return 3
        if op==0x18:return 5
        if 0x2d<=op<=0x3d:return 2
        if 0x44<=op<=0x6d:return 2
        if 0x6e<=op<=0x72:return 3
        if 0x74<=op<=0x78:return 3
        if 0x90<=op<=0xaf:return 2
        if 0xd0<=op<=0xe2:return 2
        return 1

    @classmethod
    def _exact_decode(cls,b,code_off,strings,methods,fields):
        out={'instructions':[],'calls':[],'strings':[],'fields':[],'consts':[],'decode_errors':[]}
        if not code_off or code_off+16>len(b):return out
        try:
            n=v166.u32(b,code_off+12);p=code_off+16
            units=[v166.u16(b,p+i*2) for i in range(min(n,(len(b)-p)//2))]
        except Exception as ex:
            out['decode_errors'].append(repr(ex));return out
        seen_calls=set();seen_strings=set();seen_fields=set();i=0
        while i<len(units):
            w=units[i];op=w&0xff
            # payload pseudo-instructions are encoded as nop with a non-zero high byte.
            if op==0x00 and (w>>8):
                ident=w
                try:
                    if ident==0x0100 and i+1<len(units): width=4+2*units[i+1]
                    elif ident==0x0200 and i+1<len(units): width=2+4*units[i+1]
                    elif ident==0x0300 and i+3<len(units):
                        ew=units[i+1];sz=units[i+2]|(units[i+3]<<16);width=4+((ew*sz+1)//2)
                    else:width=1
                except:width=1
                out['instructions'].append({'unit':i,'op':hex(op),'payload':hex(ident),'width':width})
                i+=max(1,width);continue
            width=cls._width(op)
            ins={'unit':i,'op':hex(op),'width':width,'words':[hex(x) for x in units[i:min(len(units),i+width)]]}
            try:
                if op==0x1a and i+1<len(units):
                    si=units[i+1];ins['kind']='const-string';ins['string_idx']=si
                    if si<len(strings):
                        s=strings[si];ins['value']=s
                        if si not in seen_strings:seen_strings.add(si);out['strings'].append({'idx':si,'value':s})
                elif op==0x1b and i+2<len(units):
                    si=units[i+1]|(units[i+2]<<16);ins['kind']='const-string/jumbo';ins['string_idx']=si
                    if si<len(strings):
                        s=strings[si];ins['value']=s
                        if si not in seen_strings:seen_strings.add(si);out['strings'].append({'idx':si,'value':s})
                elif 0x52<=op<=0x6d and i+1<len(units):
                    fi=units[i+1];ins['kind']='field';ins['field_idx']=fi
                    if fi<len(fields):
                        f=fields[fi];ins['field']=f
                        if fi not in seen_fields:seen_fields.add(fi);out['fields'].append(f)
                elif (0x6e<=op<=0x72 or 0x74<=op<=0x78) and i+1<len(units):
                    mi=units[i+1];ins['kind']='invoke';ins['method_idx']=mi
                    if mi<len(methods):
                        m=methods[mi];c={'idx':mi,'class':m.get('class'),'method':m.get('name'),'proto':m.get('proto'),'unit':i,'opcode':hex(op)}
                        ins['call']=c
                        key=(i,mi)
                        if key not in seen_calls:seen_calls.add(key);out['calls'].append(c)
                elif op==0x12:
                    val=(w>>12)&0xf;val=val-16 if val&8 else val;ins['kind']='const/4';ins['value']=val;out['consts'].append({'unit':i,'value':val,'hex':hex(val&0xffffffff)})
                elif op==0x13 and i+1<len(units):
                    val=units[i+1];val=val-65536 if val&0x8000 else val;ins['kind']='const/16';ins['value']=val;out['consts'].append({'unit':i,'value':val,'hex':hex(val&0xffffffff)})
                elif op==0x14 and i+2<len(units):
                    val=units[i+1]|(units[i+2]<<16);val=val-0x100000000 if val&0x80000000 else val;ins['kind']='const';ins['value']=val;out['consts'].append({'unit':i,'value':val,'hex':hex(val&0xffffffff)})
                elif op==0x15 and i+1<len(units):
                    val=units[i+1]<<16;val=val-0x100000000 if val&0x80000000 else val;ins['kind']='const/high16';ins['value']=val;out['consts'].append({'unit':i,'value':val,'hex':hex(val&0xffffffff)})
            except Exception as ex:out['decode_errors'].append({'unit':i,'error':repr(ex)})
            out['instructions'].append(ins);i+=max(1,width)
        out['instructions']=out['instructions'][:2500];out['calls']=out['calls'][:800];out['strings']=out['strings'][:800];out['fields']=out['fields'][:800];out['consts']=out['consts'][:800]
        return out

    def decode_exact_ota(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V1.78 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.78 · decodificando opcodes Dalvik reales del flujo OTA…')
        def work():
            rep={'app_version':'1.78.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'eliminate_false_dex_edges_and_recover_exact_ota_calls_fields_strings_and_state_machine',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'parser_fix':'walk Dalvik instructions by real opcode width; only invoke opcodes create call edges',
                 'focus_methods':[],'exact_cross_edges':[],'write_paths':[],'notify_paths':[],'hardware_start_paths':[],
                 'command_paths':[],'state_methods':[],'false_edge_checks':[],
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            seen_edges=set()
            focus={CMD,DATA,MGR,ZK,BLE,GATTCB,HW,HWM}
            wanted_mgr={'A','B','C','D','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z'}
            wanted_ble={'a','a0','I','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y'}
            wanted_hw={'t1','u1','v1','X0','O'}
            def inspect(label,b):
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                em={mid:(code,kind,acc) for _,mid,code,kind,acc in enc}
                for m in methods:
                    cls,name=m.get('class'),m.get('name')
                    if cls not in focus:continue
                    if cls==MGR and name not in wanted_mgr:continue
                    if cls==BLE and name not in wanted_ble:continue
                    if cls==HW and name not in wanted_hw:continue
                    code,kind,acc=em.get(m['idx'],(0,None,None))
                    if not code:continue
                    d=self._exact_decode(b,code,strings,methods,fields)
                    row={'dex':label,'class':cls,'method':name,'method_idx':m['idx'],'proto':m.get('proto'),'kind':kind,'access_flags':acc,'code_off':code,**d}
                    rep['focus_methods'].append(row)
                    for c in d['calls']:
                        if c.get('class') in focus:
                            e=(label,m['idx'],c['unit'],c['idx'])
                            if e not in seen_edges:
                                seen_edges.add(e);rep['exact_cross_edges'].append({'dex':label,'from_class':cls,'from_method':name,'from_idx':m['idx'],'unit':c['unit'],'opcode':c['opcode'],'to_class':c['class'],'to_method':c['method'],'to_idx':c['idx'],'to_proto':c.get('proto')})
                    calls={(c.get('class'),c.get('method')) for c in d['calls']}
                    fieldnames={f.get('name') for f in d['fields']}
                    vals=[x.get('value','') for x in d['strings']]
                    if cls==BLE and ('zkWriteCharacteristic' in fieldnames or ('Landroid/bluetooth/BluetoothGatt;','writeCharacteristic') in calls or any('writeZKData' in str(x) for x in vals)):
                        rep['write_paths'].append(row)
                    if cls==GATTCB and name=='onCharacteristicChanged':rep['notify_paths'].append(row)
                    if cls==HW and (any(c[0] in (HWM,ZK,MGR,BLE) for c in calls) or {'isStartUpgrade','listFileData','file'} & fieldnames):rep['hardware_start_paths'].append(row)
                    if cls in (CMD,DATA) or (cls==MGR and name in {'k','l','t','u','v','w','x','y'}):rep['command_paths'].append(row)
                    if cls==MGR and name in wanted_mgr:rep['state_methods'].append(row)
                # explicitly test the suspicious V1.77 a0 edge and common impossible ad/library edges.
                for r in rep['focus_methods'][-100:]:
                    if r['dex']!=label:continue
                    if r['class']==BLE and r['method']=='a0':
                        rep['false_edge_checks'].append({'check':'BleConnectService.a0','exact_calls':r['calls'],'instruction_count':len(r['instructions'])})
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
            for k,lim in [('focus_methods',120),('exact_cross_edges',300),('write_paths',20),('notify_paths',20),('hardware_start_paths',30),('command_paths',60),('state_methods',40),('false_edge_checks',20)]:rep[k]=rep[k][:lim]
            rep['summary']={'focus_methods':len(rep['focus_methods']),'exact_cross_edges':len(rep['exact_cross_edges']),'write_paths':len(rep['write_paths']),'notify_paths':len(rep['notify_paths']),'hardware_start_paths':len(rep['hardware_start_paths']),'command_paths':len(rep['command_paths']),'state_methods':len(rep['state_methods']),'next':'Use only exact invoke edges from this report to reconstruct command bytes and start/preflight sequence. Keep firmware writes disabled until image identity and every state transition are proven.'}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v178');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-exact-dalvik-ota-v178.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.78 · falló: '+repr(err));return
            self.report={'exact_dalvik_ota_v178':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep['summary'];self.status.set(f"V1.78 LISTO · métodos={s['focus_methods']} · edges exactos={s['exact_cross_edges']} · write={s['write_paths']} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV178(root);root.mainloop()
