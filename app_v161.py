import json, os, re, urllib.request
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk
import app as base
import app_v160 as v160
import app_v145 as v145

base.APP_VERSION="1.61.0"

class AppV161(v160.AppV160):
    def __init__(self, root):
        super().__init__(root)
        root.title("Reloj Lab V1.61")
        self._retitle_v161(root)
        self._replace_action_v161()
        self.status.set("V1.61 lista · analiza cómo UtraWatch almacena y referencia los paquetes Upgrade. Conserva Buscar dispositivos y Buscar actualizaciones.")

    def _retitle_v161(self, widget):
        try:
            if isinstance(widget, ttk.Label):
                t=str(widget.cget("text"))
                for old in ("V1.54","V1.55","V1.56","V1.57","V1.58","V1.59","V1.60"):
                    t=t.replace(old,"V1.61")
                widget.configure(text=t)
        except Exception:
            pass
        try:
            for child in widget.winfo_children():
                self._retitle_v161(child)
        except Exception:
            pass

    def _replace_action_v161(self):
        allowed_general=(
            "buscar relojes","buscar dispositivos","buscar disp",
            "buscar actualizaciones","buscar actualización","buscar actualizacion"
        )
        def walk(widget):
            for child in list(widget.winfo_children()):
                try:
                    if isinstance(child,(ttk.Button,tk.Button)):
                        text=str(child.cget("text") or "").strip().lower()
                        if not any(term in text for term in allowed_general):
                            try: child.pack_forget()
                            except Exception: pass
                            try: child.grid_remove()
                            except Exception: pass
                            try: child.place_forget()
                            except Exception: pass
                    else:
                        walk(child)
                except Exception:
                    pass
        walk(self.root)
        try:
            top=self.root.winfo_children()[0]
            self.storage_button=ttk.Button(top,text="ANALIZAR ALMACENAMIENTO UPGRADE",command=self.analyze_upgrade_storage)
            siblings=top.winfo_children()
            if siblings:
                self.storage_button.pack(side="left",padx=(4,10),before=siblings[0])
            else:
                self.storage_button.pack(side="left",padx=(4,10))
        except Exception:
            self.storage_button=ttk.Button(self.root,text="ANALIZAR ALMACENAMIENTO UPGRADE",command=self.analyze_upgrade_storage)
            self.storage_button.place(x=8,y=8)

    def analyze_upgrade_storage(self):
        ready,validation,validation_path=self._ready_report()
        if not ready:
            self.status.set("V1.61 · falta validación BK3288 ready_for_firmware_patch=true.")
            return
        self.face_guard_enabled=False
        self.status.set("V1.61 · analizando helper OSS, rutas de archivos y formato Upgrade…")

        def fetch_text(url, timeout=12, max_bytes=4_000_000):
            req=urllib.request.Request(url,headers={
                "User-Agent":"Mozilla/5.0 RelojLab/1.61",
                "Accept":"application/javascript,text/plain,*/*",
                "Referer":"https://wr.watchhealth.com.cn/"
            })
            with urllib.request.urlopen(req,timeout=timeout) as resp:
                raw=resp.read(max_bytes)
                return raw.decode("utf-8","replace"),getattr(resp,"status",200),(resp.headers.get("Content-Type") or "")

        def windows(text, needle, radius=900, limit=24):
            out=[]; low=text.lower(); pos=0
            while True:
                i=low.find(needle.lower(),pos)
                if i<0: break
                out.append(text[max(0,i-radius):min(len(text),i+len(needle)+radius)])
                pos=i+len(needle)
                if len(out)>=limit: break
            return out

        def work():
            started=datetime.now(timezone.utc)
            report={
                "app_version":"1.61.0",
                "generated_utc":started.isoformat(),
                "goal":"resolve_upgrade_storage_helper_file_url_construction_and_package_metadata_without_auth_or_writes",
                "validated_profile":validation,
                "validation_path":validation_path,
                "expected":v145.EXPECTED,
                "confirmed_from_v160":{
                    "upgrade_list":"/upgrade/getUpgradeInfoList",
                    "upgrade_add":"/upgrade/addUpgradeInfo",
                    "upgrade_upload":"/upgrade/uploadUpgradeFile",
                    "upgrade_record_fields":["watchId","version","fileType","filePath"],
                    "upload_form_field":"file",
                    "file_type_values":{"1":"file","2":"image","3":"package"},
                    "api_base":"/web-halfwit"
                },
                "assets":{},
                "absolute_urls":[],
                "storage_hosts":[],
                "path_candidates":[],
                "response_field_candidates":[],
                "snippets":{},
                "safety":{"credentials_sent":0,"login_requests_sent":0,"authenticated_requests_sent":0,"file_uploads_sent":0,"firmware_writes":0,"ota_writes":0,"http_methods":["GET static assets only"]},
                "notes":[]
            }
            urls={
                "oss_file":"https://wr.watchhealth.com.cn/assets/oss-file-ByeuKAOC.js",
                "update_aux":"https://wr.watchhealth.com.cn/assets/update-C9dlL75R.js",
                "update_main":"https://wr.watchhealth.com.cn/assets/update-BXapPuJE.js",
                "api":"https://wr.watchhealth.com.cn/assets/api-DsOWJ2V9.js"
            }
            texts={}
            for name,url in urls.items():
                try:
                    txt,st,ct=fetch_text(url)
                    texts[name]=txt
                    report["assets"][name]={"url":url,"status":st,"content_type":ct,"bytes":len(txt)}
                except Exception as ex:
                    report["assets"][name]={"url":url,"error":type(ex).__name__+": "+str(ex)}

            combined="\n".join(texts.values())
            abs_urls=[]
            for m in re.finditer(r'https?://[^"\'\s<>]{4,300}',combined):
                u=m.group(0).rstrip('),];}')
                if u not in abs_urls:
                    abs_urls.append(u)
            report["absolute_urls"]=abs_urls[:200]

            hosts=[]
            for u in abs_urls:
                mm=re.match(r'https?://([^/]+)',u,re.I)
                if mm and mm.group(1) not in hosts:
                    hosts.append(mm.group(1))
            report["storage_hosts"]=hosts

            paths=[]
            for m in re.finditer(r'["\'](/[^"\']{1,240})["\']',combined):
                p=m.group(1)
                lp=p.lower()
                if any(k in lp for k in ("upload","file","oss","upgrade","download","firmware","package","bucket","object")) and p not in paths:
                    paths.append(p)
            report["path_candidates"]=paths

            fields=[]
            for term in ("url","filePath","fileName","path","key","bucket","host","domain","endpoint","location","data","code","msg","md5","sha","size","watchId","version","fileType"):
                if re.search(r'(?i)\b'+re.escape(term)+r'\b',combined):
                    fields.append(term)
            report["response_field_candidates"]=fields

            targets=(
                "uploadUpgradeFile","FormData","append(\"file\"","filePath","oss-file","baseURL",
                "response.data","return","bucket","endpoint","domain","location","https://","http://",
                ".bin",".zip","package"
            )
            for term in targets:
                vals=windows(combined,term,1000,24)
                if vals:
                    report["snippets"][term]=vals

            oss=texts.get("oss_file","")
            report["oss_export_snippets"]=windows(oss,"export{",1200,8)
            report["oss_upload_snippets"]=windows(oss,"upload",1200,16)
            report["oss_return_snippets"]=windows(oss,"return",1200,16)

            if report["storage_hosts"] or report["path_candidates"]:
                report["notes"].append("Se extrajeron hosts/rutas y el helper de almacenamiento usados por Upgrade. No se realizó login, upload ni escritura BLE/OTA.")
            else:
                report["notes"].append("El helper fue descargado pero no expuso host/ruta inequívocos; se conservaron snippets completos para la siguiente versión.")
            report["elapsed_s"]=(datetime.now(timezone.utc)-started).total_seconds()
            folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","firmware-v161")
            os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,"utrawatch-upgrade-storage-v161.json")
            report["saved_path"]=out
            with open(out,"w",encoding="utf-8") as fh:
                json.dump(report,fh,ensure_ascii=False,indent=2)
            return report

        def done(report,error):
            if error:
                self.status.set("V1.61 · análisis de almacenamiento falló: "+repr(error))
                return
            self.report={"upgrade_storage_v161":report}
            self.show()
            try:
                txt=json.dumps(report,ensure_ascii=False,indent=2)
                self.root.clipboard_clear(); self.root.clipboard_append(txt); self.root.update_idletasks()
            except Exception:
                pass
            self.status.set(f"V1.61 LISTO · {len(report.get('storage_hosts',[]))} hosts · {len(report.get('path_candidates',[]))} rutas · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=="__main__":
    root=tk.Tk(); AppV161(root); root.mainloop()
