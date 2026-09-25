import asyncio, json, platform, sys, threading, tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timezone
from bleak import BleakScanner, BleakClient

APP_VERSION="0.2.0"
OAD_SERVICE="f000ffc0-0451-4000-b000-000000000000"
CONTROL_SERVICE="0000e91a-0000-1000-8000-00805f9b34fb"
NOTIFY_UUIDS=["f000ffc2-0451-4000-b000-000000000000","0000b001-0000-1000-8000-00805f9b34fb"]

class App:
    def __init__(self,root):
        self.root=root; root.title("Reloj Lab - Protocol Discovery V0.2"); root.geometry("980x680")
        self.devices=[]; self.selected=None; self.report=None
        top=ttk.Frame(root,padding=12); top.pack(fill="x")
        ttk.Label(top,text="Reloj Lab",font=("Segoe UI",18,"bold")).pack(side="left")
        ttk.Label(top,text="V0.2 · BK3288 Protocol Discovery").pack(side="left",padx=12)
        ttk.Button(top,text="Buscar relojes",command=self.scan).pack(side="right")
        body=ttk.Frame(root,padding=(12,0,12,12)); body.pack(fill="both",expand=True)
        self.tree=ttk.Treeview(body,columns=("name","address","rssi"),show="headings",height=8)
        for c,t,w in [("name","Nombre Bluetooth",300),("address","Dirección/ID",360),("rssi","RSSI",90)]:
            self.tree.heading(c,text=t); self.tree.column(c,width=w)
        self.tree.pack(fill="x"); self.tree.bind("<<TreeviewSelect>>",self.pick)
        a=ttk.Frame(body); a.pack(fill="x",pady=8)
        self.diag=ttk.Button(a,text="DIAGNÓSTICO COMPLETO",command=self.diagnose,state="disabled"); self.diag.pack(side="left")
        self.listen=ttk.Button(a,text="ESCUCHAR RELOJ 60 s",command=self.listen_notifications,state="disabled"); self.listen.pack(side="left",padx=8)
        ttk.Button(a,text="Guardar diagnóstico",command=self.save).pack(side="left")
        self.status=tk.StringVar(value="Listo. Buscá y seleccioná el reloj.")
        ttk.Label(a,textvariable=self.status).pack(side="right")
        self.text=tk.Text(body,wrap="none",font=("Consolas",9)); self.text.pack(fill="both",expand=True)
        self.text.insert("end","V0.2: diagnóstico seguro de BK3288.\n\nPrimero DIAGNÓSTICO COMPLETO. Después usá ESCUCHAR RELOJ 60 s y, durante ese minuto, tocá funciones del reloj (pasos, pulso, ajustes) para capturar notificaciones BLE.\n\nEsta versión NO escribe características y NO inicia OAD/firmware.")
    def run_async(self,coro,done):
        def worker():
            try: r=asyncio.run(coro); self.root.after(0,lambda:done(r,None))
            except Exception as e: self.root.after(0,lambda:done(None,e))
        threading.Thread(target=worker,daemon=True).start()
    def scan(self):
        self.status.set("Buscando BLE durante 8 segundos…"); self.tree.delete(*self.tree.get_children()); self.devices=[]
        async def work():
            found=await BleakScanner.discover(timeout=8.0,return_adv=True); out=[]
            for _,(d,a) in found.items():
                out.append({"device":d,"name":a.local_name or d.name or "(sin nombre)","address":d.address,"rssi":a.rssi,
                    "service_uuids":list(a.service_uuids or []),"manufacturer_data":{str(k):v.hex() for k,v in a.manufacturer_data.items()},
                    "service_data":{str(k):v.hex() for k,v in a.service_data.items()},"tx_power":a.tx_power})
            return sorted(out,key=lambda x:x["rssi"] or -999,reverse=True)
        def done(r,e):
            if e: messagebox.showerror("Bluetooth",str(e)); self.status.set("Error de escaneo"); return
            self.devices=r
            for i,x in enumerate(r): self.tree.insert("","end",iid=str(i),values=(x["name"],x["address"],x["rssi"]))
            self.status.set(f"{len(r)} dispositivos encontrados.")
        self.run_async(work(),done)
    def pick(self,_=None):
        s=self.tree.selection()
        if s:
            self.selected=self.devices[int(s[0])]; self.diag.config(state="normal"); self.listen.config(state="normal")
            self.status.set("Seleccionado. Ejecutá DIAGNÓSTICO COMPLETO.")
    def base_report(self):
        return {"app":"Reloj Lab","app_version":APP_VERSION,"generated_utc":datetime.now(timezone.utc).isoformat(),
          "computer":{"platform":platform.platform(),"python":sys.version},"advertisement":{k:v for k,v in self.selected.items() if k!="device"},
          "identification":{"expected_family":"Beken BK3288","evidence":[],"caution":"Identificación basada en Device Information; no se escribe ni flashea."},
          "connection":{"connected":False},"services":[],"standard_reads":{},"passive_notifications":[],"safety":{"writes_performed":0,"firmware_actions":0},"errors":[]}
    def diagnose(self):
        if not self.selected:return
        self.status.set("Leyendo GATT y Device Information…")
        async def work():
            rep=self.base_report()
            try:
                async with BleakClient(self.selected["device"],timeout=20) as c:
                    rep["connection"]["connected"]=c.is_connected
                    for svc in c.services:
                        sd={"uuid":svc.uuid,"description":svc.description,"characteristics":[]}
                        for ch in svc.characteristics:
                            cd={"uuid":ch.uuid,"handle":ch.handle,"description":ch.description,"properties":list(ch.properties),"descriptors":[]}
                            for de in ch.descriptors: cd["descriptors"].append({"uuid":de.uuid,"handle":de.handle,"description":de.description})
                            if "read" in ch.properties:
                                try:
                                    v=bytes(await c.read_gatt_char(ch)); cd["read_hex"]=v.hex(); cd["read_text"]=v.decode("utf-8","replace").strip("\x00")
                                except Exception as ex: cd["read_error"]=str(ex)
                            sd["characteristics"].append(cd)
                        rep["services"].append(sd)
                    std={"manufacturer":"00002a29-0000-1000-8000-00805f9b34fb","model":"00002a24-0000-1000-8000-00805f9b34fb","serial":"00002a25-0000-1000-8000-00805f9b34fb","hardware":"00002a27-0000-1000-8000-00805f9b34fb","firmware":"00002a26-0000-1000-8000-00805f9b34fb","software":"00002a28-0000-1000-8000-00805f9b34fb"}
                    for k,u in std.items():
                        try:
                            v=bytes(await c.read_gatt_char(u)); rep["standard_reads"][k]={"hex":v.hex(),"text":v.decode("utf-8","replace").strip("\x00")}
                        except Exception as ex: rep["standard_reads"][k]={"error":str(ex)}
                    m=rep["standard_reads"].get("model",{}).get("text",""); mf=rep["standard_reads"].get("manufacturer",{}).get("text","")
                    if "BK3288" in m: rep["identification"]["evidence"].append("Model string contains BK3288")
                    if "Beken" in mf or "Beken" in mf.replace("crop","corp"): rep["identification"]["evidence"].append("Manufacturer string identifies Beken")
                    if any(s["uuid"].lower()==OAD_SERVICE for s in rep["services"]): rep["identification"]["evidence"].append("OAD-like F000FFC0 service present")
                    if any(s["uuid"].lower()==CONTROL_SERVICE for s in rep["services"]): rep["identification"]["evidence"].append("Vendor service E91A present")
            except Exception as ex: rep["errors"].append(str(ex))
            return rep
        def done(r,e):
            if e: messagebox.showerror("Diagnóstico",str(e)); return
            self.report=r; self.show(); self.status.set("Diagnóstico finalizado. Ahora ejecutá ESCUCHAR RELOJ 60 s.")
        self.run_async(work(),done)
    def listen_notifications(self):
        if not self.selected:return
        self.status.set("Escuchando 60 s. Usá funciones del reloj ahora…")
        async def work():
            events=[]; errs=[]
            try:
                async with BleakClient(self.selected["device"],timeout=20) as c:
                    def cb(sender,data):
                        events.append({"utc":datetime.now(timezone.utc).isoformat(),"uuid":str(sender.uuid),"handle":sender.handle,"hex":bytes(data).hex(),"length":len(data)})
                    started=[]
                    for u in NOTIFY_UUIDS:
                        try: await c.start_notify(u,cb); started.append(u)
                        except Exception as ex: errs.append(f"{u}: {ex}")
                    await asyncio.sleep(60)
                    for u in started:
                        try: await c.stop_notify(u)
                        except: pass
            except Exception as ex: errs.append(str(ex))
            return events,errs
        def done(r,e):
            if e: messagebox.showerror("Escucha",str(e)); return
            events,errs=r
            if self.report is None:self.report=self.base_report()
            self.report["passive_notifications"].extend(events); self.report["notification_errors"]=errs
            self.report["generated_utc"]=datetime.now(timezone.utc).isoformat(); self.show()
            self.status.set(f"Escucha finalizada: {len(events)} paquetes. Guardá el diagnóstico y pasámelo.")
        self.run_async(work(),done)
    def show(self):
        self.text.delete("1.0","end"); self.text.insert("end",json.dumps(self.report,ensure_ascii=False,indent=2))
    def save(self):
        if not self.report: messagebox.showinfo("Diagnóstico","Primero ejecutá el diagnóstico."); return
        p=filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("JSON","*.json")],initialfile="reloj-diagnostico-v0.2.json")
        if p:
            with open(p,"w",encoding="utf-8") as f: json.dump(self.report,f,ensure_ascii=False,indent=2)
            self.status.set("Diagnóstico guardado. Pasámelo por el chat.")
if __name__=="__main__":
    root=tk.Tk(); App(root); root.mainloop()
