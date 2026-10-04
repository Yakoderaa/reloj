import asyncio, hashlib, json, os
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import app as base
import app_v144 as v144

base.APP_VERSION="1.45.0"

EXPECTED={
    "manufacturer":"Bekencrop",
    "model":"BK3288-Watch-1.0",
    "serial":"1.0.0.0-LE",
    "hardware":"1.0.0",
    "firmware":"0.0.1",
    "software":"6.3.0",
    "target_index":7,
    "target_cmd3":"5578",
    "devinfo_raw":"0bff0301010193e41010208a",
    "customer_id":255,
    "hardware_tuple":[3,1,1,1],
    "oad_service":"f000ffc0-0451-4000-b000-000000000000",
    "oad_ident":"f000ffc1-0451-4000-b000-000000000000",
    "oad_notify":"f000ffc2-0451-4000-b000-000000000000"
}

class AppV145(v144.AppV144):
    def __init__(self,root):
        super().__init__(root)
        root.title("Reloj Lab V1.45")
        self._retitle_v145(root)
        top=root.winfo_children()[0] if root.winfo_children() else root
        ttk.Button(top,text="VALIDAR BK3288 PARA BLOQUEO",command=self.validate_exact_bk3288).pack(side="right",padx=8)
        ttk.Button(top,text="CARGAR FIRMWARE ORIGINAL",command=self.load_original_firmware).pack(side="right",padx=8)
        self.status.set("V1.45 lista · perfil BK3288 exacto cargado; no escribe firmware si la huella no coincide 100%.")

    def _retitle_v145(self,widget):
        try:
            if isinstance(widget,ttk.Label):
                t=str(widget.cget("text"))
                if "V1.44" in t:
                    widget.configure(text=t.replace("V1.44","V1.45").replace("PREPARACIÓN DE BLOQUEO AUTÓNOMO","BK3288 · PREPARACIÓN DE PARCHE AUTÓNOMO"))
        except Exception:
            pass
        try:
            for child in widget.winfo_children():self._retitle_v145(child)
        except Exception:
            pass

    def _read_text(self,c,uuid):
        async def inner():
            raw=bytes(await asyncio.wait_for(c.read_gatt_char(uuid),timeout=3))
            return raw.decode("utf-8","replace").strip("\x00"),raw.hex()
        return inner()

    def validate_exact_bk3288(self):
        target=self.load_saved_face_lock()
        if not target:
            messagebox.showinfo("V1.45","No encuentro face-lock.json. Fijá primero la esfera 5578.")
            return
        if self.ble_busy:
            self.status.set("Esperá a que termine la operación Bluetooth actual.");return
        self.face_guard_enabled=False
        if self.face_guard_future:
            try:self.face_guard_future.cancel()
            except Exception:pass
            self.face_guard_future=None
        if not self.selected or not self.selected.get("address"):
            self.selected={"name":target.get("name") or "Apple Watch Ultra","address":target.get("address"),
                           "service_uuids":[],"manufacturer_data":{},"service_data":{}}
        self.status.set("V1.45 · verificando huella exacta BK3288 antes de habilitar cualquier paso de firmware…")
        async def work():
            report={"app_version":"1.45.0","generated_utc":datetime.now(timezone.utc).isoformat(),
                    "expected":EXPECTED,"observed":{},"checks":{},"ready_for_firmware_patch":False,
                    "safety":{"firmware_writes":0,"ota_writes":0},"errors":[]}
            c=None
            try:
                c,n=await self.connect_retry(2)
                report["connection_attempts"]=n
                uuids={"manufacturer":"00002a29-0000-1000-8000-00805f9b34fb",
                       "model":"00002a24-0000-1000-8000-00805f9b34fb",
                       "serial":"00002a25-0000-1000-8000-00805f9b34fb",
                       "hardware":"00002a27-0000-1000-8000-00805f9b34fb",
                       "firmware":"00002a26-0000-1000-8000-00805f9b34fb",
                       "software":"00002a28-0000-1000-8000-00805f9b34fb"}
                for k,u in uuids.items():
                    try:
                        txt,hx=await self._read_text(c,u);report["observed"][k]={"text":txt,"hex":hx}
                    except Exception as ex:report["observed"][k]={"error":repr(ex)}
                services={str(s.uuid).lower():s for s in c.services}
                report["observed"]["oad_service_present"]=EXPECTED["oad_service"] in services
                ffc1=None;ffc2=None
                if EXPECTED["oad_service"] in services:
                    for ch in services[EXPECTED["oad_service"]].characteristics:
                        if ch.uuid.lower()==EXPECTED["oad_ident"]:ffc1=list(ch.properties)
                        if ch.uuid.lower()==EXPECTED["oad_notify"]:ffc2=list(ch.properties)
                report["observed"]["ffc1_properties"]=ffc1
                report["observed"]["ffc2_properties"]=ffc2
                for k in ("manufacturer","model","serial","hardware","firmware","software"):
                    report["checks"][k]=report["observed"].get(k,{}).get("text")==EXPECTED[k]
                report["checks"]["oad_service"]=bool(report["observed"]["oad_service_present"])
                report["checks"]["ffc1_write_without_response"]=bool(ffc1 and "write-without-response" in ffc1)
                report["checks"]["ffc2_notify"]=bool(ffc2 and "notify" in ffc2)
                report["checks"]["target_face_index"]=int(target.get("index",-1))==EXPECTED["target_index"]
                report["checks"]["target_face_binid"]=(target.get("cmd3_raw") or "").lower()==EXPECTED["target_cmd3"]
                report["ready_for_firmware_patch"]=all(report["checks"].values())
            except Exception as ex:report["errors"].append(type(ex).__name__+": "+str(ex))
            finally:
                if c:
                    try:await asyncio.wait_for(c.disconnect(),timeout=5)
                    except Exception:pass
            return report
        def done(report,error):
            if error:self.status.set("V1.45 validación falló: "+repr(error));return
            folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab")
            os.makedirs(folder,exist_ok=True)
            path=os.path.join(folder,"bk3288-lock-ready-v145.json")
            with open(path,"w",encoding="utf-8") as fh:json.dump(report,fh,ensure_ascii=False,indent=2)
            report["saved_path"]=path;self.report={"bk3288_lock_validation":report};self.show()
            if report["ready_for_firmware_patch"]:
                self.status.set("V1.45 · BK3288 verificado 100%. Ya se puede validar una imagen original antes de parchearla.")
            else:
                self.status.set("V1.45 · huella NO coincide al 100%; firmware bloqueado por seguridad.")
        self.run_async(work(),done)

    def load_original_firmware(self):
        path=filedialog.askopenfilename(title="Seleccioná firmware ORIGINAL BK3288",filetypes=[("Firmware BIN","*.bin"),("Todos","*.*")])
        if not path:return
        try:
            size=os.path.getsize(path)
            with open(path,"rb") as fh:
                sha=hashlib.file_digest(fh,"sha256").hexdigest()
            with open(path,"rb") as fh:
                raw=fh.read()
            markers={
                "BK3288-Watch-1.0":raw.find(b"BK3288-Watch-1.0"),
                "6.3.0":raw.find(b"6.3.0"),
                "5578_ascii":raw.find(b"5578"),
                "5578_bytes":raw.find(bytes.fromhex("5578")),
                "7855_bytes":raw.find(bytes.fromhex("7855"))
            }
            result={"app_version":"1.45.0","file":os.path.basename(path),"size":size,"sha256":sha,
                    "expected_device":EXPECTED,"markers":markers,
                    "safe_to_flash":False,
                    "reason":"V1.45 sólo cataloga y valida la imagen; no la flashea hasta identificar estructura/firmas y offsets de forma inequívoca."}
            folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab")
            os.makedirs(folder,exist_ok=True)
            out=os.path.join(folder,"bk3288-original-firmware-v145.json")
            with open(out,"w",encoding="utf-8") as fh:json.dump(result,fh,ensure_ascii=False,indent=2)
            result["saved_path"]=out;self.report={"firmware_candidate":result};self.show()
            self.status.set("Firmware original catalogado. SHA-256="+sha[:16]+"…; todavía NO se escribió al reloj.")
        except Exception as ex:
            messagebox.showerror("Firmware",repr(ex))

if __name__=="__main__":
    root=tk.Tk();AppV145(root);root.mainloop()
