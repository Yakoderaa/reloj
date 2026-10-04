import hashlib, json, os, re, urllib.parse, urllib.request
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, messagebox
import app as base
import app_v145 as v145

base.APP_VERSION="1.46.0"

class AppV146(v145.AppV145):
    def __init__(self,root):
        super().__init__(root)
        root.title("Reloj Lab V1.46")
        self._retitle_v146(root)
        top=root.winfo_children()[0] if root.winfo_children() else root
        ttk.Button(top,text="BUSCAR FIRMWARE EXACTO",command=self.find_exact_firmware).pack(side="right",padx=8)
        self.status.set("V1.46 lista · busca automáticamente firmware BK3288 en fuentes públicas del proveedor; no escribe OTA.")

    def _retitle_v146(self,widget):
        try:
            if isinstance(widget,ttk.Label):
                t=str(widget.cget("text"))
                if "V1.45" in t:
                    widget.configure(text=t.replace("V1.45","V1.46").replace("BK3288 · PREPARACIÓN DE PARCHE AUTÓNOMO","BK3288 · DESCUBRIMIENTO DE FIRMWARE"))
        except Exception:
            pass
        try:
            for child in widget.winfo_children():self._retitle_v146(child)
        except Exception:
            pass

    def _ready_report(self):
        path=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","bk3288-lock-ready-v145.json")
        try:
            with open(path,"r",encoding="utf-8") as fh:r=json.load(fh)
            return bool(r.get("ready_for_firmware_patch")),r,path
        except Exception as ex:
            return False,{"error":repr(ex)},path

    def find_exact_firmware(self):
        ready,validation,validation_path=self._ready_report()
        if not ready:
            messagebox.showinfo("V1.46","Primero ejecutá VALIDAR BK3288 PARA BLOQUEO en V1.45/V1.46 hasta obtener ready_for_firmware_patch=true.")
            return
        self.status.set("V1.46 · buscando firmware exacto BK3288 en fuentes públicas del proveedor…")

        def work():
            report={
                "app_version":"1.46.0",
                "generated_utc":datetime.now(timezone.utc).isoformat(),
                "goal":"discover_exact_bk3288_original_firmware",
                "validated_profile":validation,
                "validation_path":validation_path,
                "expected":v145.EXPECTED,
                "attempts":[],"discovered_links":[],"candidates":[],"selected":None,
                "safety":{"firmware_writes":0,"ota_writes":0},
                "notes":[]
            }
            folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","firmware-v146")
            os.makedirs(folder,exist_ok=True)
            ua="Mozilla/5.0 RelojLab/1.46"

            hosts=["http://watchhealth.com.cn","https://watchhealth.com.cn","https://wr.watchhealth.com.cn"]
            roots=["/k6File/firmware/file/","/k6File/ota/file/","/k6File/update/file/","/k6File/watch/file/","/firmware/","/ota/","/update/","/data/firmware/","/data/ota/"]
            names=[
                "BK3288-Watch-1.0.bin","BK3288-Watch-1.0_6.3.0.bin","BK3288-Watch-1.0-6.3.0.bin",
                "BK3288_6.3.0.bin","BK3288-6.3.0.bin","BK3288.bin","6.3.0.bin","0.0.1.bin",
                "BK3288_Watch_1.0.bin","BK3288-Watch-1.0_0.0.1.bin"
            ]
            urls=[]
            for h in hosts:
                for r in roots:
                    for n in names:urls.append(h+r+n)

            crawl=["http://watchhealth.com.cn/","https://watchhealth.com.cn/","https://wr.watchhealth.com.cn/"]
            link_re=re.compile(rb"https?://[^\"'<> ]+|(?:href|src)=[\"']([^\"']+)[\"']",re.I)
            for page in crawl:
                try:
                    req=urllib.request.Request(page,headers={"User-Agent":ua})
                    with urllib.request.urlopen(req,timeout=8) as resp:
                        data=resp.read(512000)
                    for m in link_re.finditer(data):
                        raw=m.group(1) if m.group(1) else m.group(0)
                        try:s=raw.decode("utf-8","ignore")
                        except:continue
                        u=urllib.parse.urljoin(page,s)
                        lu=u.lower()
                        if any(x in lu for x in (".bin","firmware","upgrade","/ota/")):
                            report["discovered_links"].append(u)
                except Exception as ex:
                    report["attempts"].append({"url":page,"stage":"crawl","error":type(ex).__name__+": "+str(ex)})
            for u in report["discovered_links"]:
                if u not in urls:urls.insert(0,u)

            seen=set();urls=[u for u in urls if not (u in seen or seen.add(u))]
            for i,url in enumerate(urls[:320],1):
                item={"url":url,"stage":"probe"}
                try:
                    req=urllib.request.Request(url,headers={"User-Agent":ua,"Range":"bytes=0-65535"})
                    with urllib.request.urlopen(req,timeout=6) as resp:
                        status=getattr(resp,"status",200)
                        ctype=(resp.headers.get("Content-Type") or "").lower()
                        clen=resp.headers.get("Content-Length")
                        chunk=resp.read(65536)
                        final_url=resp.geturl()
                    item.update({"status":status,"content_type":ctype,"content_length":clen,"final_url":final_url,"probe_bytes":len(chunk)})
                    binaryish=("text/html" not in ctype and "application/json" not in ctype and len(chunk)>=1024)
                    if binaryish:
                        req2=urllib.request.Request(final_url,headers={"User-Agent":ua})
                        with urllib.request.urlopen(req2,timeout=20) as resp2:
                            declared=resp2.headers.get("Content-Length")
                            if declared and int(declared)>32*1024*1024:raise RuntimeError("candidate too large: "+declared)
                            data=resp2.read(32*1024*1024+1)
                        if len(data)>32*1024*1024:raise RuntimeError("candidate exceeds 32 MiB")
                        sha=hashlib.sha256(data).hexdigest()
                        bn=os.path.basename(urllib.parse.urlparse(final_url).path) or ("candidate-%03d.bin"%i)
                        if not bn.lower().endswith(".bin"):bn+=".bin"
                        save=os.path.join(folder,bn)
                        if os.path.exists(save):save=os.path.join(folder,sha[:12]+"-"+bn)
                        with open(save,"wb") as fh:fh.write(data)
                        markers={"model":data.find(b"BK3288-Watch-1.0"),"software":data.find(b"6.3.0"),"firmware":data.find(b"0.0.1"),"binid_ascii":data.find(b"5578"),"binid_bytes":data.find(bytes.fromhex("5578"))}
                        score=0
                        if "bk3288" in final_url.lower():score+=4
                        if "6.3.0" in final_url.lower():score+=2
                        if markers["model"]>=0:score+=8
                        if markers["software"]>=0:score+=4
                        if markers["firmware"]>=0:score+=2
                        cand={"url":final_url,"file":save,"size":len(data),"sha256":sha,"markers":markers,"score":score}
                        report["candidates"].append(cand)
                        item["candidate"]=cand
                        if score>=8:
                            report["selected"]=cand
                            report["notes"].append("High-confidence firmware candidate found; no OTA write performed.")
                            report["attempts"].append(item)
                            break
                except Exception as ex:
                    item["error"]=type(ex).__name__+": "+str(ex)
                report["attempts"].append(item)

            if report["selected"] is None and report["candidates"]:
                report["candidates"].sort(key=lambda x:x.get("score",0),reverse=True)
                report["selected"]=report["candidates"][0]
                report["notes"].append("Candidate found but confidence is limited; it must be structurally validated before any OTA write.")
            if report["selected"] is None:
                report["notes"].append("No direct firmware binary found on the probed public vendor paths. The attempt map is preserved for the next discovery pass.")

            out=os.path.join(folder,"firmware-discovery-v146.json")
            with open(out,"w",encoding="utf-8") as fh:json.dump(report,fh,ensure_ascii=False,indent=2)
            report["saved_path"]=out
            return report

        def done(report,error):
            if error:
                self.status.set("V1.46 búsqueda falló: "+repr(error));return
            self.report={"firmware_discovery":report};self.show()
            try:
                txt=json.dumps(report,ensure_ascii=False,indent=2)
                self.root.clipboard_clear();self.root.clipboard_append(txt);self.root.update_idletasks()
            except Exception:pass
            if report.get("selected"):
                s=report["selected"]
                self.status.set("V1.46 encontró candidato firmware · SHA-256 "+s["sha256"][:16]+"… · diagnóstico copiado.")
            else:
                self.status.set("V1.46 terminó: no encontró .bin directo; mapa de rutas copiado para la próxima versión.")
        self.run_thread(work,done)

if __name__=="__main__":
    root=tk.Tk();AppV146(root);root.mainloop()
