import json, os, re, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk
import app as base
import app_v154 as v154
import app_v145 as v145

base.APP_VERSION="1.55.0"

class AppV155(v154.AppV154):
    def __init__(self, root):
        super().__init__(root)
        root.title("Reloj Lab V1.55")
        self._retitle_v155(root)
        self._install_login_discovery_button()
        self.status.set("V1.55 lista · descubre el endpoint y campos reales de login del portal UtraWatch sin enviar credenciales.")

    def _retitle_v155(self, widget):
        try:
            if isinstance(widget, ttk.Label):
                t=str(widget.cget("text"))
                if "V1.54" in t:
                    widget.configure(text=t.replace("V1.54","V1.55"))
        except Exception:
            pass
        try:
            for child in widget.winfo_children():
                self._retitle_v155(child)
        except Exception:
            pass

    def _install_login_discovery_button(self):
        try:
            top=self.root.winfo_children()[0]
            btn=ttk.Button(top,text="DESCUBRIR LOGIN REAL",command=self.discover_real_login)
            siblings=top.winfo_children()
            if siblings:
                btn.pack(side="left",padx=(4,10),before=siblings[0])
            else:
                btn.pack(side="left",padx=(4,10))
            self.login_discovery_button=btn
        except Exception:
            self.login_discovery_button=ttk.Button(self.root,text="DESCUBRIR LOGIN REAL",command=self.discover_real_login)
            self.login_discovery_button.place(x=4,y=34)

    def discover_real_login(self):
        ready,validation,validation_path=self._ready_report()
        if not ready:
            self.status.set("V1.55 · falta validación BK3288 ready_for_firmware_patch=true.")
            return
        self.face_guard_enabled=False
        self.status.set("V1.55 · analizando login real y esquema Bearer del portal…")

        def fetch_text(url, timeout=10, max_bytes=4_000_000):
            req=urllib.request.Request(url,headers={
                "User-Agent":"Mozilla/5.0 RelojLab/1.55",
                "Accept":"application/javascript,text/plain,text/html,*/*",
                "Referer":"https://wr.watchhealth.com.cn/"
            })
            with urllib.request.urlopen(req,timeout=timeout) as resp:
                raw=resp.read(max_bytes)
                return raw.decode("utf-8","replace"),getattr(resp,"status",200),(resp.headers.get("Content-Type") or "")

        def windows(text, needle, radius=700, limit=20):
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
                "app_version":"1.55.0",
                "generated_utc":started.isoformat(),
                "goal":"discover_exact_utrawatch_login_endpoint_method_fields_and_token_schema",
                "validated_profile":validation,
                "validation_path":validation_path,
                "expected":v145.EXPECTED,
                "known_from_v154":{
                    "api_base":"/web-halfwit",
                    "upgrade_endpoint":"/upgrade/getUpgradeInfoList",
                    "upgrade_requires_auth":True,
                    "token_header":"Authorization",
                    "token_prefix":"Bearer ",
                    "token_storage_key":"token"
                },
                "assets":{},
                "login_path_candidates":[],
                "login_method_hints":[],
                "login_field_hints":[],
                "snippets":{},
                "safety":{
                    "firmware_writes":0,
                    "ota_writes":0,
                    "credentials_sent":0,
                    "login_requests_sent":0
                },
                "notes":[]
            }

            portal="https://wr.watchhealth.com.cn/"
            assets={
                "login":"https://wr.watchhealth.com.cn/assets/login-DQQRLLbx.js",
                "api":"https://wr.watchhealth.com.cn/assets/api-DsOWJ2V9.js",
                "index":"https://wr.watchhealth.com.cn/assets/index-CEgABmaB.js"
            }
            texts={}
            for name,url in assets.items():
                try:
                    txt,st,ct=fetch_text(url,12,5_000_000)
                    texts[name]=txt
                    report["assets"][name]={"url":url,"status":st,"content_type":ct,"bytes":len(txt)}
                except Exception as ex:
                    report["assets"][name]={"url":url,"error":type(ex).__name__+": "+str(ex)}

            combined="\n".join(texts.values())
            quoted=[]
            for m in re.finditer(r'["\']([^"\']{1,220})["\']',combined):
                s=m.group(1)
                ls=s.lower()
                if "login" in ls or "signin" in ls or "auth" in ls:
                    quoted.append(s)
            # Path-like strings are the strongest endpoint hints.
            path_candidates=[]
            for s in quoted:
                if s.startswith("/") and len(s)<180:
                    if s not in path_candidates: path_candidates.append(s)
            for m in re.finditer(r'(["\'])(/[^"\']*(?:login|signin|auth)[^"\']*)\1',combined,re.I):
                s=m.group(2)
                if s not in path_candidates: path_candidates.append(s)
            report["login_path_candidates"]=path_candidates[:100]

            # Capture likely request method around each path occurrence.
            method_hints=[]
            for p in report["login_path_candidates"]:
                for chunk in windows(combined,p,500,8):
                    methods=[]
                    for meth in ("post","get","put","delete"):
                        if re.search(r'\b'+meth+r'\b',chunk,re.I): methods.append(meth.upper())
                    method_hints.append({"path":p,"methods":methods,"snippet":chunk})
            report["login_method_hints"]=method_hints[:80]

            # Extract common form keys near login code; no values or credentials are collected.
            field_names=[]
            login_text=texts.get("login","")
            for key in ("username","userName","account","email","phone","password","passwd","pwd","captcha","code"):
                if re.search(re.escape(key),login_text,re.I):
                    field_names.append(key)
            report["login_field_hints"]=field_names

            for term in ("login","username","password","Authorization","Bearer ","TOKEN_HEADER","TOKEN_PREFIX","TOKEN_KEY","pragma"):
                vals=windows(combined,term,650,12)
                if vals: report["snippets"][term]=vals

            if report["login_path_candidates"]:
                report["notes"].append("Se identificaron rutas candidatas de login desde el JavaScript real. V1.55 no envió usuario, contraseña ni tokens.")
            else:
                report["notes"].append("El bundle fue analizado pero no apareció una ruta de login inequívoca; el informe conserva los snippets para la siguiente pasada.")
            report["elapsed_s"]=(datetime.now(timezone.utc)-started).total_seconds()
            folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","firmware-v155")
            os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,"utrawatch-login-discovery-v155.json")
            report["saved_path"]=out
            with open(out,"w",encoding="utf-8") as fh:
                json.dump(report,fh,ensure_ascii=False,indent=2)
            return report

        def done(report,error):
            if error:
                self.status.set("V1.55 · descubrimiento de login falló: "+repr(error))
                return
            self.report={"login_discovery_v155":report}
            self.show()
            try:
                txt=json.dumps(report,ensure_ascii=False,indent=2)
                self.root.clipboard_clear(); self.root.clipboard_append(txt); self.root.update_idletasks()
            except Exception:
                pass
            self.status.set(f"V1.55 LISTO · {len(report.get('login_path_candidates',[]))} rutas login · diagnóstico copiado.")

        self.run_thread(work,done)

if __name__=="__main__":
    root=tk.Tk(); AppV155(root); root.mainloop()
