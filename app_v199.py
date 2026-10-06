import io,json,os,zipfile,struct
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v198 as v198
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='1.99.0'
HEALTH='Lcom/wtwd/cocousa/ui/module/main/health/HealthModel;'
HEALTH4='Lcom/wtwd/cocousa/ui/module/main/health/HealthModel$4;'
TARGETINFO='Lcom/wtwd/cocousa/entity/device/TargetInfo;'
BASEAPI='Lcom/wtwd/cocousa/api/BaseApi;'
ACT_METHOD='L'

class AppV199(v198.AppV198):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.99')
        self._clean_v199();self._install_v199();self._restore_location_button()
        self.status.set('V1.99 lista · corrige mapa DEX método→code_off para activationDevice. Sin red ni OTA.')

    def _clean_v199(self):
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

    def _install_v199(self):
        top=self.root.winfo_children()[0]
        self.v199_button=ttk.Button(top,text='CORREGIR MAPA DEX ACTIVATION',command=self.resolve_exact_dex_map)
        sib=top.winfo_children()
        try:self.v199_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v199_button.place(x=8,y=8)

    @staticmethod
    def _u32(b,o):return struct.unpack_from('<I',b,o)[0]

    @staticmethod
    def _uleb(b,o):
        v=0;s=0
        for _ in range(5):
            x=b[o];o+=1;v|=(x&0x7f)<<s
            if not (x&0x80):return v,o
            s+=7
        return v,o

    @classmethod
    def _exact_code_map(cls,b,types):
        out={}
        try:
            csz=cls._u32(b,0x60);coff=cls._u32(b,0x64)
            for i in range(csz):
                q=coff+i*32;ci=cls._u32(b,q);ctype=types[ci] if ci<len(types) else str(ci);data_off=cls._u32(b,q+24)
                if not data_off:continue
                p=data_off
                sf,p=cls._uleb(b,p);inf,p=cls._uleb(b,p);dm,p=cls._uleb(b,p);vm,p=cls._uleb(b,p)
                fidx=0
                for _ in range(sf+inf):
                    d,p=cls._uleb(b,p);_,p=cls._uleb(b,p);fidx+=d
                for kind,count in (('direct',dm),('virtual',vm)):
                    midx=0
                    for _ in range(count):
                        d,p=cls._uleb(b,p);acc,p=cls._uleb(b,p);code,p=cls._uleb(b,p);midx+=d
                        out[midx]={'code_off':code,'access_flags':acc,'kind':kind,'class':ctype}
        except Exception as ex:
            return out,repr(ex)
        return out,None

    @staticmethod
    def _keys_from_trace(trace):
        keys=[]
        for ev in trace or []:
            if ev.get('kind')!='invoke':continue
            inv=ev.get('invoke') or {};t=inv.get('target') or {};args=inv.get('args') or []
            if t.get('class') in ('Ljava/util/HashMap;','Ljava/util/Map;') and t.get('method')=='put' and len(args)>=3:
                k=args[-2]
                if isinstance(k,dict) and k.get('kind')=='string':keys.append(k.get('value'))
        return keys

    def resolve_exact_dex_map(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V1.99 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.99 · reconstruyendo class_data_item y code_off reales…')
        def work():
            rep={'app_version':'1.99.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'repair_exact_dex_method_to_code_off_mapping_then_identify_real_activationDevice_method_signature_and_parameter_sources',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known_from_v198':{'body_keys':['lat','lng','macAddress','watchId'],'mapping_warning':'HealthModel.g metadata conflicted with activation bytecode'},
                 'activation_candidates':[],'health_methods_exact':[],'health4_methods_exact':[],'targetinfo_methods_exact':[],
                 'mapping_diffs':[],'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex':0,'exact_methods':0,'activation_candidates':0}
            wanted={HEALTH,HEALTH4,TARGETINFO}
            def inspect(label,b):
                stats['dex']+=1
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                exact,err=self._exact_code_map(b,types)
                if err:rep.setdefault('exact_map_errors',[]).append({'dex':label,'error':err})
                legacy={mid:(code,kind,acc) for _,mid,code,kind,acc in enc}
                for m in methods:
                    mid=m.get('idx');clsname=m.get('class')
                    if mid not in exact:continue
                    ex=exact[mid];code=ex.get('code_off',0);acc=ex.get('access_flags',0)
                    if not code:continue
                    stats['exact_methods']+=1
                    old=legacy.get(mid,(0,None,None))[0]
                    if old!=code and clsname in wanted:
                        rep['mapping_diffs'].append({'dex':label,'method_idx':mid,'class':clsname,'method':m.get('name'),'legacy_code_off':old,'exact_code_off':code})
                    if clsname not in wanted:continue
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc);sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except Exception as ex2:
                        rep.setdefault('symbolic_errors',[]).append({'dex':label,'method_idx':mid,'error':repr(ex2)});continue
                    row={'dex':label,'class':clsname,'method':m.get('name'),'method_idx':mid,'proto':m.get('proto'),'code_off':code,
                         'access_flags':acc,'kind':ex.get('kind'),'incoming_registers':pmap,'trace':sym.get('trace',[])[:1400],
                         'invokes':sym.get('invokes',[])[:600],'returns':sym.get('returns',[])[:100],
                         'hashmap_keys':self._keys_from_trace(sym.get('trace',[]))}
                    if clsname==HEALTH:rep['health_methods_exact'].append(row)
                    elif clsname==HEALTH4:rep['health4_methods_exact'].append(row)
                    elif clsname==TARGETINFO:rep['targetinfo_methods_exact'].append(row)
                    act_calls=[]
                    for inv in sym.get('invokes',[]):
                        t=inv.get('target') or {}
                        if t.get('class')==BASEAPI and t.get('method')==ACT_METHOD:act_calls.append(inv)
                    keys=set(row['hashmap_keys'])
                    if act_calls or {'lat','lng','macAddress','watchId'}.issubset(keys):
                        stats['activation_candidates']+=1
                        rep['activation_candidates'].append({**row,'activation_calls':act_calls})
            def apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                        for i,n in enumerate(dexes,1):
                            self._progress(f'V1.99 · DEX {i}/{len(dexes)} · {n}')
                            inspect(name+'!'+n,z.read(n))
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
            compact=[]
            for c in rep['activation_candidates']:
                compact.append({'class':c.get('class'),'method':c.get('method'),'method_idx':c.get('method_idx'),'proto':c.get('proto'),
                                'code_off':c.get('code_off'),'incoming_registers':c.get('incoming_registers'),'hashmap_keys':c.get('hashmap_keys'),
                                'activation_calls':c.get('activation_calls')})
            rep['scan_stats']=stats
            rep['resolved']={'activation_candidates_compact':compact,'mapping_diff_count':len(rep['mapping_diffs']),
                             'ready_for_real_value_mapping':bool(compact),
                             'next':'Use the corrected activation method signature/incoming registers to map lat/lng/macAddress/watchId to real runtime values; only then perform one explicit activation request.',
                             'write_gate':'KEEP_OTA_DISABLED_UNTIL_OFFICIAL_FIRMWARE_FILE_VALIDATION_SUCCEEDS'}
            rep['summary']={'activation_candidates':len(compact),'mapping_diffs':len(rep['mapping_diffs']),
                            'health_methods':len(rep['health_methods_exact']),'health4_methods':len(rep['health4_methods_exact']),
                            'targetinfo_methods':len(rep['targetinfo_methods_exact'])}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v199');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-exact-dex-activation-v199.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.99 · falló: '+repr(err));return
            self.report={'utrawatch_exact_dex_activation_v199':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep.get('summary') or {}
            self.status.set(f"V1.99 LISTO · candidatos={s.get('activation_candidates',0)} · diffs={s.get('mapping_diffs',0)} · red/OTA=0 · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV199(root);root.mainloop()
