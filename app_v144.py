import asyncio, json, os, time
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, messagebox
from bleak import BleakClient
import app as base

base.APP_VERSION="1.44.0"

B001="0000b001-0000-1000-8000-00805f9b34fb"
B002="0000b002-0000-1000-8000-00805f9b34fb"
FFC1="f000ffc1-0451-4000-b000-000000000000"
FFC2="f000ffc2-0451-4000-b000-000000000000"

class AppV144(base.App):
    def __init__(self,root):
        super().__init__(root)
        root.title("Reloj Lab V1.44")
        self._retitle(root)
        top=root.winfo_children()[0] if root.winfo_children() else root
        ttk.Button(top,text="PREPARAR BLOQUEO SIN PC",command=self.prepare_autonomous_lock_profile).pack(side="right",padx=8)
        self.status.set("V1.44 lista · PREPARAR BLOQUEO SIN PC obtiene la huella necesaria para el parche autónomo.")

    def _retitle(self,widget):
        try:
            if isinstance(widget,ttk.Label):
                t=str(widget.cget("text"))
                if "V1.43" in t:
                    widget.configure(text=t.replace("V1.43","V1.44").replace("GUARDIA PERSISTENTE CON RECONEXIÓN","PREPARACIÓN DE BLOQUEO AUTÓNOMO"))
        except Exception:
            pass
        try:
            for child in widget.winfo_children():
                self._retitle(child)
        except Exception:
            pass

    def prepare_autonomous_lock_profile(self):
        target=self.load_saved_face_lock()
        if not target:
            messagebox.showinfo("Bloqueo sin PC","Primero fijá la esfera que querés conservar con FIJAR ESFERA ACTUAL COMO ÚNICA.")
            return
        if self.ble_busy:
            self.status.set("Esperá a que termine la operación Bluetooth actual.")
            return

        self.face_guard_enabled=False
        if self.face_guard_future:
            try:self.face_guard_future.cancel()
            except Exception:pass
            self.face_guard_future=None

        if not self.selected or not self.selected.get("address"):
            self.selected={
                "name":target.get("name") or "Apple Watch Ultra",
                "address":target.get("address"),
                "service_uuids":[],"manufacturer_data":{},"service_data":{}
            }

        self.status.set("V1.44 · leyendo identidad completa, DEVINFO y OTA sin flashear…")

        async def work():
            profile={
                "app":"Reloj Lab","app_version":"1.44.0",
                "generated_utc":datetime.now(timezone.utc).isoformat(),
                "goal":"autonomous_watch_face_lock_without_pc",
                "target_face":target,
                "device":{k:v for k,v in (self.selected or {}).items() if k not in ("device","_watch_score")},
                "standard_reads":{},"services":[],"oad":{},"e91a":{},"errors":[],
                "safety":{"firmware_writes":0,"ota_writes":0,"control_queries":0}
            }
            c=None
            try:
                c,n=await self.connect_retry(2,lambda m:self.ui_queue.put(lambda x=m:self.status.set("V1.44 · "+x)))
                profile["connection_attempts"]=n
                std={
                    "manufacturer":"00002a29-0000-1000-8000-00805f9b34fb",
                    "model":"00002a24-0000-1000-8000-00805f9b34fb",
                    "serial":"00002a25-0000-1000-8000-00805f9b34fb",
                    "hardware":"00002a27-0000-1000-8000-00805f9b34fb",
                    "firmware":"00002a26-0000-1000-8000-00805f9b34fb",
                    "software":"00002a28-0000-1000-8000-00805f9b34fb"
                }
                for name,u in std.items():
                    try:
                        v=bytes(await asyncio.wait_for(c.read_gatt_char(u),timeout=3))
                        profile["standard_reads"][name]={"hex":v.hex(),"text":v.decode("utf-8","replace").strip("\x00")}
                    except Exception as ex:
                        profile["standard_reads"][name]={"error":repr(ex)}

                for svc in c.services:
                    sd={"uuid":svc.uuid,"description":getattr(svc,"description",None),"characteristics":[]}
                    for ch in svc.characteristics:
                        cd={"uuid":ch.uuid,"handle":ch.handle,"properties":list(ch.properties)}
                        sd["characteristics"].append(cd)
                        lu=ch.uuid.lower()
                        if lu in (FFC1,FFC2):
                            profile["oad"][lu]=cd
                    profile["services"].append(sd)
                profile["oad"]["service_present"]=any(str(x.get("uuid","")).lower()==base.OAD_SERVICE.lower() for x in profile["services"])

                messages=[];current=None;tx_n=1;dev_type=1
                def complete(msg):messages.append(msg)
                def rx(sender,data):
                    nonlocal current
                    b=bytes(data)
                    if not b:return
                    if b[0]==0:
                        if len(b)<10:return
                        total=int.from_bytes(b[8:10],"little")
                        current={"send_type":b[4],"opcode":b[5],"total":total,"data":bytearray(b[10:10+min(total,10)]),"next":1}
                        if len(current["data"])>=total:
                            m=current;current=None;m["payload"]=bytes(m["data"][:total]);complete(m)
                    elif current is not None and b[0]==current["next"]:
                        current["data"].extend(b[1:20]);current["next"]+=1
                        if len(current["data"])>=current["total"]:
                            m=current;current=None;m["payload"]=bytes(m["data"][:m["total"]]);complete(m)

                await asyncio.wait_for(c.start_notify(B001,rx),timeout=8)
                await asyncio.sleep(.3)

                def build(op,payload=b"",send_type=1):
                    nonlocal tx_n
                    payload=bytes(payload);n=len(payload);h=bytearray(20)
                    h[1]=dev_type;h[3]=tx_n&255;h[4]=send_type;h[5]=op;h[8]=n&255;h[9]=(n>>8)&255
                    frames=[]
                    if n<=10:
                        h[10:10+n]=payload;frames=[bytes(h)]
                    else:
                        frags=((n-10)+18)//19;h[2]=frags;h[10:20]=payload[:10];frames=[bytes(h)]
                        pos=10
                        for i in range(frags):
                            z=bytearray(20);z[0]=i+1;part=payload[pos:pos+19];z[1:1+len(part)]=part;frames.append(bytes(z));pos+=len(part)
                    tx_n=(tx_n+1)&255
                    return frames

                async def query(op,timeout=5):
                    start=len(messages)
                    for fr in build(op,b"",3):
                        await asyncio.wait_for(c.write_gatt_char(B002,fr,response=False),timeout=5)
                        await asyncio.sleep(.05)
                    profile["safety"]["control_queries"]+=1
                    end=time.monotonic()+timeout
                    while time.monotonic()<end:
                        for m in reversed(messages[start:]):
                            if m.get("opcode")==op and m.get("send_type")==1:
                                return m.get("payload",b"")
                        await asyncio.sleep(.08)
                    return None

                dev=await query(0x02,5)
                profile["e91a"]["devinfo_raw_hex"]=dev.hex() if dev is not None else None
                if dev:
                    profile["e91a"]["customer_id"]=dev[1] if len(dev)>1 else None
                    profile["e91a"]["hardware_tuple"]=list(dev[2:6]) if len(dev)>=6 else None
                    profile["e91a"]["devinfo_length"]=len(dev)

                face=await query(0x84,5)
                profile["e91a"]["watch_face_info_raw_hex"]=face.hex() if face is not None else None
                if face and len(face)>=9:
                    profile["e91a"]["active_face"]={"index":face[0],"cmd3_raw":face[7:9].hex()}
                    profile["e91a"]["target_matches_current"]=(
                        int(target.get("index",-1))==face[0] and
                        ((target.get("cmd3_raw") or "").lower() in ("",face[7:9].hex().lower()))
                    )
                try:await c.stop_notify(B001)
                except Exception:pass

            except Exception as ex:
                profile["errors"].append(type(ex).__name__+": "+str(ex))
            finally:
                if c:
                    try:await asyncio.wait_for(c.disconnect(),timeout=5)
                    except Exception as ex:profile["errors"].append("disconnect: "+repr(ex))
            return profile

        def done(profile,error):
            if error:
                self.status.set("V1.44 falló: "+repr(error));return
            folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab")
            os.makedirs(folder,exist_ok=True)
            path=os.path.join(folder,"autonomous-lock-profile-v144.json")
            with open(path,"w",encoding="utf-8") as fh:json.dump(profile,fh,ensure_ascii=False,indent=2)
            profile["saved_path"]=path
            self.report={"autonomous_lock_profile":profile}
            self.show()
            try:
                txt=json.dumps(profile,ensure_ascii=False,indent=2)
                self.root.clipboard_clear();self.root.clipboard_append(txt);self.root.update_idletasks()
                copied=True
            except Exception:
                copied=False
            self.status.set("V1.44 perfil autónomo listo"+(" y copiado." if copied else ".")+" Pasámelo para construir el parche interno.")
            self.face_guard_enabled=False
        self.run_async(work(),done)

if __name__=="__main__":
    root=tk.Tk();AppV144(root);root.mainloop()
