import io, json, os, re, zipfile
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, filedialog
import app as base
import app_v164 as v164
import app_v145 as v145

base.APP_VERSION="1.65.0"

class AppV165(v164.AppV164):
    def __init__(self, root):
        super().__init__(root)
        root.title("Reloj Lab V1.65")
        self._retitle_v165(root)
        self._install_v165_action()
        self.status.set("V1.65 lista · abre el XAPK y analiza por dentro el APK base, classes*.dex y librerías OTA. Buscar actualización sigue activo.")

    def _retitle_v165(self, widget):
        try:
            if isinstance(widget, ttk.Label):
                t=str(widget.cget("text"))
                for old in ("V1.54","V1.55","V1.56","V1.57","V1.58","V1.59","V1.60","V1.61","V1.62","V1.63","V1.64"):
                    t=t.replace(old,"V1.65")
                widget.configure(text=t)
        except Exception: pass
        try:
            for child in widget.winfo_children(): self._retitle_v165(child)
        except Exception: pass

    def _install_v165_action(self):
        keep=("buscar relojes","buscar dispositivos","buscar disp","buscar actualización","buscar actualizacion","buscar actualizaciones")
        def walk(widget):
            for child in list(widget.winfo_children()):
                try:
                    if isinstance(child,(ttk.Button,tk.Button)):
                        text=str(child.cget("text") or "").strip().lower()
                        if not any(x in text for x in keep):
                            try: child.pack_forget()
                            except Exception: pass
                            try: child.grid_remove()
                            except Exception: pass
                            try: child.place_forget()
                            except Exception: pass
                    else: walk(child)
                except Exception: pass
        walk(self.root)
        top=self.root.winfo_children()[0]
        self.v165_button=ttk.Button(top,text="ANALIZAR APK INTERNO OTA",command=self.analyze_nested_ota)
        siblings=top.winfo_children()
        try:
            if siblings: self.v165_button.pack(side="left",padx=(4,10),before=siblings[0])
            else: self.v165_button.pack(side="left",padx=(4,10))
        except Exception:
            self.v165_button.place(x=8,y=8)

    @staticmethod
    def _strings(data, min_len=6, max_count=120000):
        out=[]
        for m in re.finditer(rb'[\x20-\x7e]{'+str(min_len).encode()+rb',}',data):
            try: out.append(m.group(0).decode('utf-8','ignore'))
            except Exception: continue
            if len(out)>=max_count: break
        return out

    def analyze_nested_ota(self):
        ready,validation,validation_path=self._ready_report()
        if not ready:
            self.status.set("V1.65 · falta validación BK3288 ready_for_firmware_patch=true.")
            return
        chosen=filedialog.askopenfilename(
            title="Seleccioná com.wtwd.utrawatch APK/XAPK",
            filetypes=[("UtraWatch APK/XAPK","*.xapk *.apk *.zip"),("Todos los archivos","*.*")]
        )
        if not chosen:
            self.status.set("V1.65 · no se seleccionó ningún archivo.")
            return
        self.face_guard_enabled=False
        self.status.set("V1.65 · abriendo XAPK y buscando el APK base + classes*.dex OTA…")

        def work():
            started=datetime.now(timezone.utc)
            keywords=("firmware","upgrade","ota","oad","dfu","ffc0","ffc1","ffc2","f000ffc","bk3288","bekencrop","watchhealth","yuedongservice","updatefirmware","firmwareupdate","firmware_download","ota_check_file","bootloader")
            report={
                "app_version":"1.65.0","generated_utc":started.isoformat(),
                "goal":"deep_nested_xapk_apk_dex_ota_protocol_extraction",
                "validated_profile":validation,"validation_path":validation_path,"expected":v145.EXPECTED,
                "input":chosen,"outer_entries":[],"nested_apks":[],"dex_files":[],"native_libs":[],
                "matches":[],"urls":[],"class_hints":[],"endpoint_hints":[],
                "safety":{"network_requests":0,"firmware_downloads":0,"firmware_writes":0,"ota_writes":0},"notes":[]
            }
            matches=[]; urls=[]; classes=[]; endpoints=[]

            def inspect_blob(label,data,kind):
                strings=self._strings(data)
                for s in strings:
                    sl=s.lower()
                    hit=[k for k in keywords if k in sl]
                    if hit:
                        matches.append({"source":label,"kind":kind,"terms":hit,"text":s[:1600]})
                    for u in re.findall(r'https?://[^\s\"\'<>]{6,500}',s):
                        if u not in urls: urls.append(u)
                    if (s.startswith("L") and "/" in s and ";" in s) or ("com." in s and "." in s):
                        if any(k in sl for k in ("firmware","upgrade","ota","oad","dfu","update","beken")) and s not in classes:
                            classes.append(s[:1200])
                    if s.startswith("/") and len(s)<300 and any(k in sl for k in ("firmware","upgrade","ota","update","version")):
                        if s not in endpoints: endpoints.append(s)

            def inspect_apk_bytes(apk_name,apk_data):
                row={"name":apk_name,"size":len(apk_data),"entries":0,"dex":[],"libs":[]}
                try:
                    with zipfile.ZipFile(io.BytesIO(apk_data),"r") as az:
                        names=az.namelist(); row["entries"]=len(names)
                        for n in names:
                            low=n.lower()
                            target=(re.match(r'^classes\d*\.dex$',n) or n=='classes.dex' or low.endswith('.so') or low.endswith('.xml') or low.endswith('.json'))
                            if not target: continue
                            try: data=az.read(n)
                            except Exception: continue
                            if len(data)>80_000_000: continue
                            if n.endswith('.dex'):
                                row["dex"].append({"name":n,"size":len(data)})
                                report["dex_files"].append({"apk":apk_name,"name":n,"size":len(data)})
                                inspect_blob(apk_name+"!"+n,data,"dex")
                            elif low.endswith('.so'):
                                row["libs"].append({"name":n,"size":len(data)})
                                if any(k in low for k in ("ota","oad","dfu","ble","beken","firmware","update","watch")):
                                    report["native_libs"].append({"apk":apk_name,"name":n,"size":len(data)})
                                    inspect_blob(apk_name+"!"+n,data,"native")
                            elif any(k in low for k in ("manifest","network","config","firmware","ota","update")):
                                inspect_blob(apk_name+"!"+n,data,"resource")
                except Exception as ex:
                    row["error"]=type(ex).__name__+": "+str(ex)
                report["nested_apks"].append(row)

            if zipfile.is_zipfile(chosen):
                with zipfile.ZipFile(chosen,"r") as outer:
                    names=outer.namelist(); report["outer_entries"]=[{"name":n,"size":outer.getinfo(n).file_size} for n in names]
                    apks=[n for n in names if n.lower().endswith('.apk')]
                    apks.sort(key=lambda n:(0 if any(x in n.lower() for x in ('base','com.wtwd.utrawatch','master')) else 1,n.lower()))
                    for n in apks:
                        try: data=outer.read(n)
                        except Exception: continue
                        inspect_apk_bytes(n,data)
            else:
                with open(chosen,"rb") as fh: inspect_apk_bytes(os.path.basename(chosen),fh.read())

            report["matches"]=matches[:5000]
            report["urls"]=urls[:1000]
            report["class_hints"]=classes[:1500]
            report["endpoint_hints"]=endpoints[:1000]
            report["notes"].append("V1.65 inspecciona APKs anidados y DEX; no hace red ni escribe BLE/OTA.")
            report["elapsed_s"]=(datetime.now(timezone.utc)-started).total_seconds()
            folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","firmware-v165")
            os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,"utrawatch-deep-ota-v165.json"); report["saved_path"]=out
            with open(out,"w",encoding="utf-8") as fh: json.dump(report,fh,ensure_ascii=False,indent=2)
            return report

        def done(report,error):
            if error:
                self.status.set("V1.65 · análisis profundo falló: "+repr(error)); return
            self.report={"deep_ota_v165":report}; self.show()
            try:
                txt=json.dumps(report,ensure_ascii=False,indent=2)
                self.root.clipboard_clear(); self.root.clipboard_append(txt); self.root.update_idletasks()
            except Exception: pass
            self.status.set(f"V1.65 LISTO · APKs={len(report.get('nested_apks',[]))} · DEX={len(report.get('dex_files',[]))} · coincidencias={len(report.get('matches',[]))} · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=="__main__":
    root=tk.Tk(); AppV165(root); root.mainloop()
