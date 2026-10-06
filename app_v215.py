import io,json,os,zipfile,struct
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v214 as v214
import app_v199 as v199
import app_v179 as v179
import app_v180 as v180
import app_v210 as v210
import app_v145 as v145

base.APP_VERSION='2.15.0'
DM='Lcom/wtwd/cocousa/manager/DeviceManager;'
APP='Lcom/wtwd/cocousa/ui/module/application/Application;'
DEV1='Lcom/wtwd/cocousa/ui/module/main/device/DeviceModel$1;'
TARGETS=[(DM,'a'),(APP,'h'),(DEV1,'c'),(DM,'l')]

class AppV215(v214.AppV214):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V2.15')
        self._clean_v215();self._install_v215();self._restore_location_button()
        self.status.set('V2.15 lista · cierra orden/guards de writers y origen exacto del MAC. Sin red ni OTA.')

    def _clean_v215(self):
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

    def _install_v215(self):
        top=self.root.winfo_children()[0]
        self.v215_button=ttk.Button(top,text='CERRAR PRECEDENCIA + MAC',command=self.resolve_precedence)
        sib=top.winfo_children()
        try:self.v215_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v215_button.place(x=8,y=8)

    @staticmethod
    def _raw_invokes_method(b,code_off,target_idx):
        try:
            if not code_off or code_off+16>len(b):return False
            insns_size=struct.unpack_from('<I',b,code_off+12)[0]
            start=code_off+16;end=min(len(b),start+insns_size*2)
            units=struct.unpack_from('<'+'H'*((end-start)//2),b,start)
            invoke_ops=set(range(0x6e,0x73))|set(range(0x74,0x79))
            return any((units[i]&0xff) in invoke_ops and units[i+1]==target_idx for i in range(max(0,len(units)-1)))
        except:return False

    @staticmethod
    def _simple(a):
        try:return v210.AppV210._simple(a)
        except:return a

    def resolve_precedence(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V2.15 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V2.15 · buscando callers exactos de 4 writers…')
        def work():
            rep={'app_version':'2.15.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'prove_watchid_writer_precedence_and_exact_DeviceManager_a_mac_origin_locally',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known_from_v214':{'activation_slots_closed':True,'area':'WEATHER','lat':'Double.parseDouble(S0 param1)','lng':'Double.parseDouble(S0 param2)','mac':'PREF_KEY_DEVICE_MAC','watchId':'PREF_KEY_WATCH_ID','writers':{'ble':'Application.h -> String.valueOf(DeviceInfo.b())','account':'DeviceModel$1.c -> UserDeviceInfo.e()','clear':'DeviceManager.l -> empty'}},
                 'target_refs':[],'caller_candidates':[],'confirmed_callers':[],
                 'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex_seen':0,'target_refs':0,'methods_scanned':0,'raw_candidates':0,'confirmed_callers':0,'symbolized':0}

            def inspect(label,b):
                stats['dex_seen']+=1
                if not any(x in b for x in (b'DeviceManager',b'Application',b'DeviceModel$1')):return
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                exact,err=v199.AppV199._exact_code_map(b,types)
                if err:rep.setdefault('exact_map_errors',[]).append({'dex':label,'error':err})
                refs=[m for m in methods if (m.get('class'),m.get('name')) in TARGETS]
                if not refs:return
                encoded=[m for m in methods if (exact.get(m.get('idx')) or {}).get('code_off')]
                stats['methods_scanned']+=len(encoded)
                for tr in refs:
                    tidx=tr.get('idx');tkey=(tr.get('class'),tr.get('name'))
                    rep['target_refs'].append({'dex':label,'class':tkey[0],'method':tkey[1],'method_idx':tidx,'proto':tr.get('proto')});stats['target_refs']+=1
                    for pos,m in enumerate(encoded,1):
                        ex=exact.get(m.get('idx')) or {};code=ex.get('code_off')
                        if not self._raw_invokes_method(b,code,tidx):continue
                        stats['raw_candidates']+=1
                        cand={'dex':label,'target_class':tkey[0],'target_method':tkey[1],'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'code_off':code}
                        rep['caller_candidates'].append(cand)
                        try:
                            acc=ex.get('access_flags',0);sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                            pmap=v180.AppV180._param_map(b,code,m,acc);sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                        except Exception as e:cand['symbolic_error']=repr(e);continue
                        stats['symbolized']+=1
                        calls=[]
                        for inv in sym.get('invokes') or []:
                            t=inv.get('target') or {}
                            if t.get('class')==tkey[0] and t.get('method')==tkey[1]:
                                calls.append({'unit':inv.get('unit'),'target':t,'arg_regs':inv.get('arg_regs'),'args':[self._simple(a) for a in (inv.get('args') or [])],'raw_args':inv.get('args') or []})
                        if not calls:continue
                        stats['confirmed_callers']+=1
                        trace=sym.get('trace') or []
                        rep['confirmed_callers'].append({'dex':label,'target_class':tkey[0],'target_method':tkey[1],'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'incoming_registers':pmap,'target_calls':calls,'trace':trace[:4500]})
                self._progress(f'V2.15 · {label.split("!")[-1]} · callers={stats["confirmed_callers"]}')

            def apk(name,data):
                with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                    dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                    for i,n in enumerate(dexes,1):
                        self._progress(f'V2.15 · DEX {i}/{len(dexes)} · {n}')
                        inspect(name+'!'+n,z.read(n))
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

            mac_callers=[];ble_callers=[];account_callers=[];clear_callers=[]
            for r in rep['confirmed_callers']:
                key=(r.get('target_class'),r.get('target_method'))
                if key==(DM,'a'):mac_callers.append(r)
                elif key==(APP,'h'):ble_callers.append(r)
                elif key==(DEV1,'c'):account_callers.append(r)
                elif key==(DM,'l'):clear_callers.append(r)
            rep['scan_stats']=stats
            rep['resolved']={'DeviceManager_a_signature':'a(String deviceName,String macAddress,long deviceId,boolean active)',
                'DeviceManager_a_mac_parameter':'param1 String -> PREF_KEY_DEVICE_MAC',
                'mac_writer_callers':len(mac_callers),'ble_watchid_writer_callers':len(ble_callers),'account_watchid_writer_callers':len(account_callers),'clear_callers':len(clear_callers),
                'caller_groups':{'mac':mac_callers,'ble_watchId':ble_callers,'account_watchId':account_callers,'clear':clear_callers},
                'next':'Use confirmed caller traces and branch guards to establish actual runtime ordering. If precedence becomes unambiguous, next version may perform the first read-only activation metadata/auth preparation; still no firmware or OTA writes.',
                'write_gate':'NO_DEVICE_WRITES_IN_THIS_VERSION'}
            rep['summary']={'target_refs':stats['target_refs'],'raw_candidates':stats['raw_candidates'],'confirmed_callers':stats['confirmed_callers'],'symbolized':stats['symbolized'],'mac_callers':len(mac_callers),'ble_callers':len(ble_callers),'account_callers':len(account_callers),'clear_callers':len(clear_callers)}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v215');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-writer-precedence-v215.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V2.15 · falló: '+repr(err));return
            self.report={'utrawatch_writer_precedence_v215':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep.get('summary') or {}
            self.status.set(f"V2.15 LISTO · callers={s.get('confirmed_callers',0)} · MAC={s.get('mac_callers',0)} · BLE={s.get('ble_callers',0)} · cuenta={s.get('account_callers',0)} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV215(root);root.mainloop()
