import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v175 as v175
import app_v145 as v145

base.APP_VERSION='1.76.0'

TARGETS=(
    'otacommandgenerator','otadataprovider','otamanager','bleconnectservice',
    'zkbleotadatalistener','zkbluetoothotadataevent','zkotaerror','zkotastate',
    'hardwareupdatemodel','hardwareupdatepresenter','hardwareupdatecontract'
)

class AppV176(v175.AppV175):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.76')
        self._clean_v176();self._install_v176()
        self.status.set('V1.76 lista · reconstruye grafo OTA exacto de UtraWatch. Sin red ni escrituras.')
    def _clean_v176(self):
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
    def _install_v176(self):
        top=self.root.winfo_children()[0]
        self.v176_button=ttk.Button(top,text='RECONSTRUIR GRAFO OTA',command=self.map_ota_graph)
        sib=top.winfo_children()
        try:self.v176_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v176_button.place(x=8,y=8)
    def map_ota_graph(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V1.76 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V1.76 · reconstruyendo clases, llamadas y constantes OTA…')
        def work():
            rep={
                'app_version':'1.76.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                'goal':'reconstruct_exact_utrawatch_ota_command_and_transport_graph_without_network_or_device_writes',
                'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                'target_classes':[],'target_methods':[],'callers_of_targets':[],'calls_from_targets':[],
                'ota_types':[],'ota_strings':[],'target_fields':[],
                'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}
            }
            seen_strings=set();seen_types=set();seen_fields=set();seen_methods=set();seen_callers=set();seen_edges=set()
            def hit(s):
                q=str(s or '').lower()
                return any(k in q for k in TARGETS)
            def method_row(label,m,code,kind,acc,d):
                return {'dex':label,'class':m['class'],'method':m['name'],'method_idx':m['idx'],'proto':m.get('proto'),
                        'kind':kind,'access_flags':acc,'code_off':code,'strings':d.get('strings',[]),
                        'calls':d.get('calls',[]),'fields':d.get('fields',[]),'consts':d.get('consts',[]),
                        'raw_code_hex':d.get('raw_code_hex','')}
            def inspect(label,b):
                try: strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex: rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                em={mid:(code,kind,acc) for _,mid,code,kind,acc in enc}
                target_method_ids=set()
                target_class_names=set()
                for t in types:
                    if hit(t) or ('ota' in str(t).lower() and 'com/wtwd' in str(t).lower()):
                        key=(label,t)
                        if key not in seen_types:
                            seen_types.add(key);rep['ota_types'].append({'dex':label,'type':t})
                        target_class_names.add(t)
                for c in classes:
                    cs=str(c)
                    if hit(cs) or ('ota' in cs.lower() and 'com/wtwd' in cs.lower()):
                        key=(label,cs)
                        if key not in seen_types:
                            seen_types.add(key);rep['target_classes'].append({'dex':label,'class':cs})
                        target_class_names.add(cs)
                for s in strings:
                    sl=s.lower()
                    if any(k in sl for k in ('otacommandgenerator','otadataprovider','otamanager','zkbluetoothotadataevent','zkbleotadatalistener','zkotaerror','zkotastate','firmware_download','ota_check_file')):
                        if s not in seen_strings:
                            seen_strings.add(s);rep['ota_strings'].append(s)
                for f in fields:
                    txt=' '.join(str(f.get(k,'')) for k in ('class','name','type'))
                    if hit(txt) or ('ota' in txt.lower() and 'com/wtwd' in txt.lower()):
                        q=(label,f.get('idx'))
                        if q not in seen_fields:
                            seen_fields.add(q);rep['target_fields'].append({'dex':label,**f})
                for m in methods:
                    cls=m.get('class','');name=m.get('name','');proto=m.get('proto') or {}
                    sig=' '.join([str(cls),str(name),json.dumps(proto,ensure_ascii=False)])
                    if hit(sig) or ('ota' in sig.lower() and 'com/wtwd' in sig.lower()):
                        target_method_ids.add(m['idx'])
                details_cache={}
                for m in methods:
                    code,kind,acc=em.get(m['idx'],(0,None,None))
                    if not code:continue
                    need=m['idx'] in target_method_ids
                    d=None
                    if need:
                        d=self._details(b,code,strings,methods,fields);details_cache[m['idx']]=d
                        r=method_row(label,m,code,kind,acc,d);q=(label,m['idx'])
                        if q not in seen_methods:
                            seen_methods.add(q);rep['target_methods'].append(r)
                        for call in d.get('calls',[]):
                            edge=(label,m['idx'],call.get('idx'))
                            if edge not in seen_edges:
                                seen_edges.add(edge);rep['calls_from_targets'].append({'dex':label,'from_class':m['class'],'from_method':m['name'],'from_idx':m['idx'],'call':call})
                # One-hop reverse callers: only decode methods that actually call a target method.
                for m in methods:
                    code,kind,acc=em.get(m['idx'],(0,None,None))
                    if not code or m['idx'] in target_method_ids:continue
                    try:d=self._details(b,code,strings,methods,fields)
                    except:continue
                    calls=d.get('calls',[])
                    if any(c.get('idx') in target_method_ids or hit(c.get('class','')) for c in calls):
                        q=(label,m['idx'])
                        if q not in seen_callers:
                            seen_callers.add(q);rep['callers_of_targets'].append(method_row(label,m,code,kind,acc,d))
            def apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data)) as z:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')):inspect(name+'!'+n,z.read(n))
                except Exception as ex:rep.setdefault('errors',[]).append({'apk':name,'error':repr(ex)})
            if zipfile.is_zipfile(chosen):
                with zipfile.ZipFile(chosen) as z:
                    apks=[n for n in z.namelist() if n.lower().endswith('.apk')]
                    if apks:
                        preferred=[n for n in apks if 'com.wtwd.utrawatch' in n.lower() or os.path.basename(n).lower().startswith(('base','master'))]
                        for n in (preferred or apks[:1]):apk(n,z.read(n))
                    else:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')):inspect(n,z.read(n))
            else:
                with open(chosen,'rb') as f:apk(os.path.basename(chosen),f.read())
            for k,lim in [('target_classes',100),('target_methods',300),('callers_of_targets',300),('calls_from_targets',600),('ota_types',200),('ota_strings',300),('target_fields',300)]:
                rep[k]=rep[k][:lim]
            rep['summary']={
                'target_class_count':len(rep['target_classes']),'target_method_count':len(rep['target_methods']),
                'reverse_caller_count':len(rep['callers_of_targets']),'forward_call_count':len(rep['calls_from_targets']),
                'ota_type_count':len(rep['ota_types']),'target_field_count':len(rep['target_fields']),
                'next':'Use exact target/caller graph to recover command generator framing, data provider chunking, state/error ACK handling, and the BleConnectService OTA entry point before any firmware write is enabled.'
            }
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v176');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-ota-graph-v176.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V1.76 · falló: '+repr(err));return
            self.report={'ota_graph_v176':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep['summary'];self.status.set(f"V1.76 LISTO · clases={s['target_class_count']} · métodos={s['target_method_count']} · callers={s['reverse_caller_count']} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV176(root);root.mainloop()
