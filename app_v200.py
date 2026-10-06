import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v199 as v199
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='2.00.0'
HEALTH='Lcom/wtwd/cocousa/ui/module/main/health/HealthModel;'
TARGET_METHOD='h'
TARGET_IDX=16728

class AppV200(v199.AppV199):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V2.00')
        self._clean_v200();self._install_v200();self._restore_location_button()
        self.status.set('V2.00 lista · rastrea callers reales de HealthModel.h y sus 5 parámetros. Análisis local.')

    def _clean_v200(self):
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

    def _install_v200(self):
        top=self.root.winfo_children()[0]
        self.v200_button=ttk.Button(top,text='RASTREAR 5 VALORES REALES',command=self.trace_real_values)
        sib=top.winfo_children()
        try:self.v200_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v200_button.place(x=8,y=8)

    @staticmethod
    def _is_target(inv):
        t=inv.get('target') or {}
        return t.get('idx')==TARGET_IDX or (t.get('class')==HEALTH and t.get('method')==TARGET_METHOD)

    def trace_real_values(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V2.00 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V2.00 · rastreando callers exactos de HealthModel.h…')
        def work():
            rep={'app_version':'2.00.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'trace_exact_callers_of_HealthModel_h_and_resolve_parameter_origins_locally',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known_from_v199':{'method':'HealthModel.h','method_idx':16728,'signature':['String','double','double','String','String'],
                    'parameter_meaning':{'0':'area','1':'lat','2':'lng','3':'macAddress','4':'watchId'}},
                 'target_method':None,'callers':[],'value_maps':[],
                 'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex':0,'exact_methods':0,'callers':0}
            def inspect(label,b):
                stats['dex']+=1
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                exact,err=v199.AppV199._exact_code_map(b,types)
                if err:rep.setdefault('exact_map_errors',[]).append({'dex':label,'error':err})
                for m in methods:
                    ex=exact.get(m.get('idx'))
                    if not ex or not ex.get('code_off'):continue
                    code=ex['code_off'];acc=ex.get('access_flags',0);stats['exact_methods']+=1
                    try:sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                    except:continue
                    if m.get('class')==HEALTH and (m.get('idx')==TARGET_IDX or m.get('name')==TARGET_METHOD):
                        try:
                            pmap=v180.AppV180._param_map(b,code,m,acc);sym2=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                        except:pmap={};sym2=sym
                        rep['target_method']={'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'code_off':code,'incoming_registers':pmap,'trace':sym2.get('trace',[])[:500]}
                    hits=[x for x in (sym.get('invokes') or []) if self._is_target(x)]
                    if not hits:continue
                    try:
                        pmap=v180.AppV180._param_map(b,code,m,acc);sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                        hits=[x for x in (sym.get('invokes') or []) if self._is_target(x)]
                    except:pmap={}
                    stats['callers']+=1
                    rep['callers'].append({'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'code_off':code,'incoming_registers':pmap,'target_calls':hits,'trace':sym.get('trace',[])[:1600],'invokes':sym.get('invokes',[])[:700]})
                    for inv in hits:
                        vals=(inv.get('args') or [])[-5:]
                        rep['value_maps'].append({'caller_class':m.get('class'),'caller_method':m.get('name'),'caller_method_idx':m.get('idx'),'unit':inv.get('unit'),'arg_regs':inv.get('arg_regs'),'area':vals[0] if len(vals)>0 else None,'lat':vals[1] if len(vals)>1 else None,'lng':vals[2] if len(vals)>2 else None,'macAddress':vals[3] if len(vals)>3 else None,'watchId':vals[4] if len(vals)>4 else None})
            def apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                        for i,n in enumerate(dexes,1):
                            self._progress(f'V2.00 · DEX {i}/{len(dexes)} · {n}')
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
            rep['scan_stats']=stats
            rep['resolved']={'method':'HealthModel.h(String,double,double,String,String)','parameter_meaning':{'0':'area','1':'lat','2':'lng','3':'macAddress','4':'watchId'},'value_maps':rep['value_maps'],'ready_for_runtime_mapping':bool(rep['value_maps']),'next':'Inspect the concrete caller expressions for all five parameters and validate their runtime origins locally.','write_gate':'NO_DEVICE_WRITES_IN_THIS_VERSION'}
            rep['summary']={'callers':len(rep['callers']),'value_maps':len(rep['value_maps']),'exact_methods':stats['exact_methods']}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v200');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-parameter-origins-v200.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V2.00 · falló: '+repr(err));return
            self.report={'utrawatch_parameter_origins_v200':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep.get('summary') or {};self.status.set(f"V2.00 LISTO · callers={s.get('callers',0)} · mapas={s.get('value_maps',0)} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV200(root);root.mainloop()
