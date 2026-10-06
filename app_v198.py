import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v197 as v197
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='1.98.0'
HEALTH='Lcom/wtwd/cocousa/ui/module/main/health/HealthModel;'
TARGET_NAME='g'
TARGET_IDX=16727

class AppV198(v197.AppV197):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.98')
        self._clean_v198();self._install_v198();self._restore_location_button()
        self.status.set('V1.98 lista · rastrea valores exactos de activationDevice. Sin red ni OTA.')

    def _clean_v198(self):
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

    def _install_v198(self):
        top=self.root.winfo_children()[0]
        self.v198_button=ttk.Button(top,text='RASTREAR VALORES ACTIVATION',command=self.trace_activation_values)
        sib=top.winfo_children()
        try:self.v198_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v198_button.place(x=8,y=8)

    @staticmethod
    def _mentions_target(inv):
        t=inv.get('target') or {}
        return t.get('idx')==TARGET_IDX or (t.get('class')==HEALTH and t.get('method')==TARGET_NAME)

    def trace_activation_values(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V1.98 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.98 · rastreando HealthModel.g y sus callers…')
        def work():
            rep={'app_version':'1.98.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'resolve_exact_value_origins_for_activationDevice_lat_lng_macAddress_watchId_by_tracing_HealthModel_g_and_all_callers_without_network_or_ota',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known_from_v197':{'activation_body_keys':['lat','lng','macAddress','watchId'],'health_method':'HealthModel.g','method_idx':TARGET_IDX},
                 'health_method':None,'health_class_methods':[],'callers':[],'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex':0,'methods_symbolic':0,'callers':0,'health_methods':0}
            def inspect(label,b):
                stats['dex']+=1
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                em={mid:(code,kind,acc) for _,mid,code,kind,acc in enc}
                # First inspect every HealthModel method so field/getter setup around g is visible.
                for m in methods:
                    if m.get('class')!=HEALTH:continue
                    code,kind,acc=em.get(m.get('idx'),(0,None,None))
                    if not code:continue
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc);sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except Exception as ex:
                        rep.setdefault('symbolic_errors',[]).append({'dex':label,'method_idx':m.get('idx'),'error':repr(ex)});continue
                    stats['methods_symbolic']+=1;stats['health_methods']+=1
                    row={'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'access_flags':acc,'incoming_registers':pmap,
                         'trace':sym.get('trace',[])[:1200],'invokes':sym.get('invokes',[])[:500],'returns':sym.get('returns',[])[:80],
                         'field_reads':sym.get('critical_field_reads',[])[:160],'field_writes':sym.get('critical_field_writes',[])[:160]}
                    rep['health_class_methods'].append(row)
                    if m.get('idx')==TARGET_IDX or m.get('name')==TARGET_NAME:
                        # prefer exact index but keep the named method too for diagnostics
                        if rep['health_method'] is None or m.get('idx')==TARGET_IDX:rep['health_method']=row
                # Then inspect every method that invokes HealthModel.g.
                self._progress(f'V1.98 · {label} · buscando callers…')
                for m in methods:
                    code,kind,acc=em.get(m.get('idx'),(0,None,None))
                    if not code:continue
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                    except:continue
                    hits=[inv for inv in (sym.get('invokes') or []) if self._mentions_target(inv)]
                    if not hits:continue
                    try:
                        pmap=v180.AppV180._param_map(b,code,m,acc);sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                        hits=[inv for inv in (sym.get('invokes') or []) if self._mentions_target(inv)]
                    except:pmap={}
                    stats['methods_symbolic']+=1;stats['callers']+=1
                    rep['callers'].append({'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'access_flags':acc,
                                           'incoming_registers':pmap,'target_calls':hits,'trace':sym.get('trace',[])[:1200],
                                           'invokes':sym.get('invokes',[])[:500],'returns':sym.get('returns',[])[:80]})
            def apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                        for i,n in enumerate(dexes,1):
                            self._progress(f'V1.98 · DEX {i}/{len(dexes)} · {n}')
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

            # Extract the exact register-producing events immediately before the 4 puts in HealthModel.g.
            hm=rep.get('health_method') or {}
            trace=hm.get('trace') or []
            puts=[]
            for ev in trace:
                if ev.get('kind')=='invoke':
                    inv=ev.get('invoke') or {};t=inv.get('target') or {};args=inv.get('args') or []
                    if t.get('class') in ('Ljava/util/HashMap;','Ljava/util/Map;') and t.get('method')=='put' and len(args)>=3:
                        k=args[-2]
                        if isinstance(k,dict) and k.get('kind')=='string' and k.get('value') in ('lat','lng','macAddress','watchId'):
                            puts.append({'unit':ev.get('unit'),'key':k.get('value'),'arg_regs':inv.get('arg_regs'),'value':args[-1]})
            caller_args=[]
            for c in rep['callers']:
                for inv in c.get('target_calls') or []:
                    caller_args.append({'caller_class':c.get('class'),'caller_method':c.get('method'),'caller_method_idx':c.get('method_idx'),
                                        'unit':inv.get('unit'),'arg_regs':inv.get('arg_regs'),'args':inv.get('args')})
            rep['scan_stats']=stats
            rep['resolved']={'activation_body_keys':['lat','lng','macAddress','watchId'],'health_g_incoming_registers':hm.get('incoming_registers',{}),
                             'activation_put_values':puts,'health_g_callers':caller_args,
                             'ready_to_map_real_values':bool(hm and puts and caller_args),
                             'next':'Use these exact caller arguments and register-producing trace events to map lat/lng/macAddress/watchId to real selected-watch/location values before one explicit activation request.',
                             'write_gate':'KEEP_OTA_DISABLED_UNTIL_OFFICIAL_FIRMWARE_FILE_VALIDATION_SUCCEEDS'}
            rep['summary']={'health_methods':stats['health_methods'],'callers':stats['callers'],'activation_puts':len(puts),'methods_symbolic':stats['methods_symbolic']}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v198');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-activation-values-v198.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.98 · falló: '+repr(err));return
            self.report={'utrawatch_activation_values_v198':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep.get('summary') or {}
            self.status.set(f"V1.98 LISTO · callers={s.get('callers',0)} · puts={s.get('activation_puts',0)} · red/OTA=0 · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV198(root);root.mainloop()
