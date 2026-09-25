import asyncio, json, platform, sys, threading, tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timezone
from bleak import BleakScanner, BleakClient

APP_VERSION="0.1.0"
class App:
    def __init__(self, root):
        self.root=root; self.root.title("Reloj Lab - Hardware Discovery V0.1"); self.root.geometry("900x620")
        self.devices=[]; self.selected=None; self.report=None
        top=ttk.Frame(root,padding=12); top.pack(fill="x")
        ttk.Label(top,text="Reloj Lab",font=("Segoe UI",18,"bold")).pack(side="left")
        ttk.Label(top,text="V0.1 · Hardware Discovery").pack(side="left",padx=12)
        ttk.Button(top,text="Buscar relojes",command=self.scan).pack(side="right")
        body=ttk.Frame(root,padding=(12,0,12,12)); body.pack(fill="both",expand=True)
        self.tree=ttk.Treeview(body,columns=("name","address","rssi"),show="headings",height=10)
        for c,t,w in [("name","Nombre Bluetooth",300),("address","Dirección/ID",360),("rssi","RSSI",90)]:
            self.tree.heading(c,text=t); self.tree.column(c,width=w)
        self.tree.pack(fill="x"); self.tree.bind("<<TreeviewSelect>>",self.pick)
        actions=ttk.Frame(body); actions.pack(fill="x",pady=10)
        self.diag=ttk.Button(actions,text="DIAGNÓSTICO COMPLETO",command=self.diagnose,state="disabled"); self.diag.pack(side="left")
        ttk.Button(actions,text="Guardar diagnóstico",command=self.save).pack(side="left",padx=8)
        self.status=tk.StringVar(value="Listo. Encendé Bluetooth y poné el reloj cerca.")
        ttk.Label(actions,textvariable=self.status).pack(side="right")
        self.text=tk.Text(body,wrap="none",font=("Consolas",9)); self.text.pack(fill="both",expand=True)
        self.text.insert("end","1) Pulsá Buscar relojes.\n2) Elegí el reloj.\n3) Pulsá DIAGNÓSTICO COMPLETO.\n4) Guardá el TXT/JSON y pasámelo.\n\nLa V0.1 solo lee información Bluetooth/GATT; no escribe ni flashea el reloj.")
    def run_async(self,coro,done):
        def worker():
            try: res=asyncio.run(coro); self.root.after(0,lambda:done(res,None))
            except Exception as e: self.root.after(0,lambda:done(None,e))
        threading.Thread(target=worker,daemon=True).start()
    def scan(self):
        self.status.set("Buscando dispositivos BLE durante 8 segundos…"); self.tree.delete(*self.tree.get_children()); self.devices=[]
        async def work():
            found=await BleakScanner.discover(timeout=8.0,return_adv=True)
            out=[]
            for _,pair in found.items():
                d,a=pair
                out.append({"device":d,"name":a.local_name or d.name or "(sin nombre)","address":d.address,"rssi":a.rssi,
                    "service_uuids":list(a.service_uuids or []),"manufacturer_data":{str(k):v.hex() for k,v in a.manufacturer_data.items()},
                    "service_data":{str(k):v.hex() for k,v in a.service_data.items()},"tx_power":a.tx_power})
            return sorted(out,key=lambda x:x["rssi"] if x["rssi"] is not None else -999,reverse=True)
        def done(res,err):
            if err: self.status.set("Error de escaneo"); messagebox.showerror("Bluetooth",str(err)); return
            self.devices=res
            for i,x in enumerate(res): self.tree.insert("", "end", iid=str(i), values=(x["name"],x["address"],x["rssi"]))
            self.status.set(f"{len(res)} dispositivos encontrados. Elegí el reloj.")
        self.run_async(work(),done)
    def pick(self,_=None):
        s=self.tree.selection()
        if s: self.selected=self.devices[int(s[0])]; self.diag.config(state="normal"); self.status.set("Reloj seleccionado. Ejecutá DIAGNÓSTICO COMPLETO.")
    def diagnose(self):
        if not self.selected:return
        sel=self.selected; self.status.set("Conectando y leyendo GATT… No apagues el reloj.")
        async def work():
            rep={"app":"Reloj Lab","app_version":APP_VERSION,"generated_utc":datetime.now(timezone.utc).isoformat(),
                 "computer":{"platform":platform.platform(),"python":sys.version},"advertisement":{k:v for k,v in sel.items() if k!="device"},
                 "connection":{"connected":False},"services":[],"standard_reads":{},"errors":[]}
            try:
                async with BleakClient(sel["device"],timeout=20.0) as client:
                    rep["connection"]["connected"]=client.is_connected
                    for svc in client.services:
                        sd={"uuid":svc.uuid,"description":svc.description,"characteristics":[]}
                        for ch in svc.characteristics:
                            cd={"uuid":ch.uuid,"handle":ch.handle,"description":ch.description,"properties":list(ch.properties),"descriptors":[]}
                            for de in ch.descriptors: cd["descriptors"].append({"uuid":de.uuid,"handle":de.handle,"description":de.description})
                            if "read" in ch.properties:
                                try:
                                    val=bytes(await client.read_gatt_char(ch))
                                    cd["read_hex"]=val.hex(); cd["read_text"]=val.decode("utf-8","replace").strip("\x00")
                                except Exception as e: cd["read_error"]=str(e)
                            sd["characteristics"].append(cd)
                        rep["services"].append(sd)
                    std={"manufacturer":"00002a29-0000-1000-8000-00805f9b34fb","model":"00002a24-0000-1000-8000-00805f9b34fb",
                         "serial":"00002a25-0000-1000-8000-00805f9b34fb","hardware":"00002a27-0000-1000-8000-00805f9b34fb",
                         "firmware":"00002a26-0000-1000-8000-00805f9b34fb","software":"00002a28-0000-1000-8000-00805f9b34fb"}
                    for key,u in std.items():
                        try:
                            val=bytes(await client.read_gatt_char(u)); rep["standard_reads"][key]={"hex":val.hex(),"text":val.decode("utf-8","replace").strip("\x00")}
                        except Exception as e: rep["standard_reads"][key]={"error":str(e)}
            except Exception as e: rep["errors"].append(str(e))
            return rep
        def done(rep,err):
            if err: messagebox.showerror("Diagnóstico",str(err)); self.status.set("Falló el diagnóstico."); return
            self.report=rep; txt=json.dumps(rep,ensure_ascii=False,indent=2)
            self.text.delete("1.0","end"); self.text.insert("end",txt); self.status.set("Diagnóstico finalizado. Guardalo y pasámelo.")
        self.run_async(work(),done)
    def save(self):
        if not self.report: messagebox.showinfo("Diagnóstico","Primero ejecutá DIAGNÓSTICO COMPLETO."); return
        p=filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("JSON","*.json"),("Texto","*.txt")],initialfile="reloj-diagnostico-v0.1.json")
        if p:
            with open(p,"w",encoding="utf-8") as f: json.dump(self.report,f,ensure_ascii=False,indent=2)
            self.status.set("Diagnóstico guardado.")
if __name__=="__main__":
    root=tk.Tk(); App(root); root.mainloop()
