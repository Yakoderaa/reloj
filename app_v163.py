import json, os, re, zipfile, glob
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, filedialog
import app as base
import app_v162 as v162
import app_v145 as v145

base.APP_VERSION="1.63.0"

class AppV163(v162.AppV162):
    def __init__(self, root):
        super().__init__(root)
        root.title("Reloj Lab V1.63")
        self._retitle_v163(root)
        self._replace_action_v163()
        self.status.set("V1.63 lista · si no encuentra UtraWatch, abre selector automáticamente. Conserva Buscar dispositivos y Buscar actualizaciones.")

    def _retitle_v163(self, widget):
        try:
            if isinstance(widget, ttk.Label):
                t=str(widget.cget("text"))
                for old in ("V1.54","V1.55","V1.56","V1.57","V1.58","V1.59","V1.60","V1.61","V1.62"):
                    t=t.replace(old,"V1.63")
                widget.configure(text=t)
        except Exception:
            pass
        try:
            for child in widget.winfo_children(): self._retitle_v163(child)
        except Exception:
            pass

    def _replace_action_v163(self):
        allowed=("buscar relojes","buscar dispositivos","buscar disp","buscar actualizaciones","buscar actualización","buscar actualizacion")
        def walk(widget):
            for child in list(widget.winfo_children()):
                try:
                    if isinstance(child,(ttk.Button,tk.Button)):
                        text=str(child.cget("text") or "").strip().lower()
                        if not any(x in text for x in allowed):
                            try: child.pack_forget()
                            except Exception: pass
                            try: child.grid_remove()
                            except Exception: pass
                            try: child.place_forget()
                            except Exception: pass
                    else: walk(child)
                except Exception: pass
        walk(self.root)
        try:
            top=self.root.winfo_children()[0]
            self.v163_button=ttk.Button(top,text="SELECCIONAR UTRAWATCH Y ANALIZAR",command=self.analyze_mobile_ota_v163)
            siblings=top.winfo_children()
            if siblings: self.v163_button.pack(side="left",padx=(4,10),before=siblings[0])
            else: self.v163_button.pack(side="left",padx=(4,10))
        except Exception:
            self.v163_button=ttk.Button(self.root,text="SELECCIONAR UTRAWATCH Y ANALIZAR",command=self.analyze_mobile_ota_v163)
            self.v163_button.place(x=8,y=8)

    def _auto_candidates(self):
        home=os.path.expanduser("~")
        roots=[os.path.join(home,"Downloads"),os.path.join(home,"Desktop"),os.path.join(home,"Descargas")]
        found=[]
        for rootdir in roots:
            if not os.path.isdir(rootdir): continue
            for ext in ("*.apk","*.xapk","*.zip"):
                for p in glob.glob(os.path.join(rootdir,ext)):
                    name=os.path.basename(p).lower()
                    if "utrawatch" in name or "ultrawatch" in name:
                        if p not in found: found.append(p)
        return found

    def analyze_mobile_ota_v163(self):
        ready,validation,validation_path=self._ready_report()
        if not ready:
            self.status.set("V1.63 · falta validación BK3288 ready_for_firmware_patch=true.")
            return
        self.face_guard_enabled=False
        candidates=self._auto_candidates()
        if not candidates:
            chosen=filedialog.askopenfilename(
                title="Seleccioná el APK/XAPK/ZIP de UtraWatch",
                filetypes=[("UtraWatch package","*.apk *.xapk *.zip"),("Todos los archivos","*.*")]
            )
            if not chosen:
                self.status.set("V1.63 · no se seleccionó ningún paquete UtraWatch.")
                return
            candidates=[chosen]
        self.status.set("V1.63 · analizando paquete UtraWatch seleccionado y extrayendo evidencia OTA…")

        def printable_strings(data, min_len=5):
            out=[]
            for m in re.finditer(rb'[\x20-\x7e]{'+str(min_len).encode()+rb',}',data):
                try: s=m.group(0).decode('utf-8','ignore')
                except Exception: continue
                out.append(s)
                if len(out)>=20000: break
            return out

        def work():
            started=datetime.now(timezone.utc)
            report={
                "app_version":"1.63.0","generated_utc":started.isoformat(),
                "goal":"inspect_selected_utrawatch_package_for_exact_ota_firmware_protocol_strings",
                "validated_profile":validation,"validation_path":validation_path,"expected":v145.EXPECTED,
                "input_packages":candidates,"package_scan":[],"matches":[],"urls":[],"class_hints":[],
                "safety":{"network_requests":0,"firmware_downloads":0,"firmware_writes":0,"ota_writes":0},
                "notes":[]
            }
            keywords=("firmware","upgrade","ota","oad","ffc0","ffc1","ffc2","f000ffc","bk3288","bekencrop","watchhealth","yuedongservice","downloadurl","fileurl","dfu","bootloader","versioncheck","updatefirmware")
            urls=[]; class_hints=[]; matches=[]
            for path in candidates[:4]:
                item={"path":path,"size":os.path.getsize(path),"entries":0,"interesting_entries":[]}
                try:
                    blobs=[]
                    if zipfile.is_zipfile(path):
                        with zipfile.ZipFile(path,"r") as z:
                            names=z.namelist(); item["entries"]=len(names)
                            for name in names:
                                low=name.lower()
                                if any(k in low for k in ("classes","firmware","upgrade","ota","oad","dfu","assets","lib/","network","update")):
                                    item["interesting_entries"].append(name)
                                if name.endswith("/"): continue
                                if not (name.endswith(".dex") or name.endswith(".xml") or name.endswith(".json") or name.endswith(".txt") or name.endswith(".so") or "asset" in low or "config" in low):
                                    continue
                                try: data=z.read(name)
                                except Exception: continue
                                if len(data)>40_000_000: continue
                                blobs.append((name,data))
                    else:
                        with open(path,"rb") as fh: blobs=[("<raw>",fh.read())]

                    for entry,data in blobs:
                        strings=printable_strings(data)
                        for s in strings:
                            sl=s.lower()
                            hit=[k for k in keywords if k in sl]
                            if hit:
                                matches.append({"package":path,"entry":entry,"terms":hit,"text":s[:1200]})
                            for u in re.findall(r'https?://[^\s\"\'<>]{6,300}',s):
                                if u not in urls: urls.append(u)
                            if ("com." in s or "sdk" in sl or "service" in sl) and any(k in sl for k in ("firmware","upgrade","ota","oad","dfu","update")):
                                if s not in class_hints: class_hints.append(s[:1000])
                except Exception as ex:
                    item["error"]=type(ex).__name__+": "+str(ex)
                item["interesting_entries"]=item["interesting_entries"][:500]
                report["package_scan"].append(item)
            report["matches"]=matches[:2500]
            report["urls"]=urls[:500]
            report["class_hints"]=class_hints[:800]
            report["notes"].append("Análisis local del paquete seleccionado; no se hicieron solicitudes de red ni escrituras BLE/OTA.")
            report["elapsed_s"]=(datetime.now(timezone.utc)-started).total_seconds()
            folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","firmware-v163")
            os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,"utrawatch-selected-package-v163.json"); report["saved_path"]=out
            with open(out,"w",encoding="utf-8") as fh: json.dump(report,fh,ensure_ascii=False,indent=2)
            return report

        def done(report,error):
            if error:
                self.status.set("V1.63 · análisis falló: "+repr(error)); return
            self.report={"mobile_ota_v163":report}; self.show()
            try:
                txt=json.dumps(report,ensure_ascii=False,indent=2); self.root.clipboard_clear(); self.root.clipboard_append(txt); self.root.update_idletasks()
            except Exception: pass
            self.status.set(f"V1.63 LISTO · {len(report.get('matches',[]))} coincidencias · {len(report.get('urls',[]))} URLs · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=="__main__":
    root=tk.Tk(); AppV163(root); root.mainloop()
