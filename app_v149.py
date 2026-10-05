import concurrent.futures, json, os, re, urllib.parse, urllib.request
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, messagebox
import app as base
import app_v148 as v148
import app_v145 as v145

base.APP_VERSION="1.49.0"

class AppV149(v148.AppV148):
    def __init__(self,root):
        super().__init__(root)
        root.title("Reloj Lab V1.49")
        self._retitle_v149(root)
        top=root.winfo_children()[0] if root.winfo_children() else root
        ttk.Button(top,text="CONSULTAR API UTRAWATCH",command=self.query_utrawatch_api).pack(side="left",padx=8)
        self.status.set("V1.49 lista · consulta metadata del servidor UtraWatch en vez de adivinar nombres .bin.")

    def _retitle_v149(self,widget):
        try:
            if isinstance(widget,ttk.Label):
                t=str(widget.cget("text"))
                if "V1.48" in t: widget.configure(text=t.replace("V1.48","V1.49"))
        except Exception: pass
        try:
            for child in widget.winfo_children(): self._retitle_v149(child)
        except Exception: pass

    def _ui_status149(self,text):
        try:self.root.after(0,lambda t=text:self.status.set(t))
        except Exception:pass

    def query_utrawatch_api(self):
        ready,validation,validation_path=self._ready_report()
        if not ready:
            messagebox.showinfo("V1.49","Primero necesitás la validación BK3288 con ready_for_firmware_patch=true.")
            return
        self.face_guard_enabled=False
        self.status.set("V1.49 · consultando APIs de UtraWatch…")

        def work():
            started=datetime.now(timezone.utc)
            report={
                "app_version":"1.49.0","generated_utc":started.isoformat(),
                "goal":"discover_firmware_from_utrawatch_server_metadata",
                "validated_profile":validation,"validation_path":validation_path,
                "expected":v145.EXPECTED,"requests":[],"firmware_urls":[],"responses_with_metadata":[],
                "safety":{"firmware_writes":0,"ota_writes":0},"notes":[]
            }
            folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","firmware-v149")
            os.makedirs(folder,exist_ok=True)
            base_urls=["http://watchhealth.com.cn/YueDongService/app/","https://wr.watchhealth.com.cn/YueDongService/app/"]
            endpoints=[
                "faceConfig.do","faces.do","firmware.do","firmwares.do","firmwareVersion.do",
                "deviceFirmware.do","deviceVersion.do","version.do","versions.do","upgrade.do",
                "update.do","ota.do","checkUpdate.do","getFirmware.do","getVersion.do"
            ]
            param_sets=[
                {"deviceId":"102"}, {"deviceId":"1180"},
                {"deviceId":"102","version":"6.3.0"}, {"deviceId":"1180","version":"6.3.0"},
                {"model":"BK3288-Watch-1.0","version":"6.3.0"},
                {"product":"BK3288-Watch-1.0","software":"6.3.0"},
                {"customerId":"255","hw1":"3","hw2":"1","hw3":"1","hw4":"1","version":"6.3.0"},
                {"customerId":"255","hardware":"3,1,1,1","software":"6.3.0"}
            ]
            jobs=[]
            for b in base_urls:
                for ep in endpoints:
                    for params in param_sets:
                        jobs.append((b+ep,params))
            url_re=re.compile(r'https?://[^\"\'<>\\s]+',re.I)
            key_re=re.compile(r'firmware|upgrade|update|ota|file|url|version|device|model|bin',re.I)

            def inspect(url,params):
                q=urllib.parse.urlencode(params)
                full=url+("?"+q if q else "")
                item={"url":full,"endpoint":url.rsplit("/",1)[-1],"params":params}
                try:
                    req=urllib.request.Request(full,headers={"User-Agent":"Mozilla/5.0 RelojLab/1.49","Accept":"application/json,text/plain,*/*"})
                    with urllib.request.urlopen(req,timeout=4.0) as resp:
                        raw=resp.read(512000);ctype=(resp.headers.get("Content-Type") or "").lower();status=getattr(resp,"status",200)
                    text=raw.decode("utf-8","replace")
                    item.update({"status":status,"content_type":ctype,"bytes":len(raw),"preview":text[:3000]})
                    urls=[]
                    for u in url_re.findall(text):
                        u=u.rstrip('),]}')
                        if any(x in u.lower() for x in (".bin","firmware","upgrade","/ota/","k6file")):urls.append(u)
                    meaningful=bool(urls or key_re.search(text)) and not (len(text.strip())<3)
                    return item,urls,meaningful
                except Exception as ex:
                    item["error"]=type(ex).__name__+": "+str(ex)
                    return item,[],False

            completed=0
            with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
                futs={ex.submit(inspect,u,p):(u,p) for u,p in jobs}
                for fut in concurrent.futures.as_completed(futs):
                    completed+=1
                    try:item,urls,meaningful=fut.result()
                    except Exception as err:
                        u,p=futs[fut];item={"url":u,"params":p,"error":repr(err)};urls=[];meaningful=False
                    report["requests"].append(item)
                    for u in urls:
                        if u not in report["firmware_urls"]:report["firmware_urls"].append(u)
                    if meaningful and not item.get("error"):
                        report["responses_with_metadata"].append({k:item.get(k) for k in ("url","status","content_type","preview")})
                    if completed==1 or completed%20==0 or urls:
                        self._ui_status149(f"V1.49 · API UtraWatch {completed}/{len(jobs)} · URLs firmware {len(report['firmware_urls'])}")

            # Also query the two endpoints we already know are real, preserving the returned metadata verbatim.
            known=[
                "http://watchhealth.com.cn/YueDongService/app/faceConfig.do?deviceId=102&pageIndex=1",
                "http://watchhealth.com.cn/YueDongService/app/faceConfig.do?deviceId=1180&pageIndex=1",
                "http://watchhealth.com.cn/YueDongService/app/faces.do?deviceId=102&pageIndex=0",
                "http://watchhealth.com.cn/YueDongService/app/faces.do?deviceId=1180&pageIndex=0"
            ]
            for full in known:
                try:
                    req=urllib.request.Request(full,headers={"User-Agent":"Mozilla/5.0 RelojLab/1.49"})
                    with urllib.request.urlopen(req,timeout=8) as resp:raw=resp.read(512000)
                    text=raw.decode("utf-8","replace")
                    report["requests"].append({"url":full,"stage":"known-real-endpoint","status":200,"preview":text[:12000]})
                    for u in url_re.findall(text):
                        if any(x in u.lower() for x in (".bin","firmware","upgrade","/ota/","k6file")) and u not in report["firmware_urls"]:
                            report["firmware_urls"].append(u)
                except Exception as ex:
                    report["requests"].append({"url":full,"stage":"known-real-endpoint","error":repr(ex)})

            report["completed_requests"]=len(report["requests"])
            report["elapsed_s"]=(datetime.now(timezone.utc)-started).total_seconds()
            if report["firmware_urls"]:
                report["notes"].append("Se encontraron URLs candidatas en metadata del servidor. No se realizó ninguna escritura OTA.")
            else:
                report["notes"].append("No apareció una URL de firmware directa; se guardaron respuestas y endpoints útiles para la siguiente pasada.")
            out=os.path.join(folder,"utrawatch-api-v149.json")
            with open(out,"w",encoding="utf-8") as fh:json.dump(report,fh,ensure_ascii=False,indent=2)
            report["saved_path"]=out
            return report

        def done(report,error):
            if error:
                self.status.set("V1.49 API terminó con error: "+repr(error));return
            self.report={"utrawatch_api":report};self.show()
            try:
                txt=json.dumps(report,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(txt);self.root.update_idletasks()
            except Exception:pass
            if report.get("firmware_urls"):
                self.status.set(f"V1.49 LISTO · encontré {len(report['firmware_urls'])} URL(s) candidata(s); diagnóstico copiado.")
            else:
                self.status.set("V1.49 LISTO · API consultada sin URL directa; diagnóstico copiado.")
        self.run_thread(work,done)

if __name__=="__main__":
    root=tk.Tk();AppV149(root);root.mainloop()
