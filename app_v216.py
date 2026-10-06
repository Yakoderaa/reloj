import io,json,os,zipfile,struct
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v215 as v215
import app_v199 as v199
import app_v179 as v179
import app_v180 as v180
import app_v210 as v210
import app_v145 as v145

base.APP_VERSION='2.16.0'
DM='Lcom/wtwd/cocousa/manager/DeviceManager;'
APP='Lcom/wtwd/cocousa/ui/module/application/Application;'
DEV='Lcom/wtwd/cocousa/ui/module/main/device/DeviceModel;'
DEV1='Lcom/wtwd/cocousa/ui/module/main/device/DeviceModel$1;'
BASEACT='Lcom/wtwd/cocousa/ui/base/view/BaseImmersiveActivity;'
PREF='Lcom/wtwd/cocousa/utils/PrefUtil;'
TEXT='Landroid/text/TextUtils;'
UI='Lcom/wtwd/cocousa/entity/user/UserDeviceInfo;'
DI='Lcom/wtwd/cocousa/entity/device/DeviceInfo;'
TARGET_METHODS={(DEV1,'c'),(APP,'onBluetoothReadData'),(BASEACT,'R1'),(DEV,'j')}
CALLER_TARGETS={(DEV,'j'),(BASEACT,'R1')}

