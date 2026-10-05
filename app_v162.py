import json, os, re, zipfile, glob
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk
import app as base
import app_v161 as v161
import app_v145 as v145

base.APP_VERSION="1.62.0"

class AppV162(v161.AppV161):
    def __init__(self, root):
        super().__init__(root)
        root.title("Reloj Lab V1.62")
        self._retitle(root)
        self._replace_action()
        self.status.set("V1.62 lista · busca y analiza localmente UtraWatch para localizar OTA/firmware. Conserva Buscar dispositivos y Buscar actualizaciones.")

    def _retitle(self, widget):
        try:
            if isinstance(widget, ttk.Label):
                t=str(widget.cget("text"))
                for old in ("V1.54","V1.55","V1.56","V1.57","V1.58","V1.59","V1.60","V1.61"):
                    t=t.replace(old,"V1.62")
                widget.configure(text=t)
        except Exception:
            pass
        try:
            for child in widget.winfo_children(): self._retitle(child)
        except Exception:
            pass

    def _replace_action(self):
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
            self.v162_button=ttk.Button(top,text="ANALIZAR CLIENTE OTA MÓVIL",command=self.analyze_mobile_ota)
            siblings=top.winfo_children()
            if siblings: self.v162_button.pack(side="left",padx=(4,10),before=siblings[0])
            else: self.v162_button.pack(side="left",padx=(4,10))
        except Exception:
            self.v162_button=ttk.Button(self.root,text="ANALIZAR CLIENTE OTA MÓVIL",command=self.analyze_mobile_ota)
            self.v162_button.place(x=8,y=8)

    def analyze_mobile_ota(self):
        ready,validation,validation_path=self._ready_report()
        if not ready:
            self.status.set("V1.62 · falta validación BK3288 ready_for_firmware_patch=true.")
            return
        self.face_guard_enabled=False
        self.status.set("V1.62 · buscando UtraWatch APK/XAPK/ZIP y extrayendo huellas OTA…")

        def work():
            started=datetime.now(timezone.utc)
            home=os.path.expanduser("~")
            roots=[os.path.join(home,"Downloads"),os.path.join(home,"Desktop"),os.path.join(home,"Descargas")]
            found=[]
            for rootdir in roots:
                if not os.path.isdir(rootdir): continue
                for pat in ("*UtraWatch*.apk","*UtraWatch*.xapk","*UtraWatch*.zip","*utrawatch*.apk","*utrawatch*.xapk","*utrawatch*.zip"):
                    for p in glob.glob(os.path.join(rootdir,pat)):
                        if p not in found: found.append(p)
            report={
                "app_version":"1.62.0","generated_utc":started.isoformat(),
                "goal":"locate_mobile_utrawatch_ota_firmware_protocol_evidence_locally",
                "validated_profile":validation,"validation_path":validation_path,"expected":v145.EXPECTED,
                "v161_conclusion":{"oss_helper":"generic multipart wrapper","admin_upgrade_base":"/web-halfwit","upgrade_fields":["watchId","version","fileType","filePath"]},
                "packages_found":found,"package_scan":[],"matches":[],
                "safety":{"network_requests":0,"firmware_downloads":0,"firmware_writes":0,"ota_writes":0},"notes":[]
            }
            terms=(b"firmware",b"upgrade",b"ota",b"oad",b"ffc0",b"ffc1",b"ffc2",b"f000ffc",b"watchhealth",b"yuedongservice",b"bk3288",b"bekencrop",b"downloadurl",b"fileurl")
            matches=[]
            for path in found[:8]:
                item={"path":path,"size":os.path.getsize(path),"entries":0,"interesting_entries":[]}
                try:
                    if zipfile.is_zipfile(path):
                        with zipfile.ZipFile(path,"r") as z:
                            names=z.namelist(); item["entries"]=len(names)
                            for name in names:
                                low=name.lower()
                                if any(x in low for x in ("classes","firmware","upgrade","ota","oad","assets","config","network")):
                                    item["interesting_entries"].append(name)
                                if name.endswith("/"): continue
                                try:
                                    data=z.read(name)
                                except Exception: continue
                                dlow=data.lower()
                                hit=[t.decode() for t in terms if t in dlow]
                                if hit:
                                    matches.append({"package":path,"entry":name,"terms":hit,"bytes":len(data)})
                    else:
                        with open(path,"rb") as fh: data=fh.read()
                        dlow=data.lower(); hit=[t.decode() for t in terms if t in dlow]
                        if hit: matches.append({"package":path,"entry":"<raw>","terms":hit,"bytes":len(data)})
                except Exception as ex:
                    item["error"]=type(ex).__name__+": "+str(ex)
                item["interesting_entries"]=item["interesting_entries"][:300]
                report["package_scan"].append(item)
            report["matches"]=matches[:1000]
            if found:
                report["notes"].append("Se analizaron paquetes UtraWatch locales sin modificar archivos ni comunicarse con el reloj.")
            else:
                report["notes"].append("No se encontró UtraWatch APK/XAPK/ZIP en Descargas o Escritorio. La siguiente pasada puede usar un paquete local si está presente.")
            report["elapsed_s"]=(datetime.now(timezone.utc)-started).total_seconds()
            folder=os.path.join(os.environ.get("LOCALAPPDATA",home),"RelojLab","firmware-v162")
            os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,"utrawatch-mobile-ota-v162.json"); report["saved_path"]=out
            with open(out,"w",encoding="utf-8") as fh: json.dump(report,fh,ensure_ascii=False,indent=2)
            return report

        def done(report,error):
            if error:
                self.status.set("V1.62 · análisis OTA móvil falló: "+repr(error)); return
            self.report={"mobile_ota_v162":report}; self.show()
            try:
                txt=json.dumps(report,ensure_ascii=False,indent=2); self.root.clipboard_clear(); self.root.clipboard_append(txt); self.root.update_idletasks()
            except Exception: pass
            self.status.set(f"V1.62 LISTO · {len(report.get('packages_found',[]))} paquetes · {len(report.get('matches',[]))} coincidencias · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=="__main__":
    root=tk.Tk(); AppV162(root); root.mainloop()
