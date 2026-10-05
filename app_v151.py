import json, os, re, urllib.parse, urllib.request
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk
import app as base
import app_v150 as v150
import app_v145 as v145

base.APP_VERSION="1.51.0"

class AppV151(v150.AppV150):
    def __init__(self,root):
        super().__init__(root)
        root.title("Reloj Lab V1.51")
        self._retitle_v151(root)
        self._install_ota_discovery_button()
        self.status.set("V1.51 lista · descubre endpoints OTA reales desde el JavaScript del portal UtraWatch.")

    def _retitle_v151(self,widget):
        try:
            if isinstance(widget,ttk.Label):
                t=str(widget.cget("text"))
                if "V1.50" in t: widget.configure(text=t.replace("V1.50","V1.51"))
        except Exception: pass
        try:
            for child in widget.winfo_children(): self._retitle_v151(child)
        except Exception: pass

    def _install_ota_discovery_button(self):
        try:
            top=self.root.winfo_children()[0]
            btn=ttk.Button(top,text="DESCUBRIR ENDPOINT OTA REAL",command=self.discover_real_ota_endpoint)
            siblings=top.winfo_children()
            if siblings: btn.pack(side="left",padx=(4,10),before=siblings[0])
            else: btn.pack(side="left",padx=(4,10))
            self.ota_discovery_button=btn
        except Exception:
            self.ota_discovery_button=ttk.Button(self.root,text="DESCUBRIR ENDPOINT OTA REAL",command=self.discover_real_ota_endpoint)
            self.ota_discovery_button.place(x=4,y=34)

    def discover_real_ota_endpoint(self):
        ready,validation,validation_path=self._ready_report()
        if not ready:
            self.status.set("V1.51 · primero falta la validación BK3288 ready_for_firmware_patch=true.")
            return
        self.face_guard_enabled=False
        self.status.set("V1.51 · leyendo portal UtraWatch y extrayendo endpoints reales…")

        def fetch_text(url,timeout=8,max_bytes=2_500_000):
            req=urllib.request.Request(url,headers={
                "User-Agent":"Mozilla/5.0 RelojLab/1.51",
                "Accept":"text/html,application/javascript,application/json,text/plain,*/*"
            })
            with urllib.request.urlopen(req,timeout=timeout) as resp:
                raw=resp.read(max_bytes)
                return raw.decode("utf-8","replace"),getattr(resp,"status",200),(resp.headers.get("Content-Type") or "")

        def work():
            started=datetime.now(timezone.utc)
            report={
                "app_version":"1.51.0",
                "generated_utc":started.isoformat(),
                "goal":"discover_exact_ota_endpoint_from_utrawatch_webapp_code",
                "validated_profile":validation,
                "validation_path":validation_path,
                "expected":v145.EXPECTED,
                "portal":{},"scripts":[],"candidate_paths":[],"candidate_urls":[],"probes":[],
                "safety":{"firmware_writes":0,"ota_writes":0},"notes":[]
            }
            portal="https://wr.watchhealth.com.cn/"
            html,status,ctype=fetch_text(portal,10,500000)
            report["portal"]={"url":portal,"status":status,"content_type":ctype,"preview":html[:5000]}
            script_srcs=re.findall(r'<script[^>]+src=["\']([^"\']+)["\']',html,re.I)
            if not script_srcs:
                script_srcs=re.findall(r'([/A-Za-z0-9_.-]+\.js)',html)
            script_texts=[]
            for src in script_srcs[:12]:
                full=urllib.parse.urljoin(portal,src)
                try:
                    js,st,ct=fetch_text(full,12,4_000_000)
                    report["scripts"].append({"url":full,"status":st,"content_type":ct,"bytes":len(js)})
                    script_texts.append((full,js))
                except Exception as ex:
                    report["scripts"].append({"url":full,"error":type(ex).__name__+": "+str(ex)})

            # Extract only paths/URLs that actually exist in the shipped web app code.
            path_re=re.compile(r'(?P<q>["\'])(?P<p>[^"\']{2,220})(?P=q)')
            keywords=("firmware","upgrade","update","ota","dfu","fota","version","device","package","file")
            raw_candidates=[]
            for src,js in script_texts:
                for m in path_re.finditer(js):
                    p=m.group("p")
                    lp=p.lower()
                    if any(k in lp for k in keywords) and ("/" in p or ".do" in lp or "api" in lp):
                        if len(p)<220 and not p.startswith("data:"):
                            raw_candidates.append((src,p))
                # Also capture bare .do endpoints not necessarily quoted cleanly after minification.
                for p in re.findall(r'[A-Za-z0-9_./-]{2,120}\.do',js):
                    lp=p.lower()
                    if any(k in lp for k in keywords): raw_candidates.append((src,p))

            seen=set()
            for src,p in raw_candidates:
                p=p.replace("\\/","/")
                key=p.strip()
                if not key or key in seen: continue
                seen.add(key)
                report["candidate_paths"].append({"source_script":src,"path":key})

            # Build safe GET probes from code-derived candidates only.
            params={
                "deviceId":"1180","customerId":"255","version":"6.3.0","software":"6.3.0",
                "model":"BK3288-Watch-1.0","hardware":"3,1,1,1"
            }
            for item in report["candidate_paths"][:120]:
                p=item["path"]
                if p.startswith("http://") or p.startswith("https://"):
                    u=p
                else:
                    u=urllib.parse.urljoin(portal,p)
                report["candidate_urls"].append(u)
                try:
                    # GET only. Never POST and never touch BLE OTA here.
                    sep="&" if "?" in u else "?"
                    full=u+sep+urllib.parse.urlencode(params)
                    txt,st,ct=fetch_text(full,5,350000)
                    low=txt.lower()
                    interesting=any(x in low for x in (".bin","firmware","upgrade","version","url","download","package"))
                    probe={"url":full,"status":st,"content_type":ct,"bytes":len(txt),"interesting":interesting,"preview":txt[:5000]}
                    report["probes"].append(probe)
                except Exception as ex:
                    report["probes"].append({"url":u,"error":type(ex).__name__+": "+str(ex)})

            report["interesting_probes"]=[p for p in report["probes"] if p.get("interesting")]
            report["elapsed_s"]=(datetime.now(timezone.utc)-started).total_seconds()
            folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","firmware-v151")
            os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,"utrawatch-real-ota-endpoints-v151.json")
            with open(out,"w",encoding="utf-8") as fh:json.dump(report,fh,ensure_ascii=False,indent=2)
            report["saved_path"]=out
            if report["interesting_probes"]:
                report["notes"].append("Se hallaron respuestas relevantes desde endpoints extraídos del código real del portal. No hubo escrituras OTA.")
            else:
                report["notes"].append("No hubo respuesta firmware directa, pero quedaron identificados los endpoints reales referenciados por el portal para la siguiente pasada.")
            return report

        def done(report,error):
            if error:
                self.status.set("V1.51 · descubrimiento OTA falló: "+repr(error));return
            self.report={"real_ota_discovery":report};self.show()
            try:
                txt=json.dumps(report,ensure_ascii=False,indent=2)
                self.root.clipboard_clear();self.root.clipboard_append(txt);self.root.update_idletasks()
            except Exception: pass
            self.status.set(f"V1.51 LISTO · {len(report.get('candidate_paths',[]))} rutas reales · {len(report.get('interesting_probes',[]))} respuestas relevantes · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=="__main__":
    root=tk.Tk();AppV151(root);root.mainloop()
