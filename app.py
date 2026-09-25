import asyncio, json, platform, sys, threading, tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timezone
from bleak import BleakScanner, BleakClient
import urllib.request, tempfile, os, subprocess, time

APP_VERSION="0.8.0"
VERSION_URL="https://raw.githubusercontent.com/Yakoderaa/reloj/main/version.json"
OAD_SERVICE="f000ffc0-0451-4000-b000-000000000000"
CONTROL_SERVICE="0000e91a-0000-1000-8000-00805f9b34fb"
NOTIFY_UUIDS=["f000ffc2-0451-4000-b000-000000000000","0000b001-0000-1000-8000-00805f9b34fb"]

def ver_tuple(v):
    try:return tuple(int(x) for x in v.strip().lstrip("vV").split("."))
    except:return (0,)

class App:
    def __init__(self,root):
        self.root=root; root.title("Reloj Lab V0.8"); root.geometry("1000x700")
        self.devices=[]; self.selected=None; self.report=None; self.live_client=None; self.live_loop=None; self.closing=False; root.protocol("WM_DELETE_WINDOW",self.close_app); self.raw_hex=tk.StringVar(value="00ff000101150000010010000000010000000000")
        top=ttk.Frame(root,padding=12); top.pack(fill="x")
        ttk.Label(top,text="Reloj Lab",font=("Segoe UI",18,"bold")).pack(side="left")
        ttk.Label(top,text="V0.8 · localizador de acciones").pack(side="left",padx=12)
        ttk.Button(top,text="Buscar actualización",command=self.check_update).pack(side="right")
        ttk.Button(top,text="Buscar relojes",command=self.scan).pack(side="right",padx=8)
        body=ttk.Frame(root,padding=(12,0,12,12)); body.pack(fill="both",expand=True)
        self.tree=ttk.Treeview(body,columns=("name","address","rssi"),show="headings",height=8)
        for c,t,w in [("name","Nombre Bluetooth",300),("address","Dirección/ID",360),("rssi","RSSI",90)]:
            self.tree.heading(c,text=t); self.tree.column(c,width=w)
        self.tree.pack(fill="x"); self.tree.bind("<<TreeviewSelect>>",self.pick)
        a=ttk.Frame(body); a.pack(fill="x",pady=8)
        self.diag=ttk.Button(a,text="DIAGNÓSTICO COMPLETO",command=self.diagnose,state="disabled"); self.diag.pack(side="left")
        self.listen=ttk.Button(a,text="ESCUCHAR RELOJ 60 s",command=self.listen_notifications,state="disabled"); self.listen.pack(side="left",padx=8)
        self.explore=ttk.Button(a,text="CONECTAR Y VER TODO",command=self.explore_live,state="disabled"); self.explore.pack(side="left",padx=8)
        ttk.Button(a,text="CONTROL ACTIVO",command=self.open_control).pack(side="left",padx=8)
        ttk.Button(a,text="Guardar diagnóstico",command=self.save).pack(side="left")
        self.status=tk.StringVar(value="Listo. Buscá y seleccioná el reloj.")
        ttk.Label(a,textvariable=self.status).pack(side="right")
        self.text=tk.Text(body,wrap="none",font=("Consolas",9)); self.text.pack(fill="both",expand=True)
        self.text.insert("end","V0.3\n\nMejora de diagnóstico: reintentos y errores legibles.\nCaptura BLE pasiva.\nActualizador automático integrado.\n\nNo escribe al reloj ni inicia actualización de firmware.")
    def close_app(self):
        if self.closing:return
        self.closing=True
        self.status.set("Cerrando…")
        try:self.root.quit()
        except:pass
        try:self.root.destroy()
        except:pass

    def run_async(self,coro,done):
        def worker():
            try:r=asyncio.run(coro); self.root.after(0,lambda:done(r,None)) if not self.closing else None
            except Exception as e:self.root.after(0,lambda:done(None,e)) if not self.closing else None
        threading.Thread(target=worker,daemon=True).start()
    def run_thread(self,fn,done):
        def w():
            try:r=fn(); self.root.after(0,lambda:done(r,None))
            except Exception as e:self.root.after(0,lambda:done(None,e))
        threading.Thread(target=w,daemon=True).start()
    def scan(self):
        self.status.set("Buscando BLE durante 8 segundos…"); self.tree.delete(*self.tree.get_children()); self.devices=[]
        async def work():
            found=await BleakScanner.discover(timeout=8,return_adv=True); out=[]
            for _,(d,a) in found.items():
                out.append({"device":d,"name":a.local_name or d.name or "(sin nombre)","address":d.address,"rssi":a.rssi,
                "service_uuids":list(a.service_uuids or []),"manufacturer_data":{str(k):v.hex() for k,v in a.manufacturer_data.items()},
                "service_data":{str(k):v.hex() for k,v in a.service_data.items()},"tx_power":a.tx_power})
            return sorted(out,key=lambda x:x["rssi"] if x["rssi"] is not None else -999,reverse=True)
        def done(r,e):
            if e:self.status.set("Error de escaneo: "+repr(e)); messagebox.showerror("Bluetooth",repr(e)); return
            self.devices=r
            for i,x in enumerate(r):self.tree.insert("","end",iid=str(i),values=(x["name"],x["address"],x["rssi"]))
            self.status.set(f"{len(r)} dispositivos encontrados.")
        self.run_async(work(),done)
    def pick(self,_=None):
        s=self.tree.selection()
        if s:
            self.selected=self.devices[int(s[0])]; self.diag.config(state="normal"); self.listen.config(state="normal"); self.explore.config(state="normal")
            self.status.set("Seleccionado. Ejecutá DIAGNÓSTICO COMPLETO.")
    def base_report(self):
        return {"app":"Reloj Lab","app_version":APP_VERSION,"generated_utc":datetime.now(timezone.utc).isoformat(),
        "computer":{"platform":platform.platform(),"python":sys.version},"advertisement":{k:v for k,v in self.selected.items() if k!="device"},
        "connection":{"connected":False,"attempts":0},"services":[],"standard_reads":{},"passive_notifications":[],
        "safety":{"writes_performed":0,"firmware_actions":0},"errors":[]}
    async def connect_retry(self,attempts=3):
        last=None
        for i in range(attempts):
            c=BleakClient(self.selected["device"],timeout=20)
            try:
                await c.connect()
                if c.is_connected:return c,i+1
            except Exception as e:last=e
            try:await c.disconnect()
            except:pass
            await asyncio.sleep(1.5)
        raise RuntimeError("No se pudo conectar al reloj tras %d intentos. Detalle: %r"%(attempts,last))
    def diagnose(self):
        if not self.selected:return
        self.status.set("Conectando y leyendo GATT…")
        async def work():
            rep=self.base_report(); c=None
            try:
                c,n=await self.connect_retry(); rep["connection"]={"connected":True,"attempts":n}
                for svc in c.services:
                    sd={"uuid":svc.uuid,"description":svc.description,"characteristics":[]}
                    for ch in svc.characteristics:
                        cd={"uuid":ch.uuid,"handle":ch.handle,"description":ch.description,"properties":list(ch.properties),"descriptors":[]}
                        for de in ch.descriptors:cd["descriptors"].append({"uuid":de.uuid,"handle":de.handle,"description":de.description})
                        if "read" in ch.properties:
                            try:
                                v=bytes(await c.read_gatt_char(ch)); cd["read_hex"]=v.hex(); cd["read_text"]=v.decode("utf-8","replace").strip("\x00")
                            except Exception as ex:cd["read_error"]=repr(ex)
                        sd["characteristics"].append(cd)
                    rep["services"].append(sd)
                std={"manufacturer":"00002a29-0000-1000-8000-00805f9b34fb","model":"00002a24-0000-1000-8000-00805f9b34fb","serial":"00002a25-0000-1000-8000-00805f9b34fb","hardware":"00002a27-0000-1000-8000-00805f9b34fb","firmware":"00002a26-0000-1000-8000-00805f9b34fb","software":"00002a28-0000-1000-8000-00805f9b34fb"}
                for k,u in std.items():
                    try:
                        v=bytes(await c.read_gatt_char(u)); rep["standard_reads"][k]={"hex":v.hex(),"text":v.decode("utf-8","replace").strip("\x00")}
                    except Exception as ex:rep["standard_reads"][k]={"error":repr(ex)}
            except Exception as ex:rep["errors"].append(repr(ex))
            finally:
                if c:
                    try:await c.disconnect()
                    except:pass
            return rep
        def done(r,e):
            if e:messagebox.showerror("Diagnóstico",repr(e)); return
            self.report=r; self.show()
            self.status.set("Diagnóstico finalizado." if r["connection"]["connected"] else "No conectó. Guardá este diagnóstico igualmente.")
        self.run_async(work(),done)
    def explore_live(self):
        if not self.selected:return
        self.status.set("Conectando y abriendo explorador completo…")
        async def work():
            rep=self.base_report(); events=[]; c=None
            try:
                c,n=await self.connect_retry(); rep["connection"]={"connected":True,"attempts":n}
                self.root.after(0,lambda:self.status.set("Conectado · leyendo servicios GATT…"))
                notify=[]
                def cb(sender,data):
                    events.append({"utc":datetime.now(timezone.utc).isoformat(),"uuid":str(sender.uuid),"handle":sender.handle,"hex":bytes(data).hex(),"length":len(data)})
                services=list(c.services)
                total=sum(len(x.characteristics) for x in services); done_count=0
                for svc in services:
                    sd={"uuid":svc.uuid,"description":svc.description,"characteristics":[]}
                    for ch in svc.characteristics:
                        done_count+=1
                        self.root.after(0,lambda d=done_count,t=total:self.status.set(f"Conectado · explorando GATT {d}/{t}…"))
                        cd={"uuid":ch.uuid,"handle":ch.handle,"description":ch.description,"properties":list(ch.properties)}
                        if "read" in ch.properties:
                            try:
                                v=bytes(await asyncio.wait_for(c.read_gatt_char(ch),timeout=3)); cd["read_hex"]=v.hex(); cd["read_text"]=v.decode("utf-8","replace").strip("\\x00")
                            except Exception as ex:cd["read_error"]=repr(ex)
                        if "notify" in ch.properties or "indicate" in ch.properties:
                            try:await asyncio.wait_for(c.start_notify(ch,cb),timeout=4); notify.append(ch.uuid); cd["subscribed"]=True
                            except Exception as ex:cd["subscribe_error"]=repr(ex)
                        sd["characteristics"].append(cd)
                    rep["services"].append(sd)
                rep["live_subscriptions"]=notify
                self.root.after(0,lambda:self.status.set("Conectado. Explorando TODO durante 120 s: usá el reloj ahora."))
                await asyncio.sleep(120)
                rep["passive_notifications"]=events
                for u in notify:
                    try:await c.stop_notify(u)
                    except:pass
            except Exception as ex:rep["errors"].append(repr(ex))
            finally:
                if c:
                    try:await c.disconnect()
                    except:pass
            return rep
        def done(r,e):
            if e:messagebox.showerror("Explorador",repr(e)); return
            self.report=r; self.show(); self.status.set(f"Exploración completa: {len(r.get('passive_notifications',[]))} paquetes capturados. Guardá el diagnóstico.")
        self.run_async(work(),done)
    def listen_notifications(self):
        if not self.selected:return
        self.status.set("Escuchando 60 s. Usá funciones del reloj ahora…")
        async def work():
            events=[]; errs=[]; c=None
            try:
                c,n=await self.connect_retry()
                def cb(sender,data):events.append({"utc":datetime.now(timezone.utc).isoformat(),"uuid":str(sender.uuid),"handle":sender.handle,"hex":bytes(data).hex(),"length":len(data)})
                started=[]
                for u in NOTIFY_UUIDS:
                    try:await c.start_notify(u,cb); started.append(u)
                    except Exception as ex:errs.append(f"{u}: {repr(ex)}")
                await asyncio.sleep(60)
                for u in started:
                    try:await c.stop_notify(u)
                    except:pass
            except Exception as ex:errs.append(repr(ex))
            finally:
                if c:
                    try:await c.disconnect()
                    except:pass
            return events,errs
        def done(r,e):
            if e:messagebox.showerror("Escucha",repr(e)); return
            events,errs=r
            if self.report is None:self.report=self.base_report()
            self.report["passive_notifications"].extend(events); self.report["notification_errors"]=errs; self.show()
            self.status.set(f"Escucha finalizada: {len(events)} paquetes. Guardá el diagnóstico.")
        self.run_async(work(),done)
    def open_control(self):
        if not self.selected:
            messagebox.showinfo("Analizador","Primero buscá y seleccioná el reloj."); return
        w=tk.Toplevel(self.root); w.title("Reloj Lab · Analizador de protocolo"); w.geometry("900x620")
        ttk.Label(w,text="Analizador B002 → B001",font=("Segoe UI",14,"bold")).pack(anchor="w",padx=12,pady=(12,4))
        ttk.Label(w,text="Captura respuestas completas y compara bytes. El canal OTA FFC1 permanece separado.").pack(anchor="w",padx=12)
        row=ttk.Frame(w,padding=12); row.pack(fill="x")
        ttk.Entry(row,textvariable=self.raw_hex,width=70).pack(side="left",fill="x",expand=True)
        log=tk.Text(w,font=("Consolas",9),wrap="none"); log.pack(fill="both",expand=True,padx=12,pady=(0,12))
        def append(x): log.insert("end",x+"\n"); log.see("end")
        async def exchange(payloads,wait=.8):
            c,n=await self.connect_retry(); out=[]
            def cb(sender,d):out.append({"kind":"RX","hex":bytes(d).hex(),"t":time.time()})
            try:
                try:await asyncio.wait_for(c.start_notify("0000b001-0000-1000-8000-00805f9b34fb",cb),timeout=4)
                except Exception as ex:out.append({"kind":"NOTIFY_ERROR","hex":repr(ex),"t":time.time()})
                await asyncio.sleep(.3)
                for label,data in payloads:
                    out.append({"kind":"TX","label":label,"hex":data.hex(),"t":time.time()})
                    await c.write_gatt_char("0000b002-0000-1000-8000-00805f9b34fb",data,response=False)
                    await asyncio.sleep(wait)
                await asyncio.sleep(1.5)
            finally:
                try:await c.disconnect()
                except:pass
            return out
        def render(rows):
            last_tx=None
            for x in rows:
                if x["kind"]=="TX":
                    last_tx=x; append("TX "+x.get("label","")+": "+x["hex"])
                elif x["kind"]=="RX":
                    append("RX"+((" ← "+last_tx.get("label","")) if last_tx else "")+": "+x["hex"])
                else:append(x["kind"]+": "+x["hex"])
            append("PRUEBA FINALIZADA")
        def send_raw():
            try:data=bytes.fromhex(self.raw_hex.get().replace(" ","").strip())
            except Exception as e:messagebox.showerror("HEX","HEX inválido: "+repr(e)); return
            self.run_async(exchange([("manual",data)],1.2),lambda r,e: append("ERROR: "+repr(e)) if e else render(r))
        def differential():
            base=bytearray.fromhex("00ff000101150000010010000000010000000000")
            tests=[]
            for idx in [2,3,4,5,8,9,10,14,15,16]:
                for val in [0x00,0x01,0x02,0x10,0xff]:
                    p=bytearray(base); p[idx]=val
                    tests.append((f"byte[{idx}]={val:02x}",bytes(p)))
            append("MAPEO DIFERENCIAL: 50 paquetes controlados. Mirá el reloj y anotá cualquier cambio.")
            self.run_async(exchange(tests,.35),lambda r,e: append("ERROR: "+repr(e)) if e else render(r))
        def capture():
            append("CAPTURA 90 s: usá funciones del reloj; se registrará todo B001 espontáneo.")
            async def work():
                c,n=await self.connect_retry(); out=[]
                def cb(sender,d):out.append({"kind":"RX","hex":bytes(d).hex(),"t":time.time()})
                try:
                    await asyncio.wait_for(c.start_notify("0000b001-0000-1000-8000-00805f9b34fb",cb),timeout=4)
                    for left in range(90,0,-1):
                        if left%10==0:self.root.after(0,lambda z=left:append(f"... faltan {z}s · RX={len(out)}"))
                        await asyncio.sleep(1)
                finally:
                    try:await c.disconnect()
                    except:pass
                return out
            self.run_async(work(),lambda r,e: append("ERROR: "+repr(e)) if e else render(r))
        ttk.Button(row,text="ENVIAR HEX",command=send_raw).pack(side="left",padx=4)
        ttk.Button(row,text="MAPEO DIFERENCIAL",command=differential).pack(side="left",padx=4)
        def deep_probe():
            append("SONDEO PROFUNDO: prueba el campo de comando completo y variantes del tipo de frame.")
            base=bytearray.fromhex("00ff000101150000010010000000010000000000")
            tests=[]
            for val in range(256):
                p=bytearray(base); p[4]=val; tests.append((f"cmd={val:02x}",bytes(p)))
            for val in range(64):
                p=bytearray(base); p[5]=val; tests.append((f"type={val:02x}",bytes(p)))
            async def work():
                c,n=await self.connect_retry(); out=[]
                def cb(sender,d):out.append({"kind":"RX","hex":bytes(d).hex(),"t":time.time()})
                try:
                    try:await asyncio.wait_for(c.start_notify("0000b001-0000-1000-8000-00805f9b34fb",cb),timeout=4)
                    except Exception as ex:out.append({"kind":"NOTIFY_ERROR","hex":repr(ex),"t":time.time()})
                    for i,(label,data) in enumerate(tests,1):
                        if not c.is_connected:out.append({"kind":"DISCONNECT","hex":label,"t":time.time()}); break
                        out.append({"kind":"TX","label":label,"hex":data.hex(),"t":time.time()})
                        await asyncio.wait_for(c.write_gatt_char("0000b002-0000-1000-8000-00805f9b34fb",data,response=False),timeout=2)
                        if i%32==0:self.root.after(0,lambda i=i,t=len(tests):append(f"... {i}/{t}"))
                        await asyncio.sleep(.12)
                    await asyncio.sleep(1)
                finally:
                    try:await c.disconnect()
                    except:pass
                return out
            def done(r,e):
                if e:append("SONDEO ERROR: "+repr(e)); return
                unique=[]; last=None; tx=0
                for x in r:
                    if x["kind"]=="TX":tx+=1
                    elif x["kind"]=="RX" and x["hex"]!=last:
                        last=x["hex"]
                        if x["hex"] not in unique:unique.append(x["hex"])
                    elif x["kind"] not in ("TX","RX"):append(x["kind"]+": "+x["hex"])
                append(f"SONDEO PROFUNDO FINALIZADO · TX={tx} · RX diferentes={len(unique)}")
                for z in unique:append("RX ÚNICA: "+z)
            self.run_async(work(),done)
        ttk.Button(row,text="SONDEO PROFUNDO",command=deep_probe).pack(side="left",padx=4)
        def action_locator():
            append("LOCALIZADOR: 256 comandos, 1.0 s por comando. La pantalla muestra exactamente cuál se está ejecutando.")
            base=bytearray.fromhex("00ff000101150000010010000000010000000000")
            async def work():
                c,n=await self.connect_retry(); out=[]; current={"label":"—"}
                def cb(sender,d):out.append({"kind":"RX","label":current["label"],"hex":bytes(d).hex(),"t":time.time()})
                try:
                    await asyncio.wait_for(c.start_notify("0000b001-0000-1000-8000-00805f9b34fb",cb),timeout=4)
                    await asyncio.sleep(.3)
                    for val in range(256):
                        p=bytearray(base); p[4]=val; label=f"CMD {val:02X} ({val}/255)"; current["label"]=label
                        self.root.after(0,lambda z=label:self.status.set("PROBANDO "+z+" · mirá el reloj"))
                        out.append({"kind":"TX","label":label,"hex":bytes(p).hex(),"t":time.time()})
                        await c.write_gatt_char("0000b002-0000-1000-8000-00805f9b34fb",bytes(p),response=False)
                        await asyncio.sleep(1.0)
                    await asyncio.sleep(1)
                finally:
                    try:await c.disconnect()
                    except:pass
                return out
            def done(r,e):
                if e:append("LOCALIZADOR ERROR: "+repr(e)); return
                append("=== RESULTADO LOCALIZADOR ===")
                for x in r:
                    if x["kind"]=="RX":append(x["label"]+" → RX "+x["hex"])
                append("LOCALIZADOR FINALIZADO")
                self.status.set("Localizador finalizado.")
            self.run_async(work(),done)
        ttk.Button(row,text="LOCALIZAR ACCIONES",command=action_locator).pack(side="left",padx=4)
        ttk.Button(row,text="CAPTURAR 90 s",command=capture).pack(side="left",padx=4)
        append("Listo. El sondeo 00–0F anterior recibió ACKs pero no produjo acción visible; ahora se mapean campos del frame y tráfico espontáneo.")
    def check_update(self):
        self.status.set("Buscando actualización…")
        def work():
            req=urllib.request.Request(VERSION_URL,headers={"User-Agent":"RelojLab/"+APP_VERSION})
            with urllib.request.urlopen(req,timeout=15) as r:meta=json.loads(r.read().decode("utf-8"))
            if ver_tuple(meta["version"])<=ver_tuple(APP_VERSION):return ("current",meta)
            td=tempfile.mkdtemp(prefix="RelojLabUpdate-")
            newexe=os.path.join(td,"RelojLab-new.exe")
            req=urllib.request.Request(meta["exe_url"],headers={"User-Agent":"RelojLab/"+APP_VERSION})
            with urllib.request.urlopen(req,timeout=120) as r,open(newexe,"wb") as out:
                while True:
                    b=r.read(1024*1024)
                    if not b:break
                    out.write(b)
            if os.path.getsize(newexe)<1000000:raise RuntimeError("La descarga de la actualización no parece ser un EXE válido.")
            current=os.path.abspath(sys.executable if getattr(sys,"frozen",False) else sys.argv[0])
            updater=os.path.join(td,"RelojLab-Updater.cmd")
            log=os.path.join(os.path.dirname(current),"RelojLab-update.log")
            script='''@echo off
setlocal
echo Actualizacion iniciada > "'''+log+'''"
timeout /t 3 /nobreak >nul
copy /y "'''+newexe+'''" "'''+current+'''" >> "'''+log+'''" 2>&1
if errorlevel 1 (
  echo Fallo reemplazo >> "'''+log+'''"
  start "" "'''+newexe+'''"
  exit /b 1
)
start "" "'''+current+'''"
echo OK >> "'''+log+'''"
del "%~f0"
'''
            with open(updater,"w",encoding="utf-8") as out:out.write(script)
            subprocess.Popen(["cmd.exe","/c","start","",updater],cwd=td,creationflags=0x08000000)
            return ("updating",meta)
        def done(r,e):
            if e:
                self.status.set("Error al actualizar.")
                messagebox.showerror("Actualización","No se pudo completar la actualización.\n\n"+repr(e)+"\n\nPodés instalar el EXE manualmente.")
                return
            state,meta=r
            if state=="current":
                self.status.set("Ya tenés la última versión.")
                messagebox.showinfo("Actualización","Reloj Lab "+APP_VERSION+" ya está actualizado.")
            else:
                self.status.set("Actualización descargada. Cerrando para instalar…")
                self.root.after(800,self.root.destroy)
        self.run_thread(work,done)
    def show(self):
        self.text.delete("1.0","end"); self.text.insert("end",json.dumps(self.report,ensure_ascii=False,indent=2))
    def save(self):
        if not self.report:messagebox.showinfo("Diagnóstico","Primero ejecutá el diagnóstico."); return
        p=filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("JSON","*.json")],initialfile="reloj-diagnostico-v0.3.json")
        if p:
            with open(p,"w",encoding="utf-8") as f:json.dump(self.report,f,ensure_ascii=False,indent=2)
            self.status.set("Diagnóstico guardado.")
if __name__=="__main__":
    root=tk.Tk(); App(root); root.mainloop()
