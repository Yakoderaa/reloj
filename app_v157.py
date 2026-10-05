import json, os, re, urllib.request
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk
import app as base
import app_v154_core as v154core
import app_v145 as v145

base.APP_VERSION="1.57.0"

class AppV157(v154core.AppV154):
    def __init__(self, root):
        super().__init__(root)
        root.title("Reloj Lab V1.57")
        self._retitle_v157(root)
        self._install_resolve_login_button()
        self.status.set("V1.57 lista · resuelve el endpoint real de login desde user-BMKq3CNS.js sin enviar credenciales.")

    def _retitle_v157(self, widget):
        try:
            if isinstance(widget, ttk.Label):
                t=str(widget.cget("text"))
                for old in ("V1.54","V1.55","V1.56"):
                    t=t.replace(old,"V1.57")
                widget.configure(text=t)
        except Exception:
            pass
        try:
            for child in widget.winfo_children():
                self._retitle_v157(child)
        except Exception:
            pass

    def _install_resolve_login_button(self):
        try:
            top=self.root.winfo_children()[0]
            btn=ttk.Button(top,text="RESOLVER ENDPOINT LOGIN",command=self.resolve_login_endpoint)
            siblings=top.winfo_children()
            if siblings:
                btn.pack(side="left",padx=(4,10),before=siblings[0])
            else:
                btn.pack(side="left",padx=(4,10))
            self.resolve_login_button=btn
        except Exception:
            self.resolve_login_button=ttk.Button(self.root,text="RESOLVER ENDPOINT LOGIN",command=self.resolve_login_endpoint)
            self.resolve_login_button.place(x=4,y=34)

    def resolve_login_endpoint(self):
        ready,validation,validation_path=self._ready_report()
        if not ready:
            self.status.set("V1.57 · falta validación BK3288 ready_for_firmware_patch=true.")
            return
        self.face_guard_enabled=False
        self.status.set("V1.57 · analizando user-BMKq3CNS.js y el helper HTTP real…")

        def fetch_text(url, timeout=10, max_bytes=2_000_000):
            req=urllib.request.Request(url,headers={
                "User-Agent":"Mozilla/5.0 RelojLab/1.57",
                "Accept":"application/javascript,text/plain,*/*",
                "Referer":"https://wr.watchhealth.com.cn/"
            })
            with urllib.request.urlopen(req,timeout=timeout) as resp:
                raw=resp.read(max_bytes)
                return raw.decode("utf-8","replace"),getattr(resp,"status",200),(resp.headers.get("Content-Type") or "")

        def windows(text, needle, radius=550, limit=20):
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
                "app_version":"1.57.0",
                "generated_utc":started.isoformat(),
                "goal":"resolve_exact_login_api_function_from_user_bundle_without_auth_request",
                "validated_profile":validation,
                "validation_path":validation_path,
                "expected":v145.EXPECTED,
                "known_from_v156":{
                    "ui_route":"/login",
                    "payload_fields":["account","password"],
                    "login_component_import":"{l as M} from ./user-BMKq3CNS.js",
                    "api_base":"/web-halfwit",
                    "token_header":"Authorization",
                    "token_prefix":"Bearer "
                },
                "assets":{},
                "user_bundle_export_map":[],
                "api_helper_export_map":[],
                "path_candidates":[],
                "call_candidates":[],
                "snippets":{},
                "safety":{"credentials_sent":0,"login_requests_sent":0,"firmware_writes":0,"ota_writes":0},
                "notes":[]
            }
            urls={
                "user":"https://wr.watchhealth.com.cn/assets/user-BMKq3CNS.js",
                "api":"https://wr.watchhealth.com.cn/assets/api-DsOWJ2V9.js",
                "login":"https://wr.watchhealth.com.cn/assets/login-DQQRLLbx.js"
            }
            texts={}
            for name,url in urls.items():
                try:
                    txt,st,ct=fetch_text(url,12,3_000_000)
                    texts[name]=txt
                    report["assets"][name]={"url":url,"status":st,"content_type":ct,"bytes":len(txt)}
                except Exception as ex:
                    report["assets"][name]={"url":url,"error":type(ex).__name__+": "+str(ex)}

            user=texts.get("user","")
            api=texts.get("api","")
            # Export aliases are essential because login imports export `l` as M.
            for label,text,target in (("user",user,"user_bundle_export_map"),("api",api,"api_helper_export_map")):
                for m in re.finditer(r'export\s*\{([^}]*)\}',text):
                    entries=[]
                    for part in m.group(1).split(','):
                        part=part.strip()
                        mm=re.match(r'([\w$]+)\s+as\s+([\w$]+)',part)
                        if mm:
                            entries.append({"local":mm.group(1),"exported":mm.group(2)})
                    if entries:
                        report[target].extend(entries)

            # Every quoted API path in the user bundle.
            paths=[]
            for m in re.finditer(r'["\'](/[^"\']{1,180})["\']',user):
                p=m.group(1)
                if p not in paths:
                    paths.append(p)
            report["path_candidates"]=paths

            # Collect the surrounding call expression for each path and infer likely method from imported helper usage.
            calls=[]
            for p in paths:
                for chunk in windows(user,p,420,8):
                    helpers=[]
                    for mm in re.finditer(r'([\w$]+)\(\s*["\']'+re.escape(p)+r'["\']',chunk):
                        helpers.append(mm.group(1))
                    calls.append({"path":p,"helper_symbols":list(dict.fromkeys(helpers)),"snippet":chunk})
            report["call_candidates"]=calls[:120]

            # Targeted snippets that should reveal the export `l` implementation and exact endpoint.
            for term in ("export{"," as l","/login","account","password","user/login","login"):
                vals=windows(user,term,700,16)
                if vals:
                    report["snippets"][term]=vals

            # Summarize strongest candidate: implementation whose local symbol is exported as `l`.
            exported_l=[x.get("local") for x in report["user_bundle_export_map"] if x.get("exported")=="l"]
            report["login_export_local_symbols"]=exported_l
            strong=[]
            for symbol in exported_l:
                for chunk in windows(user,symbol,900,20):
                    quoted_paths=re.findall(r'["\'](/[^"\']{1,180})["\']',chunk)
                    for p in quoted_paths:
                        strong.append({"export_local":symbol,"path":p,"snippet":chunk})
            # Remove duplicate path+symbol pairs.
            seen=set(); uniq=[]
            for x in strong:
                key=(x["export_local"],x["path"])
                if key in seen: continue
                seen.add(key); uniq.append(x)
            report["strong_login_candidates"]=uniq[:30]

            if uniq:
                report["notes"].append("Se resolvió el símbolo exportado como `l` y sus rutas cercanas. No se envió ninguna solicitud de login.")
            else:
                report["notes"].append("Se descargó el módulo real de usuario y se conservaron exportaciones/rutas/snippets para resolver el último alias sin probar credenciales.")
            report["elapsed_s"]=(datetime.now(timezone.utc)-started).total_seconds()
            folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","firmware-v157")
            os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,"utrawatch-login-endpoint-v157.json")
            report["saved_path"]=out
            with open(out,"w",encoding="utf-8") as fh:
                json.dump(report,fh,ensure_ascii=False,indent=2)
            return report

        def done(report,error):
            if error:
                self.status.set("V1.57 · resolver endpoint falló: "+repr(error))
                return
            self.report={"login_endpoint_v157":report}
            self.show()
            try:
                txt=json.dumps(report,ensure_ascii=False,indent=2)
                self.root.clipboard_clear(); self.root.clipboard_append(txt); self.root.update_idletasks()
            except Exception:
                pass
            self.status.set(f"V1.57 LISTO · {len(report.get('path_candidates',[]))} rutas · {len(report.get('strong_login_candidates',[]))} candidatas fuertes · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=="__main__":
    root=tk.Tk(); AppV157(root); root.mainloop()
