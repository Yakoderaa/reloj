import io, json, os, zipfile
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, filedialog
import app as base
import app_v166 as v166
import app_v145 as v145

base.APP_VERSION='1.67.0'

TARGET_CLASSES=(
    'Lcom/wtwd/cocousa/ble/ZKBleOtaManager;',
    'Lcom/wtwd/cocousa/ble/BleConnectService;',
    'Lcom/bluetrum/fota/bluetooth/h;',
)
TARGET_BLE_METHODS={'O','R','V','W','X','Y'}

class AppV167(v166.AppV166):
    def __init__(self,root):
        super().__init__(root)
        root.title('Reloj Lab V1.67')
        self._clean_v167(); self._install_v167()
        self.status.set('V1.67 lista · traza ZKBleOtaManager, BleConnectService y Bluetrum FOTA para reconstruir el flujo OTA exacto.')

    def _clean_v167(self):
        keep=('buscar relojes','buscar dispositivos','buscar disp','buscar actualización','buscar actualizacion','buscar actualizaciones')
        def walk(w):
            for c in list(w.winfo_children()):
                try:
                    if isinstance(c,(ttk.Button,tk.Button)):
                        t=str(c.cget('text') or '').lower()
                        if not any(x in t for x in keep):
                            try:c.pack_forget()
                            except Exception:pass
                            try:c.grid_remove()
                            except Exception:pass
                            try:c.place_forget()
                            except Exception:pass
                    else: walk(c)
                except Exception: pass
        walk(self.root)

    def _install_v167(self):
        top=self.root.winfo_children()[0]
        self.v167_button=ttk.Button(top,text='TRAZAR OTA ZK + BLUETRUM',command=self.trace_ota_graph)
        sib=top.winfo_children()
        try:self.v167_button.pack(side='left',padx=(4,10),before=sib[0] if sib else None)
        except Exception:self.v167_button.place(x=8,y=8)

    def trace_ota_graph(self):
        ready,validation,vpath=self._ready_report()
        if not ready:
            self.status.set('V1.67 · falta validación BK3288.'); return
        chosen=filedialog.askopenfilename(title='Seleccioná UtraWatch XAPK/APK',filetypes=[('UtraWatch','*.xapk *.apk *.zip'),('Todos','*.*')])
        if not chosen: return
        self.face_guard_enabled=False
        self.status.set('V1.67 · reconstruyendo flujo ZKBleOtaManager → BleConnectService → Bluetrum…')

        def work():
            rep={
                'app_version':'1.67.0','generated_utc':datetime.now(timezone.utc).isoformat(),
                'goal':'reconstruct_zkbleotamanager_bleconnectservice_bluetrum_call_graph',
                'validated_profile':validation,'validation_path':vpath,'expected':v145.EXPECTED,'input':chosen,
                'dex':[],'target_methods':[],'callers_into_targets':[],'two_hop_neighbors':[],
                'candidate_uuid_strings':[],'candidate_protocol_strings':[],
                'safety':{'network_requests':0,'firmware_downloads':0,'firmware_writes':0,'ota_writes':0}
            }

            def inspect(label,b):
                try: strings,types,methods,classes,enc=self._dex_model(b)
                except Exception as ex:
                    rep['dex'].append({'name':label,'error':repr(ex)}); return
                code_by_mid={mid:code for _,mid,code in enc}
                rep['dex'].append({'name':label,'classes':len(classes),'methods':len(methods)})

                target_ids=set()
                for m in methods:
                    if m['class'] in TARGET_CLASSES:
                        if m['class']=='Lcom/wtwd/cocousa/ble/BleConnectService;' and m['name'] not in TARGET_BLE_METHODS:
                            continue
                        target_ids.add(m['idx'])

                rows={}
                for mid in sorted(target_ids):
                    me=methods[mid]; code=code_by_mid.get(mid,0)
                    ss,mm=self._refs_in_code(b,code,strings,methods)
                    row={'dex':label,'class':me['class'],'method':me['name'],'method_idx':mid,'code_off':code,
                         'strings':[x for x in ss if len(x)<2000][:250],
                         'calls':[{'idx':x['idx'],'class':x['class'],'method':x['name']} for x in mm[:250]]}
                    rep['target_methods'].append(row); rows[mid]=row
                    for s in row['strings']:
                        sl=s.lower()
                        if ('ffc' in sl or '0000' in sl or 'uuid' in sl or 'characteristic' in sl or 'service' in sl) and s not in rep['candidate_uuid_strings']:
                            rep['candidate_uuid_strings'].append(s)
                        if any(k in sl for k in ('firmware','upgrade','ota','fota','dfu','packet','crc','version','offset','chunk','progress','download','write','notify','mtu')) and s not in rep['candidate_protocol_strings']:
                            rep['candidate_protocol_strings'].append(s)

                # Find every encoded method that directly calls any target method.
                for desc,mid,code in enc:
                    if mid in target_ids: continue
                    ss,mm=self._refs_in_code(b,code,strings,methods)
                    hits=[x for x in mm if x['idx'] in target_ids]
                    if not hits: continue
                    me=methods[mid]
                    rep['callers_into_targets'].append({
                        'dex':label,'caller_class':me['class'],'caller_method':me['name'],'caller_idx':mid,'code_off':code,
                        'strings':[x for x in ss if len(x)<2000][:150],
                        'calls_target':[{'idx':x['idx'],'class':x['class'],'method':x['name']} for x in hits]
                    })

                # Two-hop neighborhood: callees of ZKBleOtaManager and callers of those callees.
                neighbor_ids=set()
                for r in rep['target_methods']:
                    if r['dex']!=label or r['class']!='Lcom/wtwd/cocousa/ble/ZKBleOtaManager;': continue
                    for c in r['calls']:
                        if c['class'].startswith('Lcom/wtwd/') or c['class'].startswith('Lcom/bluetrum/'):
                            neighbor_ids.add(c['idx'])
                for nid in sorted(neighbor_ids):
                    if not (0<=nid<len(methods)): continue
                    me=methods[nid]; code=code_by_mid.get(nid,0); ss,mm=self._refs_in_code(b,code,strings,methods)
                    rep['two_hop_neighbors'].append({'dex':label,'class':me['class'],'method':me['name'],'method_idx':nid,'code_off':code,
                        'strings':[x for x in ss if len(x)<2000][:150],
                        'calls':[{'idx':x['idx'],'class':x['class'],'method':x['name']} for x in mm[:150]]})

            def inspect_apk(name,data):
                try:
                    with zipfile.ZipFile(io.BytesIO(data),'r') as z:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')):
                                inspect(name+'!'+n,z.read(n))
                except Exception: pass

            if zipfile.is_zipfile(chosen):
                with zipfile.ZipFile(chosen,'r') as z:
                    apks=[n for n in z.namelist() if n.lower().endswith('.apk')]
                    if apks:
                        for n in apks:
                            if 'com.wtwd.utrawatch' in n.lower() or 'base' in n.lower(): inspect_apk(n,z.read(n))
                    else:
                        for n in z.namelist():
                            if n=='classes.dex' or (n.startswith('classes') and n.endswith('.dex')): inspect(n,z.read(n))
            else:
                with open(chosen,'rb') as f: inspect_apk(os.path.basename(chosen),f.read())

            rep['target_methods']=rep['target_methods'][:2000]
            rep['callers_into_targets']=rep['callers_into_targets'][:3000]
            rep['two_hop_neighbors']=rep['two_hop_neighbors'][:2000]
            rep['candidate_uuid_strings']=rep['candidate_uuid_strings'][:1000]
            rep['candidate_protocol_strings']=rep['candidate_protocol_strings'][:1500]
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'RelojLab','firmware-v167'); os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,'utrawatch-zk-ota-graph-v167.json'); rep['saved_path']=out
            with open(out,'w',encoding='utf-8') as f: json.dump(rep,f,ensure_ascii=False,indent=2)
            return rep

        def done(rep,err):
            if err:
                self.status.set('V1.67 · falló: '+repr(err)); return
            self.report={'zk_ota_graph_v167':rep}; self.show()
            try:
                t=json.dumps(rep,ensure_ascii=False,indent=2); self.root.clipboard_clear(); self.root.clipboard_append(t); self.root.update_idletasks()
            except Exception: pass
            self.status.set(f"V1.67 LISTO · targets={len(rep['target_methods'])} · callers={len(rep['callers_into_targets'])} · vecinos={len(rep['two_hop_neighbors'])} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=='__main__':
    root=tk.Tk(); AppV167(root); root.mainloop()