class AppV216(v215.AppV215):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V2.16')
        self._clean_v216();self._install_v216();self._restore_location_button()
        self.status.set('V2.16 lista · prueba el orden real de WATCH_ID/MAC y cuándo se limpia. Sin red ni OTA.')

    def _clean_v216(self):
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

    def _install_v216(self):
        top=self.root.winfo_children()[0]
        self.v216_button=ttk.Button(top,text='PROBAR ORDEN REAL WATCH_ID',command=self.resolve_runtime_order)
        sib=top.winfo_children()
        try:self.v216_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v216_button.place(x=8,y=8)

    @staticmethod
    def _simple(a):
        try:return v210.AppV210._simple(a)
        except:return a

    @staticmethod
    def _branch_ops(b,code_off):
        out=[]
        try:
            if not code_off or code_off+16>len(b):return out
            n=struct.unpack_from('<I',b,code_off+12)[0];start=code_off+16;end=min(len(b),start+n*2)
            units=struct.unpack_from('<'+'H'*((end-start)//2),b,start)
            names={0x28:'goto',0x29:'goto/16',0x2a:'goto/32',0x32:'if-eq',0x33:'if-ne',0x34:'if-lt',0x35:'if-ge',0x36:'if-gt',0x37:'if-le',0x38:'if-eqz',0x39:'if-nez',0x3a:'if-ltz',0x3b:'if-gez',0x3c:'if-gtz',0x3d:'if-lez',0x2b:'packed-switch',0x2c:'sparse-switch'}
            i=0
            while i<len(units):
                op=units[i]&0xff
                if op in names:out.append({'unit':i,'opcode':hex(op),'kind':names[op],'raw':units[i:min(len(units),i+3)]})
                # conservative DEX width table for opcodes relevant here; unknown=>1 so only used as guard context, not decoding semantics
                if op in (0x29,0x32,0x33,0x34,0x35,0x36,0x37,0x38,0x39,0x3a,0x3b,0x3c,0x3d):w=2
                elif op in (0x2a,0x2b,0x2c):w=3
                elif op in tuple(range(0x6e,0x73))+tuple(range(0x74,0x79)):w=3
                elif op in (0x1a,):w=2
                elif op in (0x1b,):w=3
                else:w=1
                i+=w
        except Exception:pass
        return out

    def resolve_runtime_order(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V2.16 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V2.16 · resolviendo guards y callers de limpieza…')
        def work():
            rep={'app_version':'2.16.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'establish_runtime_order_and_guards_for_watchid_mac_and_clear_paths_locally',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known_from_v215':{'DeviceManager_a_signature':'a(String deviceName,String macAddress,long deviceId,boolean active)','mac_parameter':'param1 -> PREF_KEY_DEVICE_MAC','mac_callers':7,'ble_watchid_writer_callers':1,'account_writer_is_DeviceModel1_c':True,'clear_callers':2},
                 'methods':[],'caller_triggers':[],'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex_seen':0,'target_methods':0,'trigger_callers':0,'symbolized':0}
            def inspect(label,b):
                stats['dex_seen']+=1
                if not any(x in b for x in (b'DeviceModel',b'Application',b'BaseImmersiveActivity')):return
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                exact,err=v199.AppV199._exact_code_map(b,types)
                if err:rep.setdefault('exact_map_errors',[]).append({'dex':label,'error':err})
                refs={(m.get('class'),m.get('name')):m for m in methods if (m.get('class'),m.get('name')) in (TARGET_METHODS|CALLER_TARGETS)}
                for key,m in list(refs.items()):
                    if key not in TARGET_METHODS:continue
                    ex=exact.get(m.get('idx')) or {};code=ex.get('code_off');acc=ex.get('access_flags',0)
                    if not code:continue
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields);pmap=v180.AppV180._param_map(b,code,m,acc);sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except Exception as e:rep.setdefault('symbolic_errors',[]).append({'class':key[0],'method':key[1],'error':repr(e)});continue
                    stats['symbolized']+=1;stats['target_methods']+=1
                    events=[]
                    for inv in sym.get('invokes') or []:
                        t=inv.get('target') or {};cls=t.get('class');mn=t.get('method');args=[self._simple(a) for a in (inv.get('args') or [])]
                        interesting=(cls in (DM,PREF,TEXT,UI,DI,APP) or (cls and ('BluetoothReadDataEvent' in cls or 'DeviceModel' in cls)))
                        if interesting:events.append({'unit':inv.get('unit'),'class':cls,'method':mn,'args':args,'arg_regs':inv.get('arg_regs')})
                    rep['methods'].append({'dex':label,'class':key[0],'method':key[1],'method_idx':m.get('idx'),'proto':m.get('proto'),'incoming_registers':pmap,'events':events,'branches':self._branch_ops(b,code),'trace':(sym.get('trace') or [])[:3200]})
                encoded=[m for m in methods if (exact.get(m.get('idx')) or {}).get('code_off')]
                for tkey in CALLER_TARGETS:
                    tr=refs.get(tkey)
                    if not tr:continue
                    tidx=tr.get('idx')
                    for m in encoded:
                        ex=exact.get(m.get('idx')) or {};code=ex.get('code_off')
                        if not v215.AppV215._raw_invokes_method(b,code,tidx):continue
                        try:
                            sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields);pmap=v180.AppV180._param_map(b,code,m,ex.get('access_flags',0));sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                        except:continue
                        calls=[]
                        for inv in sym.get('invokes') or []:
                            t=inv.get('target') or {}
                            if t.get('class')==tkey[0] and t.get('method')==tkey[1]:calls.append({'unit':inv.get('unit'),'args':[self._simple(a) for a in (inv.get('args') or [])]})
                        if calls:
                            stats['trigger_callers']+=1;stats['symbolized']+=1
                            rep['caller_triggers'].append({'target_class':tkey[0],'target_method':tkey[1],'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'incoming_registers':pmap,'calls':calls,'branches':self._branch_ops(b,code),'trace':(sym.get('trace') or [])[:2400]})
                self._progress(f'V2.16 · {label.split("!")[-1]} · targets={stats["target_methods"]} · triggers={stats["trigger_callers"]}')
            def apk(name,data):
                with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                    dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                    for i,n in enumerate(dexes,1):
                        self._progress(f'V2.16 · DEX {i}/{len(dexes)} · {n}');inspect(name+'!'+n,z.read(n))
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
            account=next((r for r in rep['methods'] if r['class']==DEV1 and r['method']=='c'),None)
            ble=next((r for r in rep['methods'] if r['class']==APP and r['method']=='onBluetoothReadData'),None)
            clear1=next((r for r in rep['methods'] if r['class']==BASEACT and r['method']=='R1'),None)
            clear2=next((r for r in rep['methods'] if r['class']==DEV and r['method']=='j'),None)
            def seq(r):
                if not r:return []
                out=[]
                for e in r.get('events') or []:
                    if (e['class'],e['method']) in ((DM,'a'),(DM,'l'),(PREF,'h'),(TEXT,'isEmpty'),(UI,'e'),(DI,'b'),(APP,'h')):out.append({'unit':e['unit'],'class':e['class'],'method':e['method'],'args':e['args']})
                return out
            rep['scan_stats']=stats
            rep['resolved']={'account_writer_sequence':seq(account),'ble_writer_sequence':seq(ble),'clear_activity_sequence':seq(clear1),'clear_device_sequence':seq(clear2),
                'clear_trigger_callers':[x for x in rep['caller_triggers'] if x['target_method'] in ('j','R1')],
                'interpretation_gate':'Use branch lists + event order to decide whether account watchId overwrites BLE customerId in normal bind flow and whether clears occur only on explicit disconnect/logout paths.',
                'next':'If ordering is unambiguous, prepare the first safe guest-auth/activation metadata step with transient token handling only; no firmware download and no BLE/OTA writes.',
                'write_gate':'NO_DEVICE_WRITES_IN_THIS_VERSION'}
            rep['summary']={'target_methods':stats['target_methods'],'trigger_callers':stats['trigger_callers'],'symbolized':stats['symbolized'],'account_events':len(seq(account)),'ble_events':len(seq(ble)),'clear_triggers':len(rep['resolved']['clear_trigger_callers'])}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v216');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-runtime-order-v216.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V2.16 · falló: '+repr(err));return
            self.report={'utrawatch_runtime_order_v216':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep.get('summary') or {}
            self.status.set(f"V2.16 LISTO · targets={s.get('target_methods',0)} · triggers={s.get('trigger_callers',0)} · clear={s.get('clear_triggers',0)} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV216(root);root.mainloop()
