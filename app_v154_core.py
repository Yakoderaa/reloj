import json, os, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk
import app as base
import app_v152 as v152
import app_v145 as v145

base.APP_VERSION="1.54.0"

class AppV154(v152.AppV152):
    def __init__(self,root):
        super().__init__(root)
        root.title("Reloj Lab V1.54")
        self._retitle_v154(root)
        self._install_exact_api_button()
        self.status.set("V1.54 lista · prueba la raíz exacta /web-halfwit descubierta en el cliente UtraWatch.")

    def _retitle_v154(self,widget):
        try:
            if isinstance(widget,ttk.Label):
                t=str(widget.cget("text"))
                t=t.replace("V1.52","V1.54").replace("V1.53","V1.54")
                widget.configure(text=t)
        except Exception: pass
        try:
            for child in widget.winfo_children(): self._retitle_v154(child)
        except Exception: pass

    def _install_exact_api_button(self):
        try:
            top=self.root.winfo_children()[0]
            btn=ttk.Button(top,text="PROBAR API EXACTA",command=self.probe_exact_web_halfwit_api)
            siblings=top.winfo_children()
            if siblings: btn.pack(side="left",padx=(4,10),before=siblings[0])
            else: btn.pack(side="left",padx=(4,10))
            self.exact_api_button=btn
        except Exception:
            self.exact_api_button=ttk.Button(self.root,text="PROBAR API EXACTA",command=self.probe_exact_web_halfwit_api)
            self.exact_api_button.place(x=4,y=34)

    def probe_exact_web_halfwit_api(self):
        ready,validation,validation_path=self._ready_report()
        if not ready:
            self.status.set("V1.54 · falta validación BK3288 ready_for_firmware_patch=true.")
            return
        self.face_guard_enabled=False
        self.status.set("V1.54 · consultando /web-halfwit/upgrade/getUpgradeInfoList…")

        def get_any(url,timeout=10,max_bytes=2_000_000):
            req=urllib.request.Request(url,headers={
                "User-Agent":"Mozilla/5.0 RelojLab/1.54",
                "Accept":"application/json,text/plain,*/*",
                "Referer":"https://wr.watchhealth.com.cn/",
                "Origin":"https://wr.watchhealth.com.cn"
            })
            try:
                with urllib.request.urlopen(req,timeout=timeout) as resp:
                    raw=resp.read(max_bytes)
                    return raw.decode("utf-8","replace"),getattr(resp,"status",200),(resp.headers.get("Content-Type") or ""),dict(resp.headers.items()),None
            except urllib.error.HTTPError as ex:
                try: raw=ex.read(max_bytes)
                except Exception: raw=b""
                return raw.decode("utf-8","replace"),ex.code,(ex.headers.get("Content-Type") or "") if ex.headers else "",dict(ex.headers.items()) if ex.headers else {},type(ex).__name__+": "+str(ex)

        def snippets(text,terms,radius=550):
            out={};low=text.lower()
            for term in terms:
                vals=[];p=0
                while True:
                    i=low.find(term.lower(),p)
                    if i<0: break
                    vals.append(text[max(0,i-radius):min(len(text),i+len(term)+radius)])
                    p=i+len(term)
                    if len(vals)>=12: break
                if vals: out[term]=vals
            return out

        def collect_candidates(obj):
            found=[];stack=[("$",obj)]
            while stack:
                path,x=stack.pop()
                if isinstance(x,dict):
                    for k,v in x.items(): stack.append((path+"."+str(k),v))
                elif isinstance(x,list):
                    for i,v in enumerate(x): stack.append((path+f"[{i}]",v))
                elif isinstance(x,str):
                    lx=x.lower()
                    if x.startswith(("http://","https://")) or any(z in lx for z in (".bin",".zip",".img",".hex",".fw","firmware","upgrade")):
                        found.append({"path":path,"value":x})
            return found

        def work():
            started=datetime.now(timezone.utc)
            report={
                "app_version":"1.54.0","generated_utc":started.isoformat(),
                "goal":"probe_exact_web_halfwit_upgrade_api_and_resolve_auth_schema",
                "validated_profile":validation,"validation_path":validation_path,"expected":v145.EXPECTED,
                "discovery_from_v153":{"exact_baseURL":"/web-halfwit","endpoint":"/upgrade/getUpgradeInfoList","auth_flow":"sessionStorage TOKEN_KEY -> TOKEN_HEADER = TOKEN_PREFIX + token"},
                "client_assets":{},"auth_snippets":{},"requests":[],"firmware_candidates":[],
                "safety":{"firmware_writes":0,"ota_writes":0,"http_methods":["GET"],"auth_bypass_attempts":0},"notes":[]
            }
            assets=[("api","https://wr.watchhealth.com.cn/assets/api-DsOWJ2V9.js"),("index","https://wr.watchhealth.com.cn/assets/index-CEgABmaB.js")]
            for name,url in assets:
                try:
                    txt,st,ct,hdr,err=get_any(url,12,4_000_000)
                    report["client_assets"][name]={"url":url,"status":st,"content_type":ct,"bytes":len(txt)}
                    ss=snippets(txt,["/web-halfwit","TOKEN_KEY","TOKEN_HEADER","TOKEN_PREFIX","pragma","Unauthorized","login"])
                    if ss: report["auth_snippets"][name]=ss
                except Exception as ex:
                    report["client_assets"][name]={"url":url,"error":type(ex).__name__+": "+str(ex)}

            base_url="https://wr.watchhealth.com.cn/web-halfwit";endpoint="/upgrade/getUpgradeInfoList"
            param_sets=[{"currentPage":"1","pageSize":"100","watchId":"1180"},{"currentPage":"1","pageSize":"100","watchId":"BK3288-Watch-1.0"},{"currentPage":"1","pageSize":"100","version":"6.3.0"},{"currentPage":"1","pageSize":"100"}]
            for params in param_sets:
                url=base_url+endpoint+"?"+urllib.parse.urlencode(params)
                try:
                    txt,st,ct,hdr,err=get_any(url,8,2_000_000)
                    rec={"url":url,"status":st,"content_type":ct,"bytes":len(txt),"headers":{k:v for k,v in hdr.items() if k.lower() in ("pragma","www-authenticate","content-type","server")},"preview":txt[:20000]}
                    if err: rec["http_error"]=err
                    try:
                        obj=json.loads(txt);rec["json"]=obj
                        found=collect_candidates(obj)
                        if found:
                            rec["candidate_values"]=found;report["firmware_candidates"].extend([dict(x,source_url=url) for x in found])
                    except Exception: pass
                    report["requests"].append(rec)
                except Exception as ex:
                    report["requests"].append({"url":url,"error":type(ex).__name__+": "+str(ex)})

            seen=set();uniq=[]
            for x in report["firmware_candidates"]:
                k=(x.get("path"),x.get("value"))
                if k in seen: continue
                seen.add(k);uniq.append(x)
            report["firmware_candidates"]=uniq
            statuses=[r.get("status") for r in report["requests"] if "status" in r]
            if report["firmware_candidates"]:
                report["notes"].append("La raíz exacta devolvió candidatos de archivo/firmware. No se descargó ni escribió firmware.")
            elif any(s in (401,403) for s in statuses):
                report["notes"].append("La raíz /web-halfwit es correcta y exige autenticación del portal. V1.54 no intenta evadirla ni adivinar credenciales; registra el esquema real para continuar por una vía pública/propietaria segura.")
            else:
                report["notes"].append("La raíz exacta fue consultada y se registró su respuesta completa para la siguiente pasada. No hubo escrituras OTA.")
            report["elapsed_s"]=(datetime.now(timezone.utc)-started).total_seconds()
            folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","firmware-v154");os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,"utrawatch-web-halfwit-v154.json");report["saved_path"]=out
            with open(out,"w",encoding="utf-8") as fh: json.dump(report,fh,ensure_ascii=False,indent=2)
            return report

        def done(report,error):
            if error:
                self.status.set("V1.54 · prueba API exacta falló: "+repr(error));return
            self.report={"exact_api_v154":report};self.show()
            try:
                txt=json.dumps(report,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(txt);self.root.update_idletasks()
            except Exception: pass
            self.status.set(f"V1.54 LISTO · {len(report.get('requests',[]))} consultas exactas · {len(report.get('firmware_candidates',[]))} candidatos · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=="__main__":
    root=tk.Tk();AppV154(root);root.mainloop()
