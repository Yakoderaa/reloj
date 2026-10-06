import io,json,os,zipfile
from datetime import datetime,timezone
import tkinter as tk
from tkinter import ttk,filedialog
import app as base
import app_v206 as v206
import app_v199 as v199
import app_v179 as v179
import app_v180 as v180
import app_v145 as v145

base.APP_VERSION='2.07.0'
DM='Lcom/wtwd/cocousa/manager/DeviceManager;'
HEALTH='Lcom/wtwd/cocousa/ui/module/main/health/HealthModel;'
GF='Lcom/wtwd/cocousa/entity/GaoFengLocationInfo;'

class AppV207(v206.AppV206):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V2.07')
        self._clean_v207();self._install_v207();self._restore_location_button()
        self.status.set('V2.07 lista · cierra quién escribe WATCH_ID y qué campo produce area. Sin red ni OTA.')

    def _clean_v207(self):
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

    def _install_v207(self):
        top=self.root.winfo_children()[0]
        self.v207_button=ttk.Button(top,text='CERRAR WRITER WATCHID + AREA',command=self.resolve_writer_area)
        sib=top.winfo_children()
        try:self.v207_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except:self.v207_button.place(x=8,y=8)

    def resolve_writer_area(self):
        ready,validation,vpath=self._ready_report()
        if not ready:self.status.set('V2.07 · falta validación BK3288.');return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen:return
        self.face_guard_enabled=False
        self.status.set('V2.07 · buscando sólo writers de PREF_KEY_WATCH_ID y GaoFengLocationInfo…')
        def work():
            rep={'app_version':'2.07.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                 'goal':'resolve_exact_PREF_KEY_WATCH_ID_writer_and_GaoFengLocationInfo_area_field_without_network_or_device_writes',
                 'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                 'known':{'watchId_getter':'DeviceManager.j()->PREF_KEY_WATCH_ID','mac_getter':'DeviceManager.d()->PREF_KEY_DEVICE_MAC','location_flow_closed_v205':True},
                 'watchid_writer_candidates':[],'gaofeng_methods':[],'health_l':[],'location_button_fix':{'requested':True,'restored_if_present':True},
                 'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}}
            stats={'dex_seen':0,'writer_candidates':0,'gaofeng_methods':0,'health_l':0}
            def inspect(label,b):
                stats['dex_seen']+=1
                try:strings,types,methods,classes,enc,fields=self._dex_full(b)
                except Exception as ex:rep.setdefault('errors',[]).append({'dex':label,'error':repr(ex)});return
                exact,err=v199.AppV199._exact_code_map(b,types)
                if err:rep.setdefault('exact_map_errors',[]).append({'dex':label,'error':err})
                for m in methods:
                    is_gf=m.get('class')==GF
                    is_health_l=(m.get('class')==HEALTH and m.get('name')=='l')
                    ex=exact.get(m.get('idx')) or {};code=ex.get('code_off');acc=ex.get('access_flags',0)
                    if not code:continue
                    pre=False
                    try:
                        raw=b[code:code+1200]
                        # symbolic only for exact small target classes, or methods whose nearby code references the preference string through normal symbolization
                        pre=is_gf or is_health_l
                    except:pass
                    if not pre and m.get('class')==DM: pre=True
                    if not pre:continue
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        pmap=v180.AppV180._param_map(b,code,m,acc)
                        sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    except Exception as ex2:
                        rep.setdefault('symbolic_errors',[]).append({'class':m.get('class'),'method':m.get('name'),'error':repr(ex2)});continue
                    row={'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'code_off':code,'incoming_registers':pmap,'invokes':sym.get('invokes') or [],'trace':(sym.get('trace') or [])[:2600]}
                    txt=json.dumps(row,ensure_ascii=False)
                    if is_gf:
                        rep['gaofeng_methods'].append(row);stats['gaofeng_methods']+=1
                    if is_health_l:
                        rep['health_l'].append(row);stats['health_l']+=1
                    if m.get('class')==DM and 'PREF_KEY_WATCH_ID' in txt and 'PrefUtil' in txt:
                        rep['watchid_writer_candidates'].append(row);stats['writer_candidates']+=1
                # second narrow pass: exact methods likely writing WATCH_ID based on symbol strings already present in class method bodies
                for m in methods:
                    ex=exact.get(m.get('idx')) or {};code=ex.get('code_off');acc=ex.get('access_flags',0)
                    if not code or m.get('class')==DM:continue
                    if stats['writer_candidates']>12:break
                    try:
                        sym=v179.AppV179._symbolic(b,code,strings,types,methods,fields)
                        txt=json.dumps(sym,ensure_ascii=False)
                    except:continue
                    if 'PREF_KEY_WATCH_ID' not in txt:continue
                    if 'PrefUtil' not in txt:continue
                    pmap=v180.AppV180._param_map(b,code,m,acc);sym=v180.AppV180._rewrite_unknown_regs(sym,pmap)
                    row={'dex':label,'class':m.get('class'),'method':m.get('name'),'method_idx':m.get('idx'),'proto':m.get('proto'),'code_off':code,'incoming_registers':pmap,'invokes':sym.get('invokes') or [],'trace':(sym.get('trace') or [])[:2600]}
                    if not any(x.get('method_idx')==row['method_idx'] and x.get('dex')==label for x in rep['watchid_writer_candidates']):
                        rep['watchid_writer_candidates'].append(row);stats['writer_candidates']+=1
            def apk(name,data):
                with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                    dexes=[n for n in z.namelist() if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex'))]
                    for i,n in enumerate(dexes,1):
                        self._progress(f'V2.07 · DEX {i}/{len(dexes)} · {n}')
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
            rep['resolved']={'watchid_writer_candidates_found':len(rep['watchid_writer_candidates']),
                'gaofeng_methods_found':len(rep['gaofeng_methods']),'health_l_found':len(rep['health_l']),
                'next':'Use the confirmed WATCH_ID writer plus GaoFengLocationInfo/HealthModel.l field flow to construct the exact activation body in the next version. Keep firmware and OTA disabled.',
                'write_gate':'NO_DEVICE_WRITES_IN_THIS_VERSION'}
            rep['summary']={'watchid_writer_candidates':len(rep['watchid_writer_candidates']),'gaofeng_methods':len(rep['gaofeng_methods']),'health_l':len(rep['health_l'])}
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v207');os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-watchid-writer-area-v207.json');rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f:json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep
        def done(rep,err):
            if err:self.status.set('V2.07 · falló: '+repr(err));return
            self.report={'utrawatch_watchid_writer_area_v207':rep};self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(t);self.root.update_idletasks()
            except:pass
            s=rep.get('summary') or {}
            self.status.set(f"V2.07 LISTO · writer={s.get('watchid_writer_candidates',0)} · GaoFeng={s.get('gaofeng_methods',0)} · l={s.get('health_l',0)} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk();AppV207(root);root.mainloop()
