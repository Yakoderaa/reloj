import io,json,os,zipfile,struct
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v207 as v207
import app_v199 as v199
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='2.08.0'
DM='Lcom/wtwd/cocousa/manager/DeviceManager;'
HEALTH='Lcom/wtwd/cocousa/ui/module/main/health/HealthModel;'
GF='Lcom/wtwd/cocousa/entity/GaoFengLocationInfo;'
KEY='PREF_KEY_WATCH_ID'

class AppV208(v207.AppV207):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V2.08')
        self._clean_v208();self._install_v208();self._restore_location_button()
        self.status.set('V2.08 lista · xref binario de WATCH_ID; simboliza sólo coincidencias reales.')

    def _clean_v208(self):
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
                except: pass
        walk(self.root)

    def _install_v208(self):
        top=self.root.winfo_children()[0]
        self.v208_button=ttk.Button(top,text='XREF RÁPIDO WATCHID + AREA',command=self.resolve_fast)
        sib=top.winfo_children()
        try:self.v208_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v208_button.place(x=8,y=8)

    @staticmethod
    def _code_refs_string(b,code_off,string_idx):
        try:
            size=struct.unpack_from('<I',b,code_off+12)[0]
            start=code_off+16; end=start+size*2
            if end>len(b):return False
            data=b[start:end]
            units=len(data)//2
            for i in range(units):
                u=struct.unpack_from('<H',data,i*2)[0]; op=u & 0xff
                if op==0x1a and i+1<units:
                    if struct.unpack_from('<H',data,(i+1)*2)[0]==string_idx:return True
                elif op==0x1b and i+2<units:
                    if struct.unpack_from('<I',data,(i+1)*2)[0]==string_idx:return True
        except:pass
        return False

    def resolve_fast(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V2.08 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V2.08 · localizando xrefs crudos de WATCH_ID…')
        def work():
            rep={'app_version':'2.08.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'find_exact_PREF_KEY_WATCH_ID_writers_with_raw_const_string_xref_then_symbolize_only_matches',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known':{'watchId_getter':'DeviceManager.j()->PREF_KEY_WATCH_ID','mac_getter':'DeviceManager.d()->PREF_KEY_DEVICE_MAC'},
                 'raw_watchid_xrefs':[],'confirmed_watchid_methods':[],'gaofeng_methods':[],'health_l':[],
                 'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex_seen':0,'methods_checked_raw':0,'raw_xrefs':0,'symbolized':0}
            def inspect(label,b):
                stats['dex_seen']+=1
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                try:key_idx=next(i for i,s in enumerate(strings) if s==KEY)
                except StopIteration:key_idx=None
                target_classes={GF}
                exact,err=v199.AppV199._exact_code_map(b,types)
                if err:rep.setdefault('exact_map_errors',[]).append({'dex':label,'error':err})
                candidates=[]
                for m in methods:
                    ex=exact.get(m.get('idx')) or {}; code=ex.get('code_off'); acc=ex.get('access_flags',0)
                    if not code:continue
                    stats['methods_checked_raw']+=1
                    is_gf=m.get('class')==GF
                    is_l=m.get('class')==HEALTH and m.get('name')=='l'
                    hit=(key_idx is not None and self._code_refs_string(b,code,key_idx))
                    if hit:
                        rep['raw_watchid_xrefs'].append({'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'code_off':code})
                        stats['raw_xrefs']+=1
                    if hit or is_gf or is_l:
                        candidates.append((m,code,acc,hit,is_gf,is_l))
                self._progress(f'V2.08 · {label.split("!")[-1]} · xrefs={stats["raw_xrefs"]}')
                for m,code,acc,hit,is_gf,is_l in candidates:
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc)
                        sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except Exception as ex2:
                        rep.setdefault('symbolic_errors',[]).append({'class':m.get('class'),'method':m.get('name'),'error':repr(ex2)});continue
                    row={'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'code_off':code,'incoming_registers':pmap,'invokes':sym.get('invokes') or [],'trace':(sym.get('trace') or [])[:3200]}
                    stats['symbolized']+=1
                    if hit:rep['confirmed_watchid_methods'].append(row)
                    if is_gf:rep['gaofeng_methods'].append(row)
                    if is_l:rep['health_l'].append(row)
            def apk(name,data):
                with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                    dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                    for i,n in enumerate(dexes,1):
                        self._progress(f'V2.08 · DEX {i}/{len(dexes)} · {n}')
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
            rep['scan_stats']=stats
            rep['resolved']={'watchid_xrefs_found':len(rep['raw_watchid_xrefs']),'confirmed_watchid_methods':len(rep['confirmed_watchid_methods']),
                'gaofeng_methods_found':len(rep['gaofeng_methods']),'health_l_found':len(rep['health_l']),
                'next':'Inspect only confirmed WATCH_ID xrefs and area field flow; no broad symbolic scan is needed.',
                'write_gate':'NO_DEVICE_WRITES_IN_THIS_VERSION'}
            rep['summary']={'watchid_xrefs':len(rep['raw_watchid_xrefs']),'confirmed_watchid_methods':len(rep['confirmed_watchid_methods']),'gaofeng_methods':len(rep['gaofeng_methods']),'health_l':len(rep['health_l'])}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v208');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-watchid-xref-area-v208.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V2.08 · falló: '+repr(err));return
            self.report={'utrawatch_watchid_xref_area_v208':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep.get('summary') or {}
            self.status.set(f"V2.08 LISTO · xrefs={s.get('watchid_xrefs',0)} · simbolizados={s.get('confirmed_watchid_methods',0)} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV208(root);root.mainloop()
