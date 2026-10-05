import json, os, re, urllib.parse, urllib.request
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk
import app as base
import app_v151 as v151
import app_v145 as v145

base.APP_VERSION="1.52.0"

class AppV152(v151.AppV151):
    def __init__(self,root):
        super().__init__(root)
        root.title("Reloj Lab V1.52")
        self._retitle_v152(root)
        self._install_upgrade_api_button()
        self.status.set("V1.52 lista · consulta el endpoint real /upgrade/getUpgradeInfoList descubierto en UtraWatch.")

    def _retitle_v152(self,widget):
        try:
            if isinstance(widget,ttk.Label):
                t=str(widget.cget("text"))
                if "V1.51" in t: widget.configure(text=t.replace("V1.51","V1.52"))
        except Exception: pass
        try:
            for child in widget.winfo_children(): self._retitle_v152(child)
        except Exception: pass

    def _install_upgrade_api_button(self):
        try:
            top=self.root.winfo_children()[0]
            btn=ttk.Button(top,text="CONSULTAR UPGRADE REAL",command=self.query_real_upgrade_api)
            siblings=top.winfo_children()
            if siblings: btn.pack(side="left",padx=(4,10),before=siblings[0])
            else: btn.pack(side="left",padx=(4,10))
            self.upgrade_api_button=btn
        except Exception:
            self.upgrade_api_button=ttk.Button(self.root,text="CONSULTAR UPGRADE REAL",command=self.query_real_upgrade_api)
            self.upgrade_api_button.place(x=4,y=34)

    def query_real_upgrade_api(self):
        ready,validation,validation_path=self._ready_report()
        if not ready:
            self.status.set("V1.52 · falta validación BK3288 ready_for_firmware_patch=true.")
            return
        self.face_guard_enabled=False
        self.status.set("V1.52 · consultando API real de upgrade UtraWatch…")

        def get(url,timeout=8,max_bytes=2_000_000):
            req=urllib.request.Request(url,headers={
                "User-Agent":"Mozilla/5.0 RelojLab/1.52",
                "Accept":"application/json,text/plain,application/javascript,text/html,*/*",
                "Referer":"https://wr.watchhealth.com.cn/"
            })
            with urllib.request.urlopen(req,timeout=timeout) as resp:
                raw=resp.read(max_bytes)
                return raw.decode("utf-8","replace"),getattr(resp,"status",200),(resp.headers.get("Content-Type") or ""),dict(resp.headers.items())

        def extract_urls(obj):
            found=[]
            def walk(x,path="$"):
                if isinstance(x,dict):
                    for k,v in x.items(): walk(v,path+"."+str(k))
                elif isinstance(x,list):
                    for i,v in enumerate(x): walk(v,path+f"[{i}]")
                elif isinstance(x,str):
                    lx=x.lower()
                    if x.startswith(("http://","https://")) or any(t in lx for t in (".bin",".zip",".img",".hex",".fw","firmware","upgrade")):
                        found.append({"path":path,"value":x})
            walk(obj)
            return found

        def work():
            started=datetime.now(timezone.utc)
            report={
                "app_version":"1.52.0",
                "generated_utc":started.isoformat(),
                "goal":"query_real_utrawatch_upgrade_api_for_bk3288",
                "validated_profile":validation,
                "validation_path":validation_path,
                "expected":v145.EXPECTED,
                "discovered_from_v151":{
                    "module":"assets/update-C9dlL75R.js",
                    "list_endpoint":"/upgrade/getUpgradeInfoList",
                    "upload_endpoint":"/upgrade/uploadUpgradeFile",
                    "add_endpoint":"/upgrade/addUpgradeInfo"
                },
                "api_module":{},"candidate_api_bases":[],"requests":[],"firmware_candidates":[],
                "safety":{"firmware_writes":0,"ota_writes":0,"http_methods":["GET"]},"notes":[]
            }
            portal="https://wr.watchhealth.com.cn/"
            api_asset=urllib.parse.urljoin(portal,"assets/api-DsOWJ2V9.js")
            try:
                js,st,ct,hdr=get(api_asset,10,500000)
                report["api_module"]={"url":api_asset,"status":st,"content_type":ct,"bytes":len(js),"preview":js[:12000]}
                # Pull likely baseURL strings from the real API helper.
                vals=[]
                for pat in (r'baseURL\s*:\s*["\']([^"\']+)',r'["\'](https?://[^"\']+)["\']',r'["\'](/[^"\']{1,100})["\']'):
                    for m in re.finditer(pat,js,re.I):
                        v=m.group(1)
                        if any(k in v.lower() for k in ("api","service","watch","upgrade","http")):
                            vals.append(v)
                report["api_module"]["base_hints"]=list(dict.fromkeys(vals))[:80]
            except Exception as ex:
                js=""
                report["api_module"]={"url":api_asset,"error":type(ex).__name__+": "+str(ex)}

            # Candidate roots are code-derived hints plus only a few deployment conventions.
            roots=[portal.rstrip("/")]
            for hint in report.get("api_module",{}).get("base_hints",[]):
                try:
                    if hint.startswith("http"):
                        roots.append(hint.rstrip("/"))
                    elif hint.startswith("/"):
                        roots.append(urllib.parse.urljoin(portal,hint).rstrip("/"))
                except: pass
            roots += [
                "https://wr.watchhealth.com.cn/api",
                "https://wr.watchhealth.com.cn/prod-api",
                "https://wr.watchhealth.com.cn/YueDongService",
                "http://watchhealth.com.cn/YueDongService"
            ]
            roots=list(dict.fromkeys(roots))
            report["candidate_api_bases"]=roots

            endpoint="/upgrade/getUpgradeInfoList"
            param_sets=[
                {"currentPage":"1","pageSize":"100","watchId":"1180"},
                {"currentPage":"1","pageSize":"100","watchId":"102"},
                {"currentPage":"1","pageSize":"100","watchId":"BK3288-Watch-1.0"},
                {"currentPage":"1","pageSize":"100","version":"6.3.0"},
                {"currentPage":"1","pageSize":"100"},
                {"pageNum":"1","pageSize":"100","watchId":"1180"},
            ]
            for root in roots:
                base=root.rstrip("/")+endpoint
                for params in param_sets:
                    full=base+"?"+urllib.parse.urlencode(params)
                    try:
                        txt,st,ct,hdr=get(full,7,2_000_000)
                        rec={"url":full,"status":st,"content_type":ct,"bytes":len(txt),"preview":txt[:16000]}
                        try:
                            obj=json.loads(txt)
                            rec["json"]=obj
                            urls=extract_urls(obj)
                            if urls:
                                rec["candidate_values"]=urls
                                report["firmware_candidates"].extend([dict(x,source_url=full) for x in urls])
                        except Exception:
                            pass
                        report["requests"].append(rec)
                    except Exception as ex:
                        report["requests"].append({"url":full,"error":type(ex).__name__+": "+str(ex)})

            # Deduplicate candidates without downloading/flashing anything.
            seen=set();uniq=[]
            for x in report["firmware_candidates"]:
                k=(x.get("path"),x.get("value"))
                if k in seen: continue
                seen.add(k);uniq.append(x)
            report["firmware_candidates"]=uniq
            report["elapsed_s"]=(datetime.now(timezone.utc)-started).total_seconds()
            folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","firmware-v152")
            os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,"utrawatch-upgrade-api-v152.json")
            with open(out,"w",encoding="utf-8") as fh:json.dump(report,fh,ensure_ascii=False,indent=2)
            report["saved_path"]=out
            if report["firmware_candidates"]:
                report["notes"].append("La API real devolvió candidatos de archivo/firmware. No se descargó ni escribió firmware.")
            else:
                report["notes"].append("La API real fue consultada, pero no devolvió una URL de firmware utilizable sin autenticación o parámetros adicionales.")
            return report

        def done(report,error):
            if error:
                self.status.set("V1.52 · consulta upgrade falló: "+repr(error));return
            self.report={"real_upgrade_api":report};self.show()
            try:
                txt=json.dumps(report,ensure_ascii=False,indent=2)
                self.root.clipboard_clear();self.root.clipboard_append(txt);self.root.update_idletasks()
            except Exception: pass
            self.status.set(f"V1.52 LISTO · {len(report.get('requests',[]))} consultas · {len(report.get('firmware_candidates',[]))} candidatos · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=="__main__":
    root=tk.Tk();AppV152(root);root.mainloop()
