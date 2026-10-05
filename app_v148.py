import concurrent.futures, hashlib, json, os, urllib.parse, urllib.request
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, messagebox
import app as base
import app_v147 as v147
import app_v145 as v145

base.APP_VERSION="1.48.0"

class AppV148(v147.AppV147):
    def __init__(self,root):
        super().__init__(root)
        root.title("Reloj Lab V1.48")
        self._retitle_v148(root)
        self.status.set("V1.48 lista · búsqueda paralela con progreso y límite total; no puede quedar buscando indefinidamente.")

    def _retitle_v148(self,widget):
        try:
            if isinstance(widget,ttk.Label):
                t=str(widget.cget("text"))
                if "V1.47" in t: widget.configure(text=t.replace("V1.47","V1.48"))
        except Exception: pass
        try:
            for child in widget.winfo_children(): self._retitle_v148(child)
        except Exception: pass

    def _ui_status(self,text):
        try:self.root.after(0,lambda t=text:self.status.set(t))
        except Exception:pass

    def find_exact_firmware(self):
        self.face_guard_enabled=False
        if self.face_guard_future:
            try:self.face_guard_future.cancel()
            except Exception:pass
            self.face_guard_future=None
        ready,validation,validation_path=self._ready_report()
        if not ready:
            messagebox.showinfo("V1.48","No encuentro la validación BK3288 lista. Ejecutá VALIDAR BK3288 PARA BLOQUEO una vez.")
            return
        self.status.set("V1.48 · preparando búsqueda rápida de firmware…")

        def work():
            started=datetime.now(timezone.utc)
            report={"app_version":"1.48.0","generated_utc":started.isoformat(),
                    "goal":"fast_exact_bk3288_firmware_discovery","validated_profile":validation,
                    "validation_path":validation_path,"expected":v145.EXPECTED,
                    "mode":{"parallel_workers":16,"per_request_timeout_s":3.0,"global_limit_s":120,"max_urls":180},
                    "attempts":[],"candidates":[],"selected":None,
                    "safety":{"firmware_writes":0,"ota_writes":0},"notes":[]}
            folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","firmware-v148")
            os.makedirs(folder,exist_ok=True)
            hosts=["http://watchhealth.com.cn","https://watchhealth.com.cn","https://wr.watchhealth.com.cn"]
            roots=["/k6File/firmware/file/","/k6File/ota/file/","/k6File/update/file/","/k6File/watch/file/","/firmware/","/ota/"]
            names=["BK3288-Watch-1.0.bin","BK3288-Watch-1.0_6.3.0.bin","BK3288-Watch-1.0-6.3.0.bin",
                   "BK3288_6.3.0.bin","BK3288-6.3.0.bin","BK3288.bin","6.3.0.bin","0.0.1.bin",
                   "BK3288_Watch_1.0.bin","BK3288-Watch-1.0_0.0.1.bin"]
            urls=[h+r+n for h in hosts for r in roots for n in names][:180]
            ua="Mozilla/5.0 RelojLab/1.48"

            def probe(url):
                item={"url":url,"stage":"probe"}
                try:
                    req=urllib.request.Request(url,headers={"User-Agent":ua,"Range":"bytes=0-65535"})
                    with urllib.request.urlopen(req,timeout=3.0) as resp:
                        status=getattr(resp,"status",200); ctype=(resp.headers.get("Content-Type") or "").lower()
                        chunk=resp.read(65536); final=resp.geturl(); clen=resp.headers.get("Content-Length")
                    item.update({"status":status,"content_type":ctype,"content_length":clen,"final_url":final,"probe_bytes":len(chunk)})
                    binaryish=("text/html" not in ctype and "application/json" not in ctype and len(chunk)>=1024)
                    if not binaryish:return item,None
                    req2=urllib.request.Request(final,headers={"User-Agent":ua})
                    with urllib.request.urlopen(req2,timeout=8.0) as resp2:
                        declared=resp2.headers.get("Content-Length")
                        if declared and int(declared)>32*1024*1024:raise RuntimeError("candidate too large")
                        data=resp2.read(32*1024*1024+1)
                    if len(data)>32*1024*1024:raise RuntimeError("candidate exceeds 32 MiB")
                    sha=hashlib.sha256(data).hexdigest()
                    markers={"model":data.find(b"BK3288-Watch-1.0"),"software":data.find(b"6.3.0"),
                             "firmware":data.find(b"0.0.1"),"binid_ascii":data.find(b"5578"),
                             "binid_bytes":data.find(bytes.fromhex("5578"))}
                    score=(4 if "bk3288" in final.lower() else 0)+(2 if "6.3.0" in final.lower() else 0)
                    score+=(8 if markers["model"]>=0 else 0)+(4 if markers["software"]>=0 else 0)+(2 if markers["firmware"]>=0 else 0)
                    bn=os.path.basename(urllib.parse.urlparse(final).path) or (sha[:12]+".bin")
                    if not bn.lower().endswith(".bin"):bn+=".bin"
                    save=os.path.join(folder,sha[:12]+"-"+bn)
                    with open(save,"wb") as fh:fh.write(data)
                    cand={"url":final,"file":save,"size":len(data),"sha256":sha,"markers":markers,"score":score}
                    item["candidate"]=cand
                    return item,cand
                except Exception as ex:
                    item["error"]=type(ex).__name__+": "+str(ex)
                    return item,None

            completed=0
            selected=None
            executor=concurrent.futures.ThreadPoolExecutor(max_workers=16)
            futures={executor.submit(probe,u):u for u in urls}
            try:
                for fut in concurrent.futures.as_completed(futures,timeout=120):
                    completed+=1
                    try:item,cand=fut.result()
                    except Exception as ex:item={"url":futures[fut],"error":repr(ex)};cand=None
                    report["attempts"].append(item)
                    if cand:
                        report["candidates"].append(cand)
                        if selected is None or cand.get("score",0)>selected.get("score",0): selected=cand
                    if completed==1 or completed%5==0 or cand:
                        self._ui_status(f"V1.48 · buscando firmware · ruta {completed}/{len(urls)} · candidatos {len(report['candidates'])}")
                    if cand and cand.get("score",0)>=8:
                        selected=cand
                        report["notes"].append("Candidato de alta confianza encontrado; se detuvo la búsqueda anticipadamente.")
                        break
            except concurrent.futures.TimeoutError:
                report["notes"].append("Límite global de 120 s alcanzado; se conservaron todos los resultados obtenidos.")
            finally:
                for f in futures:
                    if not f.done():f.cancel()
                executor.shutdown(wait=False,cancel_futures=True)

            report["selected"]=selected
            report["completed_probes"]=completed
            report["total_planned_probes"]=len(urls)
            report["elapsed_s"]=(datetime.now(timezone.utc)-started).total_seconds()
            if selected is None:report["notes"].append("No se encontró .bin directo en esta pasada rápida; la app terminó normalmente.")
            out=os.path.join(folder,"firmware-discovery-v148.json")
            with open(out,"w",encoding="utf-8") as fh:json.dump(report,fh,ensure_ascii=False,indent=2)
            report["saved_path"]=out
            return report

        def done(report,error):
            if error:
                self.status.set("V1.48 búsqueda terminó con error: "+repr(error));return
            self.report={"firmware_discovery":report};self.show()
            try:
                txt=json.dumps(report,ensure_ascii=False,indent=2);self.root.clipboard_clear();self.root.clipboard_append(txt);self.root.update_idletasks()
            except Exception:pass
            if report.get("selected"):
                self.status.set("V1.48 LISTO · candidato encontrado; diagnóstico copiado. Pegámelo en ChatGPT.")
            else:
                self.status.set("V1.48 LISTO · búsqueda terminada sin candidato directo; diagnóstico copiado. Pegámelo en ChatGPT.")
        self.run_thread(work,done)

if __name__=="__main__":
    root=tk.Tk();AppV148(root);root.mainloop()
