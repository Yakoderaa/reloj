import json, os, re, urllib.parse, urllib.request
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk
import app as base
import app_v152 as v152
import app_v145 as v145

base.APP_VERSION="1.53.0"

class AppV153(v152.AppV152):
    def __init__(self,root):
        super().__init__(root)
        root.title("Reloj Lab V1.53")
        self._retitle_v153(root)
        self._install_api_config_button()
        self.status.set("V1.53 lista · extrae baseURL y autenticación real del cliente UtraWatch antes de consultar Upgrade.")

    def _retitle_v153(self,widget):
        try:
            if isinstance(widget,ttk.Label):
                t=str(widget.cget("text"))
                if "V1.52" in t: widget.configure(text=t.replace("V1.52","V1.53"))
        except Exception: pass
        try:
            for child in widget.winfo_children(): self._retitle_v153(child)
        except Exception: pass

    def _install_api_config_button(self):
        try:
            top=self.root.winfo_children()[0]
            btn=ttk.Button(top,text="EXTRAER API REAL",command=self.extract_real_api_config)
            siblings=top.winfo_children()
            if siblings: btn.pack(side="left",padx=(4,10),before=siblings[0])
            else: btn.pack(side="left",padx=(4,10))
            self.api_config_button=btn
        except Exception:
            self.api_config_button=ttk.Button(self.root,text="EXTRAER API REAL",command=self.extract_real_api_config)
            self.api_config_button.place(x=4,y=34)

    def extract_real_api_config(self):
        ready,validation,validation_path=self._ready_report()
        if not ready:
            self.status.set("V1.53 · falta validación BK3288 ready_for_firmware_patch=true.")
            return
        self.face_guard_enabled=False
        self.status.set("V1.53 · analizando configuración HTTP real de UtraWatch…")

        def get(url,timeout=10,max_bytes=4_000_000):
            req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 RelojLab/1.53","Accept":"application/json,text/plain,application/javascript,text/html,*/*","Referer":"https://wr.watchhealth.com.cn/"})
            with urllib.request.urlopen(req,timeout=timeout) as resp:
                raw=resp.read(max_bytes)
                return raw.decode("utf-8","replace"),getattr(resp,"status",200),(resp.headers.get("Content-Type") or ""),dict(resp.headers.items())

        def windows(text,needle,radius=500):
            out=[];low=text.lower();pos=0
            while True:
                i=low.find(needle.lower(),pos)
                if i<0: break
                out.append(text[max(0,i-radius):min(len(text),i+len(needle)+radius)])
                pos=i+len(needle)
                if len(out)>=20: break
            return out

        def work():
            started=datetime.now(timezone.utc)
            report={"app_version":"1.53.0","generated_utc":started.isoformat(),"goal":"extract_exact_utrawatch_http_base_and_auth_then_query_upgrade","validated_profile":validation,"validation_path":validation_path,"expected":v145.EXPECTED,"api_asset":{},"config_snippets":{},"absolute_urls":[],"host_hints":[],"candidate_api_bases":[],"requests":[],"firmware_candidates":[],"safety":{"firmware_writes":0,"ota_writes":0,"http_methods":["GET"]},"notes":[]}
            portal="https://wr.watchhealth.com.cn/"
            api_asset=urllib.parse.urljoin(portal,"assets/api-DsOWJ2V9.js")
            js,st,ct,hdr=get(api_asset,12,4_000_000)
            report["api_asset"]={"url":api_asset,"status":st,"content_type":ct,"bytes":len(js)}
            keys=["baseURL","axios.create","create({","Authorization","Bearer","token","interceptors.request","localStorage","sessionStorage","VITE_","/upgrade/"]
            for k in keys:
                w=windows(js,k,700)
                if w: report["config_snippets"][k]=w
            abs_urls=re.findall(r'https?://[^"\'`\\\s)]+',js,re.I)
            clean=[]
            for u in abs_urls:
                u=u.rstrip(";,.}")
                if u not in clean: clean.append(u)
            report["absolute_urls"]=clean[:200]
            hints=[]
            for m in re.finditer(r'["\']([^"\']{3,220})["\']',js):
                s=m.group(1);ls=s.lower()
                if ("http" in ls or "api" in ls or "service" in ls) and not s.startswith("data:"):
                    if any(x in ls for x in ("watchhealth","api","service","upgrade")): hints.append(s)
            for s in clean: hints.append(s)
            report["host_hints"]=list(dict.fromkeys(hints))[:250]
            roots=[]
            for pat in [r'baseURL\s*:\s*["\']([^"\']+)',r'baseURL\s*=\s*["\']([^"\']+)']:
                for m in re.finditer(pat,js,re.I): roots.append(m.group(1))
            for u in clean:
                lu=u.lower()
                if any(k in lu for k in ("watchhealth","api","service")):
                    p=urllib.parse.urlsplit(u)
                    if p.scheme and p.netloc:
                        roots.append(f"{p.scheme}://{p.netloc}{p.path.rstrip('/')}")
            roots += ["https://wr.watchhealth.com.cn","https://wr.watchhealth.com.cn/api","https://wr.watchhealth.com.cn/prod-api"]
            norm=[]
            for r in roots:
                try:
                    if r.startswith("/"): r=urllib.parse.urljoin(portal,r)
                    r=r.rstrip("/")
                    if r and r not in norm: norm.append(r)
                except Exception: pass
            report["candidate_api_bases"]=norm
            endpoint="/upgrade/getUpgradeInfoList"; params={"currentPage":"1","pageSize":"100","watchId":"1180"}
            for root in norm[:40]:
                full=root if root.lower().endswith(endpoint.lower()) else root+endpoint
                full=full+("&" if "?" in full else "?")+urllib.parse.urlencode(params)
                try:
                    txt,s,c,h=get(full,7,2_000_000)
                    rec={"url":full,"status":s,"content_type":c,"bytes":len(txt),"preview":txt[:12000]}
                    try:
                        obj=json.loads(txt);rec["json"]=obj;stack=[("$",obj)]
                        while stack:
                            path,x=stack.pop()
                            if isinstance(x,dict):
                                for k,v in x.items(): stack.append((path+"."+str(k),v))
                            elif isinstance(x,list):
                                for i,v in enumerate(x): stack.append((path+f"[{i}]",v))
                            elif isinstance(x,str):
                                lx=x.lower()
                                if x.startswith(("http://","https://")) or any(z in lx for z in (".bin",".zip",".img","firmware","upgrade")):
                                    report["firmware_candidates"].append({"path":path,"value":x,"source_url":full})
                    except Exception: pass
                    report["requests"].append(rec)
                except Exception as ex:
                    report["requests"].append({"url":full,"error":type(ex).__name__+": "+str(ex)})
            seen=set();uniq=[]
            for x in report["firmware_candidates"]:
                k=(x.get("path"),x.get("value"))
                if k in seen: continue
                seen.add(k);uniq.append(x)
            report["firmware_candidates"]=uniq
            report["elapsed_s"]=(datetime.now(timezone.utc)-started).total_seconds()
            folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","firmware-v153");os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,"utrawatch-api-config-v153.json");report["saved_path"]=out
            report["notes"].append("Se obtuvo al menos un candidato desde una raíz API derivada del cliente real. No se descargó ni escribió firmware." if report["firmware_candidates"] else "Se extrajeron baseURL/auth hints y respuestas para identificar el requisito exacto de acceso en la siguiente pasada. No hubo escrituras OTA.")
            with open(out,"w",encoding="utf-8") as fh: json.dump(report,fh,ensure_ascii=False,indent=2)
            return report

        def done(report,error):
            if error:
                self.status.set("V1.53 · extracción API falló: "+repr(error));return
            self.report={"api_config_v153":report};self.show()
            try:
                txt=json.dumps(report,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(txt);self.root.update_idletasks()
            except Exception: pass
            self.status.set(f"V1.53 LISTO · {len(report.get('candidate_api_bases',[]))} raíces · {len(report.get('firmware_candidates',[]))} candidatos · diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=="__main__":
    root=tk.Tk();AppV153(root);root.mainloop()
