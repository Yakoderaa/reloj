import json, os, re, urllib.request
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk
import app as base
import app_v159 as v159
import app_v145 as v145

base.APP_VERSION="1.60.0"

class AppV160(v159.AppV159):
    def __init__(self, root):
        super().__init__(root)
        root.title("Reloj Lab V1.60")
        self._retitle_v160(root)
        self._replace_action_button()
        self.status.set("V1.60 lista · analiza el flujo Upgrade real de UtraWatch. Conserva Buscar dispositivos y Buscar actualizaciones.")

    def _retitle_v160(self, widget):
        try:
            if isinstance(widget, ttk.Label):
                t=str(widget.cget("text"))
                for old in ("V1.54","V1.55","V1.56","V1.57","V1.58","V1.59"):
                    t=t.replace(old,"V1.60")
                widget.configure(text=t)
        except Exception:
            pass
        try:
            for child in widget.winfo_children():
                self._retitle_v160(child)
        except Exception:
            pass

    def _replace_action_button(self):
        # Keep only the two general utility buttons plus this version's one required action.
        allowed_general=(
            "buscar relojes",
            "buscar dispositivos",
            "buscar disp",
            "buscar actualizaciones",
            "buscar actualización",
            "buscar actualizacion",
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
            self.upgrade_flow_button=ttk.Button(top,text="ANALIZAR UPGRADE REAL",command=self.analyze_upgrade_flow)
            siblings=top.winfo_children()
            if siblings:
                self.upgrade_flow_button.pack(side="left",padx=(4,10),before=siblings[0])
            else:
                self.upgrade_flow_button.pack(side="left",padx=(4,10))
        except Exception:
            self.upgrade_flow_button=ttk.Button(self.root,text="ANALIZAR UPGRADE REAL",command=self.analyze_upgrade_flow)
            self.upgrade_flow_button.place(x=8,y=8)

    def analyze_upgrade_flow(self):
        ready,validation,validation_path=self._ready_report()
        if not ready:
            self.status.set("V1.60 · falta validación BK3288 ready_for_firmware_patch=true.")
            return
        self.face_guard_enabled=False
        self.status.set("V1.60 · analizando bundles reales de Upgrade/UtraWatch…")

        def fetch_text(url, timeout=12, max_bytes=4_000_000):
            req=urllib.request.Request(url,headers={
                "User-Agent":"Mozilla/5.0 RelojLab/1.60",
                "Accept":"application/javascript,text/plain,*/*",
                "Referer":"https://wr.watchhealth.com.cn/"
            })
            with urllib.request.urlopen(req,timeout=timeout) as resp:
                raw=resp.read(max_bytes)
                return raw.decode("utf-8","replace"),getattr(resp,"status",200),(resp.headers.get("Content-Type") or "")

        def windows(text, needle, radius=700, limit=24):
            out=[];low=text.lower();pos=0
            while True:
                i=low.find(needle.lower(),pos)
                if i<0: break
                out.append(text[max(0,i-radius):min(len(text),i+len(needle)+radius)])
                pos=i+len(needle)
                if len(out)>=limit: break
            return out

        def export_map(text):
            out=[]
            for m in re.finditer(r'export\s*\{([^}]*)\}',text):
                for part in m.group(1).split(','):
                    mm=re.match(r'\s*([\w$]+)\s+as\s+([\w$]+)\s*',part)
                    if mm:
                        out.append({"local":mm.group(1),"exported":mm.group(2)})
            return out

        def work():
            started=datetime.now(timezone.utc)
            report={
                "app_version":"1.60.0",
                "generated_utc":started.isoformat(),
                "goal":"resolve_real_utrawatch_upgrade_client_flow_and_firmware_fields_without_auth_or_ota",
                "validated_profile":validation,
                "validation_path":validation_path,
                "expected":v145.EXPECTED,
                "confirmed_from_v157":{
                    "login_endpoint":"/sys/user/login",
                    "login_payload_fields":["account","password"],
                    "login_export_local":"d",
                    "login_helper_export_alias":"p",
                    "api_base":"/web-halfwit"
                },
                "assets":{},
                "api_helper_export_map":[],
                "upgrade_paths":[],
                "upgrade_calls":[],
                "field_hints":[],
                "snippets":{},
                "safety":{"credentials_sent":0,"login_requests_sent":0,"authenticated_requests_sent":0,"firmware_writes":0,"ota_writes":0,"http_methods":["GET static assets only"]},
                "notes":[]
            }
            urls={
                "update_main":"https://wr.watchhealth.com.cn/assets/update-BXapPuJE.js",
                "update_aux":"https://wr.watchhealth.com.cn/assets/update-C9dlL75R.js",
                "api":"https://wr.watchhealth.com.cn/assets/api-DsOWJ2V9.js",
                "device":"https://wr.watchhealth.com.cn/assets/device-Cp-Kct1F.js"
            }
            texts={}
            for name,url in urls.items():
                try:
                    txt,st,ct=fetch_text(url)
                    texts[name]=txt
                    report["assets"][name]={"url":url,"status":st,"content_type":ct,"bytes":len(txt)}
                except Exception as ex:
                    report["assets"][name]={"url":url,"error":type(ex).__name__+": "+str(ex)}

            api=texts.get("api","")
            report["api_helper_export_map"]=export_map(api)

            combined="\n".join([texts.get("update_main",""),texts.get("update_aux",""),texts.get("device","")])
            paths=[]
            for m in re.finditer(r'["\'](/[^"\']{1,220})["\']',combined):
                p=m.group(1)
                lp=p.lower()
                if any(k in lp for k in ("upgrade","firmware","ota","file","watch","device")) and p not in paths:
                    paths.append(p)
            report["upgrade_paths"]=paths

            calls=[]
            for p in paths:
                for chunk in windows(combined,p,500,12):
                    helpers=[]
                    for mm in re.finditer(r'([\w$]+)\(\s*["\']'+re.escape(p)+r'["\']',chunk):
                        helpers.append(mm.group(1))
                    calls.append({"path":p,"helper_symbols":list(dict.fromkeys(helpers)),"snippet":chunk})
            report["upgrade_calls"]=calls[:160]

            fields=[]
            field_terms=("watchId","version","filePath","fileName","upgradeFile","upgradeType","firmware","downloadUrl","url","md5","sha","size","remark","customerId","hardware","software")
            for term in field_terms:
                if re.search(re.escape(term),combined,re.I):
                    fields.append(term)
            report["field_hints"]=fields

            for term in ("getUpgradeInfoList","uploadUpgradeFile","addUpgradeInfo","upgrade","filePath","watchId","version","download",".bin",".zip","/web-halfwit"):
                vals=windows(combined,term,750,20)
                if vals:
                    report["snippets"][term]=vals

            # Resolve the exact helper implementation for alias p, known from V1.57 login call.
            alias_p=[x.get("local") for x in report["api_helper_export_map"] if x.get("exported")=="p"]
            report["api_alias_p_local_symbols"]=alias_p
            helper_chunks=[]
            for sym in alias_p:
                helper_chunks.extend(windows(api,sym,850,20))
            report["api_alias_p_snippets"]=helper_chunks[:20]

            if report["upgrade_paths"]:
                report["notes"].append("Se identificaron rutas Upgrade/firmware directamente desde los bundles reales. No se realizó login ni ninguna escritura OTA.")
            else:
                report["notes"].append("No aparecieron rutas Upgrade inequívocas en los assets actuales; se conservaron snippets y campos para la siguiente pasada.")
            report["elapsed_s"]=(datetime.now(timezone.utc)-started).total_seconds()
            folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","firmware-v160")
            os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,"utrawatch-upgrade-flow-v160.json")
            report["saved_path"]=out
            with open(out,"w",encoding="utf-8") as fh:
                json.dump(report,fh,ensure_ascii=False,indent=2)
            return report

        def done(report,error):
            if error:
                self.status.set("V1.60 · análisis Upgrade falló: "+repr(error))
                return
            self.report={"upgrade_flow_v160":report}
            self.show()
            try:
                txt=json.dumps(report,ensure_ascii=False,indent=2)
                self.root.clipboard_clear();self.root.clipboard_append(txt);self.root.update_idletasks()
            except Exception:
                pass
            self.status.set(f"V1.60 LISTO · {len(report.get('upgrade_paths',[]))} rutas Upgrade · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=="__main__":
    root=tk.Tk();AppV160(root);root.mainloop()
