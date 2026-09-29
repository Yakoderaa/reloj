import asyncio, json, platform, sys, threading, tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timezone
from bleak import BleakScanner, BleakClient
import urllib.request, tempfile, os, subprocess, time, hashlib, queue, math

APP_VERSION="1.22.0"
VERSION_URL="https://raw.githubusercontent.com/Yakoderaa/reloj/main/version.json"
OAD_SERVICE="f000ffc0-0451-4000-b000-000000000000"
CONTROL_SERVICE="0000e91a-0000-1000-8000-00805f9b34fb"
NOTIFY_UUIDS=["f000ffc2-0451-4000-b000-000000000000","0000b001-0000-1000-8000-00805f9b34fb"]

def ver_tuple(v):
    try:return tuple(int(x) for x in v.strip().lstrip("vV").split("."))
    except:return (0,)

class App:
    def __init__(self,root):
        self.root=root; root.title("Reloj Lab V1.22"); root.geometry("1000x700")
        self.ui_queue=queue.Queue()
        self.ble_loop=asyncio.new_event_loop()
        self.ble_busy=False
        def bluetooth_worker():
            asyncio.set_event_loop(self.ble_loop)
            if sys.platform == "win32":
                from bleak.backends.winrt.util import uninitialize_sta
                uninitialize_sta()
            self.ble_loop.run_forever()
        threading.Thread(target=bluetooth_worker,daemon=True).start()
        self.root.after(50,self.drain_ui)
        self.state_path=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab","window-state.json")
        self.window_state=self.load_window_state()
        if self.window_state.get("main_geometry"):
            try: root.geometry(self.window_state["main_geometry"])
            except: pass
        self.devices=[]; self.selected=None; self.report=None; self.live_client=None; self.live_loop=None; self.closing=False; root.protocol("WM_DELETE_WINDOW",self.close_app); self.raw_hex=tk.StringVar(value="00ff000101150000010010000000010000000000")
        top=ttk.Frame(root,padding=12); top.pack(fill="x")
        ttk.Label(top,text="Reloj Lab",font=("Segoe UI",18,"bold")).pack(side="left")
        ttk.Label(top,text="V1.22 · esfera MARKET propia").pack(side="left",padx=12)
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
    def load_window_state(self):
        try:
            with open(self.state_path,"r",encoding="utf-8") as fh:return json.load(fh)
        except:return {}
    def save_window_state(self,control_geometry=None):
        try:
            os.makedirs(os.path.dirname(self.state_path),exist_ok=True)
            self.window_state["main_geometry"]=self.root.geometry()
            if control_geometry:self.window_state["control_geometry"]=control_geometry
            with open(self.state_path,"w",encoding="utf-8") as fh:json.dump(self.window_state,fh)
        except:pass

    def close_app(self):
        if self.closing:return
        try:self.save_window_state()
        except:pass
        self.closing=True
        self.status.set("Cerrando…")
        try:self.root.quit()
        except:pass
        try:self.root.destroy()
        except:pass

    def drain_ui(self):
        if self.closing:return
        while True:
            try:callback=self.ui_queue.get_nowait()
            except queue.Empty:break
            try:callback()
            except tk.TclError:pass
        self.root.after(50,self.drain_ui)

    def run_async(self,coro,done):
        if self.ble_busy:
            coro.close()
            done(None,RuntimeError("Hay una operación Bluetooth en curso. Esperá a que termine."))
            return
        self.ble_busy=True
        self.tree.state(["disabled"])
        future=asyncio.run_coroutine_threadsafe(coro,self.ble_loop)
        def finished(f):
            try:result=f.result(); error=None
            except BaseException as ex:result=None; error=ex
            def deliver():
                self.ble_busy=False
                self.tree.state(["!disabled"])
                done(result,error)
            self.ui_queue.put(deliver)
        future.add_done_callback(finished)

    def run_thread(self,fn,done):
        def w():
            try:r=fn(); self.root.after(0,lambda:done(r,None))
            except Exception as e:self.root.after(0,lambda error=e:done(None,error))
        threading.Thread(target=w,daemon=True).start()
    def scan(self):
        if self.ble_busy:
            self.status.set("Esperá a que termine la operación Bluetooth actual."); return
        self.selected=None
        for button in (self.diag,self.listen,self.explore):button.config(state="disabled")
        self.status.set("Buscando el reloj UtraWatch durante 10 segundos…")
        self.tree.delete(*self.tree.get_children()); self.devices=[]

        def watch_score(x):
            services={str(v).lower() for v in (x.get("service_uuids") or [])}
            service_data={str(k).lower():v for k,v in (x.get("service_data") or {}).items()}
            name=(x.get("name") or "").strip().lower()
            manufacturer=x.get("manufacturer_data") or {}
            score=0
            if "0000e91a-0000-1000-8000-00805f9b34fb" in services:score+=120
            if "00003802-0000-1000-8000-00805f9b34fb" in services:score+=110
            if any("3802" in k for k in service_data):score+=110
            if name=="apple watch ultra":score+=60
            if str(manufacturer.get("255","")).lower()=="00a6":score+=40
            return score

        async def work():
            found=await BleakScanner.discover(timeout=10,return_adv=True); out=[]
            for _,(d,a) in found.items():
                row={"device":d,"name":a.local_name or d.name or "(sin nombre)","address":d.address,"rssi":a.rssi,
                     "service_uuids":list(a.service_uuids or []),
                     "manufacturer_data":{str(k):v.hex() for k,v in a.manufacturer_data.items()},
                     "service_data":{str(k):v.hex() for k,v in a.service_data.items()},
                     "tx_power":a.tx_power}
                row["_watch_score"]=watch_score(row)
                out.append(row)
            return sorted(out,key=lambda x:(x.get("_watch_score",0),x["rssi"] if x["rssi"] is not None else -999),reverse=True)

        def done(r,e):
            if e:
                self.status.set("Error de escaneo: "+repr(e)); messagebox.showerror("Bluetooth",repr(e)); return
            self.devices=r
            for i,x in enumerate(r):
                label=x["name"]
                if x.get("_watch_score",0)>0:label="✓ RELOJ · "+label
                self.tree.insert("","end",iid=str(i),values=(label,x["address"],x["rssi"]))
            candidates=[(i,x) for i,x in enumerate(r) if x.get("_watch_score",0)>0]
            if candidates:
                i,x=candidates[0]
                self.selected=x
                self.tree.selection_set(str(i)); self.tree.focus(str(i)); self.tree.see(str(i))
                for button in (self.diag,self.listen,self.explore):button.config(state="normal")
                self.status.set("Reloj UtraWatch identificado automáticamente: "+x["name"]+" · "+x["address"])
            else:
                self.status.set(str(len(r))+" BLE encontrados, pero ninguno coincide con la firma UtraWatch.")
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
    async def connect_retry(self,attempts=2,progress=None,*,services=None,pair=False):
        from connection import connect_watch
        return await connect_watch(self,attempts,progress,services=services,pair=pair)

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
    async def inspect_gatt_snapshot(self,emit):
        address=(self.selected or {}).get("address")
        if not address: raise RuntimeError("Seleccioná el reloj primero.")
        client=None
        snapshot={"services":[],"errors":[],"connected":False}
        try:
            target=await asyncio.wait_for(BleakScanner.find_device_by_address(address,timeout=8),timeout=10)
            if target is None: raise RuntimeError("El reloj seleccionado no está visible.")
            client=BleakClient(target,timeout=15,winrt={"use_cached_services":False})
            await asyncio.wait_for(client.connect(),timeout=18)
            if not client.is_connected: raise RuntimeError("GATT no conectado")
            snapshot["connected"]=True
            present=set()
            for svc in client.services:
                entry={"uuid":svc.uuid,"characteristics":[]}
                emit("SERVICIO "+svc.uuid)
                for ch in svc.characteristics:
                    present.add(ch.uuid.lower())
                    row={"uuid":ch.uuid,"handle":ch.handle,"properties":list(ch.properties)}
                    entry["characteristics"].append(row)
                    emit("  CARACTERÍSTICA "+str(row))
                snapshot["services"].append(entry)
            expected={"B001":"0000b001-0000-1000-8000-00805f9b34fb","B002":"0000b002-0000-1000-8000-00805f9b34fb","FFC1":"f000ffc1-0451-4000-b000-000000000000","FFC2":"f000ffc2-0451-4000-b000-000000000000"}
            snapshot["present"]={name:uuid in present for name,uuid in expected.items()}
            emit("PRESENCIA "+str(snapshot["present"]))
            if not snapshot["present"]["B001"]:
                emit("B001 AUSENTE en esta enumeración. Causa pendiente; no confirma modo OTA.")
        except asyncio.CancelledError: raise
        except Exception as ex:
            snapshot["errors"].append(type(ex).__name__+": "+str(ex))
            emit("ERROR DE INSPECCIÓN · "+snapshot["errors"][-1])
        finally:
            if client is not None:
                try: await asyncio.wait_for(client.disconnect(),timeout=4)
                except Exception as ex:
                    snapshot["errors"].append("Cierre: "+repr(ex))
                    emit("ERROR DE CIERRE · "+repr(ex))
        return snapshot

    def open_control(self):
        if not self.selected:
            messagebox.showinfo("Analizador","Primero buscá y seleccioná el reloj."); return
        w=tk.Toplevel(self.root); w.title("Reloj Lab · Analizador de protocolo"); w.geometry(self.window_state.get("control_geometry","900x620"))
        def close_control():
            try:self.save_window_state(w.geometry())
            except:pass
            w.destroy()
        w.protocol("WM_DELETE_WINDOW",close_control)
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
        def copy_control_diagnostic():
            text=log.get("1.0","end-1c")
            if not text.strip():
                self.status.set("No hay diagnóstico para copiar todavía.")
                return
            try:
                w.clipboard_clear()
                w.clipboard_append(text)
                w.update_idletasks()
                self.status.set("Diagnóstico copiado al portapapeles.")
            except Exception as ex:
                messagebox.showerror("Copiar diagnóstico",repr(ex))
        primary_test=ttk.Button(row,text="INSTALAR ESFERA SINCRONIZADA V1.22")
        primary_test.pack(side="left",padx=4)
        ttk.Button(row,text="COPIAR DIAGNÓSTICO",command=copy_control_diagnostic).pack(side="left",padx=4)
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
            append("LOCALIZADOR RÁPIDO: 256 comandos, 0.25 s por comando. Registra el comando exacto de cada respuesta.")
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
                        await asyncio.sleep(.25)
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
        def ota_inspect():
            append("OTA/BOOT INSPECTOR: consultando FFC1/FFC2 sin transferir firmware.")
            async def work():
                c,n=await self.connect_retry(); out=[]
                try:
                    for u in ["f000ffc1-0451-4000-b000-000000000000","f000ffc2-0451-4000-b000-000000000000"]:
                        try:
                            ch=c.services.get_characteristic(u)
                            out.append(u+" props="+str(ch.properties if ch else None))
                            if ch and "read" in ch.properties:
                                d=await c.read_gatt_char(u); out.append(u+" read="+bytes(d).hex())
                        except Exception as ex:out.append(u+" error="+repr(ex))
                finally:
                    try:await c.disconnect()
                    except:pass
                return out
            self.run_async(work(),lambda r,e:append("OTA ERROR: "+repr(e)) if e else [append(x) for x in r]+[append("OTA INSPECCIÓN FINALIZADA")])
        ttk.Button(row,text="INSPECCIONAR OTA/BOOT",command=ota_inspect).pack(side="left",padx=4)
        def dual_capture():
            append("CAPTURA DUAL V0.11: diagnóstico por etapas, timeout y fallback automático.")
            async def work():
                out=[]; c=None
                def emit(msg):
                    out.append((time.time(),"SYS",msg))
                    self.root.after(0,lambda m=msg:(append(m),self.status.set(m)))
                def mk(tag):
                    def cb(sender,d):out.append((time.time(),tag,bytes(d).hex()))
                    return cb
                try:
                    emit("ETAPA 1/4 · Conectando…")
                    c,n=await asyncio.wait_for(self.connect_retry(),timeout=20)
                    emit("ETAPA 1/4 · Conectado.")
                    emit("ETAPA 2/4 · Suscribiendo B001…")
                    try:
                        await asyncio.wait_for(c.start_notify("0000b001-0000-1000-8000-00805f9b34fb",mk("B001")),timeout=5)
                        emit("ETAPA 2/4 · B001 OK.")
                    except Exception as ex:emit("ETAPA 2/4 · B001 FALLÓ: "+repr(ex))
                    emit("ETAPA 3/4 · Suscribiendo FFC2…")
                    try:
                        await asyncio.wait_for(c.start_notify("f000ffc2-0451-4000-b000-000000000000",mk("FFC2")),timeout=5)
                        emit("ETAPA 3/4 · FFC2 OK.")
                    except Exception as ex:emit("ETAPA 3/4 · FFC2 sin respuesta; sigo sólo con B001: "+repr(ex))
                    emit("ETAPA 4/4 · Capturando 60 s…")
                    for elapsed in range(60):
                        if not c.is_connected:
                            emit("Conexión perdida en segundo "+str(elapsed)); break
                        if elapsed%5==0:
                            events=sum(1 for x in out if x[1] in ("B001","FFC2"))
                            self.root.after(0,lambda e=elapsed,n=events:self.status.set(f"CAPTURA · {60-e}s restantes · eventos={n}"))
                        await asyncio.sleep(1)
                    emit("CAPTURA DUAL FINALIZADA.")
                except asyncio.TimeoutError:emit("TIMEOUT GLOBAL: la conexión no respondió a tiempo.")
                except Exception as ex:emit("ERROR CAPTURA: "+repr(ex))
                finally:
                    if c:
                        try:await asyncio.wait_for(c.disconnect(),timeout=4)
                        except:pass
                return out
            def done(r,e):
                if e:append("WATCHDOG: "+repr(e)); self.status.set("Captura detenida por watchdog."); return
                append("=== RESULTADO V0.11 ===")
                data=[x for x in r if x[1] in ("B001","FFC2")]
                if data:
                    t0=data[0][0]
                    for t,tag,h in data:append(f"+{t-t0:06.2f}s {tag} {h}")
                else:append("Sin paquetes espontáneos B001/FFC2 durante la ventana.")
                append("RESULTADO V0.11 FINALIZADO")
                self.status.set("Captura finalizada.")
            self.run_async(asyncio.wait_for(work(),timeout=100),done)
        ttk.Button(row,text="CAPTURA DUAL ROBUSTA",command=dual_capture).pack(side="left",padx=4)
        def firmware_preflight():
            if self.ble_busy:
                append("Ya hay una operación Bluetooth en curso."); return
            append("PREFLIGHT V"+APP_VERSION+": conexión directa e identificación. No instala otro sistema.")
            rep=self.base_report()
            rep["firmware_access"]={"bootloader_confirmed":False,"compatible_image":False,
                "ready_to_flash":False,"reason":"Faltan hardware confirmado, firmware compatible y protocolo de instalación verificado."}
            rep["preflight_log"]=[]
            async def work():
                c=None
                def emit(m):
                    rep["preflight_log"].append(m)
                    self.ui_queue.put(lambda x=m:(append(x),self.status.set(x)))
                async def heartbeat():
                    started=time.monotonic()
                    while True:
                        await asyncio.sleep(5)
                        emit(f"En curso: {int(time.monotonic()-started)} s")
                pulse=asyncio.create_task(heartbeat())
                try:
                    emit("1/4 · Probando cuatro rutas de conexión Windows/BLE…")
                    c,n=await self.connect_retry(8,emit)
                    rep["connection"]={"connected":True,"attempts":n}
                    emit("2/4 · Leyendo identidad del firmware…")
                    for key,short in [("manufacturer","2a29"),("model","2a24"),("hardware","2a27"),("firmware","2a26"),("software","2a28")]:
                        uuid=f"0000{short}-0000-1000-8000-00805f9b34fb"
                        ch=c.services.get_characteristic(uuid)
                        if ch and "read" in ch.properties:
                            try:
                                data=bytes(await asyncio.wait_for(c.read_gatt_char(ch),timeout=4))
                                rep["standard_reads"][key]={"hex":data.hex(),"text":data.decode("utf-8",errors="replace")}
                                emit(key+": "+rep["standard_reads"][key]["text"])
                            except Exception as ex:rep["errors"].append(key+": "+repr(ex))
                    emit("3/4 · Inventario GATT y canal candidato a OTA…")
                    for svc in c.services:
                        rep["services"].append({"uuid":svc.uuid,"characteristics":[{"uuid":ch.uuid,"properties":list(ch.properties)} for ch in svc.characteristics]})
                    for uuid in NOTIFY_UUIDS:
                        ch=c.services.get_characteristic(uuid)
                        if not ch or "notify" not in ch.properties:continue
                        try:
                            def notification(sender,data):
                                rep["passive_notifications"].append({"uuid":str(sender.uuid),"hex":bytes(data).hex()})
                            await asyncio.wait_for(c.start_notify(ch,notification),timeout=5)
                            emit("Notificaciones habilitadas: "+uuid)
                        except Exception as ex:rep["errors"].append(uuid+": "+repr(ex))
                    await asyncio.sleep(4)
                    emit("4/4 · Inventario terminado. Acceso al bootloader NO confirmado; firmware alternativo NO disponible.")
                except Exception as ex:
                    rep["errors"].append(repr(ex)); emit("No se completó el preflight: "+repr(ex))
                finally:
                    pulse.cancel()
                    await asyncio.gather(pulse,return_exceptions=True)
                    if c:
                        try:await asyncio.wait_for(c.disconnect(),timeout=4)
                        except Exception as ex:rep["errors"].append("Desconexión: "+repr(ex))
                return rep
            def done(result,error):
                if error:rep["errors"].append(repr(error))
                self.report=result or rep
                self.report["connection"]=dict(getattr(self,"connection_state",self.report["connection"]))
                self.show()
                append("Informe disponible en Guardar diagnóstico.")
                self.status.set("Preflight finalizado con errores." if self.report["errors"] else "Preflight finalizado. Firmware aún no habilitado.")
            self.run_async(work(),done)
        ttk.Button(row,text="PREFLIGHT FIRMWARE",command=firmware_preflight).pack(side="left",padx=4)
        def ota_fingerprint():
            append("HUELLA OTA V0.16: inventario GATT completo + escucha FFC2. No escribe FFC1.")
            async def work():
                c=None; rows=[]
                def emit(m):
                    rows.append(m); self.root.after(0,lambda x=m:(append(x),self.status.set(x)))
                try:
                    emit("1/5 · Abriendo GATT con la ruta validada…")
                    c,n=await self.connect_retry(4,emit)
                    emit(f"2/5 · GATT abierto en intento {n}. Enumerando servicios/características…")
                    for svc in c.services:
                        emit("SERVICE "+str(svc.uuid))
                        for ch in svc.characteristics:
                            emit("  CHAR "+str(ch.uuid)+" props="+",".join(ch.properties))
                            for desc in ch.descriptors:
                                emit("    DESC "+str(desc.uuid)+" handle="+str(desc.handle))
                    emit("3/5 · Midiendo MTU negociado…")
                    emit("MTU="+str(getattr(c,"mtu_size","desconocido")))
                    events=[]
                    emit("4/5 · Suscribiendo FFC2 durante 12 s…")
                    try:
                        def rx(sender,data):
                            h=bytes(data).hex(); events.append(h)
                            self.root.after(0,lambda x=h:append("FFC2 RX "+x))
                        await asyncio.wait_for(c.start_notify("f000ffc2-0451-4000-b000-000000000000",rx),timeout=7)
                        for sec in range(12):
                            self.root.after(0,lambda n=12-sec:self.status.set(f"HUELLA OTA · escucha FFC2 · {n}s"))
                            await asyncio.sleep(1)
                        try:await c.stop_notify("f000ffc2-0451-4000-b000-000000000000")
                        except:pass
                    except Exception as ex:emit("FFC2 LISTEN ERROR: "+repr(ex))
                    emit("5/5 · HUELLA OTA COMPLETA · paquetes FFC2="+str(len(events)))
                    if not events:emit("FFC2 quedó silencioso sin una orden previa: necesitamos identificar el handshake antes de escribir.")
                except Exception as ex:emit("HUELLA OTA ERROR: "+repr(ex))
                finally:
                    if c:
                        try:await asyncio.wait_for(c.disconnect(),timeout=5)
                        except:pass
                return rows
            self.run_async(asyncio.wait_for(work(),timeout=190),lambda r,e:append("HUELLA OTA WATCHDOG: "+repr(e)) if e else append("HUELLA OTA V0.16 FINALIZADA"))
        ttk.Button(row,text="HUELLA OTA PROFUNDA",command=ota_fingerprint).pack(side="left",padx=4)
        def ota_lab(pair=False):
            if self.ble_busy:
                append("V1.22 NO INICIADA · Bluetooth ocupado.")
                return
            append("V1.22 · GATT DIRECTO E91A · consulta sólo el servicio de la esfera durante la instalación. Conserva validación ATT, dos intentos y diagnóstico por intento; no reinicia Bluetooth.")
            rep=self.base_report()
            rep["windows_binding_repair"]=dict(getattr(self,"binding_repair",{}))
            rep["single_face_install"]={
                "phase":"prepare","blocks":[],"payload_bytes_written":0,"ack_count":0,
                "firmware_actions":0,"factory_faces_deleted":False
            }
            t0=time.monotonic()

            def emit(msg):
                line=f"+{time.monotonic()-t0:06.2f}s · {msg}"
                self.ui_queue.put(lambda x=line:(append(x),self.status.set(x)))

            def crc16_8005(data):
                crc=0
                for x in data:
                    crc ^= (x&255)<<8
                    for _ in range(8):
                        crc=((crc<<1)^0x8005)&0xffff if (crc&0x8000) else (crc<<1)&0xffff
                return crc

            def oem_dial_compress(raw):
                # Exact GZipUtils.zlib(..., false) parameters from the UtraWatch SDK:
                # deflater.init(level=6, windowBits=9, memLevel=3, W_ZLIB).
                import zlib
                co=zlib.compressobj(level=6,method=zlib.DEFLATED,wbits=9,memLevel=3)
                comp=co.compress(raw)+co.flush()
                hdr=bytearray(20)
                total=len(comp)+20
                hdr[0:4]=total.to_bytes(4,"little")
                hdr[4:6]=crc16_8005(comp).to_bytes(2,"little")
                hdr[6:8]=bytes([0xFE,0xFE])
                hdr[8]=1
                if len(raw)>26 and raw[9]==255:
                    hdr[9]=raw[25]
                    hdr[10]=raw[26]
                elif len(raw)>9:
                    hdr[9]=raw[9]
                    hdr[10]=0
                hdr[11]=0
                return bytes(hdr)+comp,comp

            def build_dynamic_reference_v121():
                import base64,zlib
                root=getattr(sys,"_MEIPASS",os.path.dirname(os.path.abspath(__file__)))
                b64_path=os.path.join(root,"assets","target_face_v121.b64")
                meta_path=os.path.join(root,"assets","target_face_v121.json")
                if not os.path.exists(b64_path):
                    raise RuntimeError("Falta la esfera MARKET V1.22 en el paquete")
                packed=open(b64_path,"r",encoding="ascii").read().strip()
                raw=zlib.decompress(base64.b64decode(packed))
                if len(raw)<0x800 or int.from_bytes(raw[:4],"little")!=len(raw)-16:
                    raise RuntimeError("Esfera MARKET V1.22 inválida")
                bin_id_hex=raw[4:6].hex()
                if bin_id_hex!="4cc6":
                    raise RuntimeError("BinID MARKET V1.22 inesperado: "+bin_id_hex)
                def u16(off): return int.from_bytes(raw[off:off+2],"little")
                def find_field(field):
                    for off in range(0x10,0x800-28):
                        if u16(off)==0x0164 and u16(off+8)==0x1202 and u16(off+10)==field:
                            return off
                    return None
                fields={name:find_field(field) for field,name in (
                    (0x8001,"hour"),(0x8002,"minute"),(0x8009,"steps"),
                    (0x800E,"heart_rate"),(0x8013,"battery"))}
                if any(v is None for v in fields.values()):
                    raise RuntimeError("MARKET V1.22 no contiene todos los campos vivos requeridos: "+repr(fields))
                meta={}
                if os.path.exists(meta_path):
                    try:
                        with open(meta_path,"r",encoding="utf-8") as fh: meta=json.load(fh)
                    except Exception: meta={}
                folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),
                                    "RelojLab","wf-analysis-v121")
                os.makedirs(folder,exist_ok=True)
                path=os.path.join(folder,"approved-market-v121.bin")
                with open(path,"wb") as fh:fh.write(raw)
                return path,raw,240,296,fields,bin_id_hex,meta

            def build(dev_type,n_seq,op,payload=b"",send_type=1):
                # CEProtocolB wire header: byte1=device type, byte3=N sequence.
                # V0.82 incorrectly incremented byte1 and left byte3 at zero.
                payload=bytes(payload);n=len(payload)
                if n>4855:raise RuntimeError("payload WTWD demasiado grande")
                h=bytearray(20)
                if n<=10:
                    h[1]=dev_type&255;h[3]=n_seq&255;h[4]=send_type;h[5]=op
                    h[8]=n&255;h[9]=(n>>8)&255;h[10:10+n]=payload
                    return [bytes(h)]
                frags=((n-10)+18)//19
                h[1]=dev_type&255;h[2]=frags;h[3]=n_seq&255;h[4]=send_type;h[5]=op
                h[8]=n&255;h[9]=(n>>8)&255;h[10:20]=payload[:10]
                out=[bytes(h)];pos=10
                for i in range(frags):
                    c=bytearray(20);c[0]=i+1
                    part=payload[pos:pos+19];c[1:1+len(part)]=part
                    out.append(bytes(c));pos+=len(part)
                return out

            def sync_payload():
                # Mirrors SendDataManager.sendAsynInfoDetail() for an ALREADY paired watch.
                # The previous implementation always sent pair=1, which is only used on first pairing.
                now=int(time.time());off=-time.timezone
                if time.daylight and time.localtime().tm_isdst:off=-time.altzone
                tm=now.to_bytes(4,"little")+int(off).to_bytes(4,"little",signed=True)+bytes([0])
                subs=[
                    bytes([0x0C,0x00,0x66,0xE8,0x03,0x00,0x00,0x01,0x19,0xAF,0x46,0x00]),
                    bytes([12,0,0x68])+tm,
                    bytes([0x08,0x00,0x7C,0x01,0xFF,0xFF,0xFF,0xFF]),
                    bytes([0x04,0x00,0x7A,0x01]),
                    bytes([0x04,0x00,0x7B,0x01]),
                    bytes([0x04,0x00,0x67,0x00]),
                    bytes([0x04,0x00,0x6D,0x01]),
                    bytes([0x05,0x00,0x78,0x00,0x00])
                ]
                body=b"".join(subs);total=len(body)+1
                return bytes([total&255,(total>>8)&255,len(subs)])+body

            async def work():
                path,raw,target_w,target_h,market_fields,market_bin_id,wf_meta=await asyncio.to_thread(build_dynamic_reference_v121)
                emit("1/9 · Cargando esfera aprobada como MARKET REAL 240×296 · BinID "+market_bin_id.upper()+"…")
                expected_cmd2=None
                oem_stream,deflated=await asyncio.to_thread(oem_dial_compress,raw)
                rep["single_face_install"]["candidate"]={
                    "path":path,
                    "format":"UtraWatch device-1180 MARKET dinámico · referencia aprobada",
                    "visual_mode":"firmware-rendered MARKET dynamic face",
                    "target_source":"real 4CC6 MARKET minimal analog engine + approved field layout",
                    "width":target_w,"height":target_h,
                    "market_live_field_offsets":market_fields,
                    "dynamic_fields":{
                        "analog_hour":"firmware dynamic · real MARKET 4CC6",
                        "analog_minute":"firmware dynamic · real MARKET 4CC6",
                        "analog_second":"firmware dynamic · real MARKET 4CC6",
                        "time":"firmware live · fields 0x8001/0x8002",
                        "steps":"firmware live · field 0x8009",
                        "heart_rate":"firmware live · field 0x800E",
                        "battery":"firmware live · field 0x8013"
                    },
                    "static_analog_note":None,
                    "raw_size":len(raw),
                    "raw_sha256":hashlib.sha256(raw).hexdigest(),
                    "market_bin_id_hex":market_bin_id,
                    "build_meta":wf_meta
                }

                c=None;events=[];messages=[];tx_n=1;wire_dev_type=1
                current=None
                ack83_event=asyncio.Event()
                ack83_statuses=[]
                protocol_acks_sent=[]

                try:
                    emit("2/9 · Conectando al servicio de esfera E91A…")
                    c,n=await self.connect_retry(2,emit,services=[CONTROL_SERVICE],pair=pair)
                    if pair: rep["windows_binding_repair"]["phase"]="gatt_verified"
                    rep["connection"]={"connected":True,"attempts":n}
                    rep["advertisement"]={k:v for k,v in (self.selected or {}).items() if k not in ("device","_watch_score")}
                    rep["single_face_install"]["auto_watch_identity"]={
                        "name":(self.selected or {}).get("name"),
                        "address":(self.selected or {}).get("address"),
                        "service_uuids":(self.selected or {}).get("service_uuids"),
                        "service_data":(self.selected or {}).get("service_data")
                    }
                    b001="0000b001-0000-1000-8000-00805f9b34fb"
                    b002="0000b002-0000-1000-8000-00805f9b34fb"

                    async def ack_device_message(msg):
                        # CEProtocolB automatically ACKs every complete device->app message.
                        # V0.81 parsed those messages but never returned this protocol ACK.
                        a=bytearray(20)
                        a[1]=msg.get("pid",0)&255
                        a[3]=msg.get("n",0)&255
                        a[4]=4
                        a[5]=msg.get("opcode",0)&255
                        a[8]=1
                        a[10]=1
                        try:
                            await asyncio.wait_for(c.write_gatt_char(b002,bytes(a),response=False),timeout=5)
                            protocol_acks_sent.append({"opcode":msg.get("opcode"),"pid":msg.get("pid"),"n":msg.get("n")})
                        except Exception as ex:
                            rep["errors"].append("protocol_ack "+hex(msg.get("opcode",0))+": "+repr(ex))

                    def complete_message(msg):
                        messages.append(msg)
                        if msg["send_type"]==4:
                            if msg["opcode"]==0x83 and msg["payload"]:
                                ack83_statuses.append(msg["payload"][0])
                                ack83_event.set()
                        else:
                            asyncio.create_task(ack_device_message(msg))

                    def rx(sender,data):
                        nonlocal current,wire_dev_type
                        b=bytes(data);events.append(b)
                        if len(b)<1:return
                        if b[0]==0:
                            if len(b)<10:return
                            # CEProtocolB learns the real device type from device traffic.
                            # This watch reports 0xFF; all following app packets must use it.
                            wire_dev_type=b[1]&255
                            plen=b[8]|(b[9]<<8)
                            take=min(10,plen)
                            current={
                                "opcode":b[5],"send_type":b[4],"pid":b[1],"n":b[3],"expected_frags":b[2],
                                "next_frag":1,"plen":plen,"payload":bytearray(b[10:10+take])
                            }
                            if b[2]==0 or len(current["payload"])>=plen:
                                msg={k:v for k,v in current.items() if k not in ("payload","next_frag","expected_frags","plen")}
                                msg["payload"]=bytes(current["payload"][:plen])
                                complete_message(msg);current=None
                        elif current is not None and b[0]==current["next_frag"]:
                            need=current["plen"]-len(current["payload"])
                            current["payload"].extend(b[1:1+min(19,max(0,need))])
                            current["next_frag"]+=1
                            if len(current["payload"])>=current["plen"]:
                                msg={k:v for k,v in current.items() if k not in ("payload","next_frag","expected_frags","plen")}
                                msg["payload"]=bytes(current["payload"][:current["plen"]])
                                complete_message(msg);current=None

                    # V1.04 proved that throwing away a rare valid B001/B002 session after
                    # one notify timeout is counterproductive. Keep it alive and let WinRT/CCCD
                    # settle; retry start_notify on the SAME characteristic/session first.
                    notify_errors=[]
                    notify_ok=False
                    for notify_try,delay in enumerate((0.0,1.5,3.0,5.0),1):
                        if delay:
                            emit(f"B001 CCCD · esperando {delay:.1f}s en la MISMA sesión GATT...")
                            await asyncio.sleep(delay)
                        try:
                            emit(f"B001 NOTIFY MISMA SESIÓN {notify_try}/4 · handle={getattr(b001,'handle',None)}")
                            await asyncio.wait_for(c.start_notify(b001,rx),timeout=12)
                            await asyncio.sleep(.5)
                            notify_ok=True
                            emit("B001 NOTIFY OK · sesión GATT conservada")
                            break
                        except Exception as nex:
                            err=type(nex).__name__+": "+str(nex)
                            notify_errors.append(err)
                            emit("B001 NOTIFY FALLÓ · "+err)
                            if not c.is_connected:
                                emit("B001 · Windows marcó la sesión desconectada; no se destruye otra sesión válida innecesariamente.")
                                break
                    rep["single_face_install"]["notify_recovery"]={"errors":notify_errors,"ok":notify_ok,"strategy":"same_gatt_session_cccd_settle"}
                    if not notify_ok: raise RuntimeError("B001 notify no operativo en sesión GATT válida: "+" | ".join(notify_errors))

                    async def tx(op,payload=b"",send_type=1,wait=.5):
                        nonlocal tx_n,wire_dev_type
                        start=len(messages)
                        this_n=tx_n&255
                        this_dev_type=wire_dev_type&255
                        frames=build(this_dev_type,this_n,op,payload,send_type)
                        for fr in frames:
                            await asyncio.wait_for(c.write_gatt_char(b002,fr,response=False),timeout=5)
                            await asyncio.sleep(.045)
                        tx_n=(tx_n+1)&255
                        if wait:await asyncio.sleep(wait)
                        return {"n":this_n,"dev_type":this_dev_type},messages[start:],frames

                    async def tx83_wait(payload,timeout=4.0):
                        before=len(ack83_statuses);ack83_event.clear()
                        wire,_,frames=await tx(0x83,payload,1,0)
                        if len(ack83_statuses)==before:
                            try:await asyncio.wait_for(ack83_event.wait(),timeout=timeout)
                            except asyncio.TimeoutError:pass
                        status=ack83_statuses[-1] if len(ack83_statuses)>before else None
                        return wire,status,frames

                    def latest_data(opcode,since=0):
                        for m in reversed(messages[since:]):
                            if m["opcode"]==opcode and m["send_type"]==1:
                                return m["payload"]
                        return None

                    async def wait_data(opcode,since,timeout=6.0):
                        end=time.monotonic()+timeout
                        while time.monotonic()<end:
                            value=latest_data(opcode,since)
                            if value is not None:return value
                            await asyncio.sleep(.08)
                        return None

                    def dial_info(payload):
                        if payload is None or len(payload)<17:return None
                        return {
                            "index":payload[0],
                            "cmd2_hex":payload[1:7].hex(),
                            "cmd3_raw":payload[7:9].hex(),
                            "all_len":int.from_bytes(payload[9:13],"little"),
                            "current_pos":int.from_bytes(payload[13:17],"little"),
                            "raw_hex":payload.hex()
                        }

                    def parse_dev_sync_properties(payload):
                        out={}
                        if payload is None or len(payload)<3:return out
                        count=payload[2];pos=3
                        for _ in range(count):
                            if pos+3>len(payload):break
                            item_len=int.from_bytes(payload[pos:pos+2],"little")
                            if item_len<3 or pos+item_len>len(payload):break
                            dtype=payload[pos+2]
                            out[dtype]=bytes(payload[pos+3:pos+item_len])
                            pos+=item_len
                        return out

                    def parse_dev_sync_pid(payload):
                        data=parse_dev_sync_properties(payload).get(31)
                        if data is None or len(data)<2:return None
                        value=int.from_bytes(data[:2],"little")
                        return value if value>0 else None

                    def fetch_face_slots(device_id):
                        # Exact endpoint used by UtraWatch V2ChoiceClockdialVM.faceConfig(pid, 1).
                        last=None
                        for scheme in ("http","https"):
                            url=(scheme+"://watchhealth.com.cn/YueDongService/app/faceConfig.do?deviceId="+
                                 str(int(device_id))+"&pageIndex=1")
                            try:
                                req=urllib.request.Request(url,headers={"User-Agent":"UtraWatch/1.5 RelojLab/0.81","Accept":"application/json"})
                                with urllib.request.urlopen(req,timeout=10) as response:
                                    obj=json.loads(response.read().decode("utf-8","replace"))
                                rows=obj.get("result") if isinstance(obj,dict) else None
                                if obj.get("code")!=0 or not isinstance(rows,list) or not rows:
                                    raise RuntimeError("faceConfig rechazó deviceId="+str(device_id)+": "+str(obj)[:180])
                                usable=[]
                                for row in rows:
                                    if not isinstance(row,dict):continue
                                    try:order=int(row.get("showOrder"))
                                    except Exception:continue
                                    if order>0:usable.append(row)
                                editable=[x for x in usable if int(x.get("editable",0) or 0)==1]
                                if not editable:raise RuntimeError("faceConfig no contiene editable=1")
                                custom=min(editable,key=lambda x:int(x.get("showOrder")))
                                custom_order=int(custom.get("showOrder"))
                                max_order=max(int(x.get("showOrder")) for x in usable)
                                return {
                                    "device_id":int(device_id),"source":"UtraWatch faceConfig.do",
                                    "custom_show_order":custom_order,"custom_index":custom_order-1,
                                    "market_show_order":max_order+1,"market_index":max_order,
                                    "face_count":len(usable),"editable_id":custom.get("id")
                                }
                            except Exception as ex:last=ex
                        raise RuntimeError("No se pudo resolver faceConfig: "+repr(last))

                    async def transfer_slot(command,label,file_bytes,chunks):
                        result={"cmd":command,"label":label,"bytes":0,"acks":0,"blocks":len(chunks),"ok":False}
                        for idx,chunk in enumerate(chunks,1):
                            offset=(idx-1)*300
                            app_payload=bytes([command])+len(file_bytes).to_bytes(4,"little")+offset.to_bytes(4,"little")+chunk
                            wire,status,frames=await tx83_wait(app_payload)
                            connected=bool(getattr(c,"is_connected",False))
                            rep["single_face_install"]["blocks"].append({
                                "slot_cmd":command,"slot":label,"index":idx,
                                "wire_dev_type":wire.get("dev_type"),"wire_n":wire.get("n"),"offset":offset,
                                "data_length":len(chunk),"wtwd_payload_length":len(app_payload),
                                "frame_count":len(frames),"status":status,"connected":connected
                            })
                            result["bytes"]+=len(chunk)
                            if status==1:result["acks"]+=1
                            rep["single_face_install"]["payload_bytes_written"]+=len(chunk)
                            if status==1:rep["single_face_install"]["ack_count"]+=1
                            if idx==1 or idx%10==0 or idx==len(chunks):
                                emit(label+" · "+str(idx)+"/"+str(len(chunks))+" · "+str(result["bytes"])+"/"+str(len(file_bytes))+" B · ACK="+str(status))
                            if status!=1 or not connected:
                                raise RuntimeError(label+" bloque "+str(idx)+" rechazado o desconectado: "+str(status))
                        result["ok"]=(result["bytes"]==len(file_bytes) and result["acks"]==len(chunks))
                        return result

                    emit("3/9 · Inicialización OEM real · DEVINFO → PAIR SYNC → DEV_SYNC…")
                    dev_mark=len(messages)
                    await tx(0x02,b"",3,0)
                    dev_info=await wait_data(0x02,dev_mark,4.5)
                    customer_id=(dev_info[1] if dev_info is not None and len(dev_info)>=2 else None)
                    hardware_tuple=(tuple(dev_info[2:6]) if dev_info is not None and len(dev_info)>=6 else None)

                    # Official UtraWatch sends sendAsynInfoDetail() first. On an already paired
                    # device pair=0; DEV_SYNC (0x09) is then emitted by the watch.
                    sync_mark=len(messages)
                    host_now=datetime.now().astimezone()
                    rep["single_face_install"]["clock_sync"]={
                        "host_iso":host_now.isoformat(),
                        "utc_offset_seconds":int(host_now.utcoffset().total_seconds()) if host_now.utcoffset() else 0,
                        "method":"OEM DEV_SYNC payload 0x68"
                    }
                    emit("HORA · sincronizando reloj con "+host_now.strftime("%H:%M:%S")+" · zona "+host_now.strftime("%z"))
                    await tx(0x6E,sync_payload(),1,0)
                    dev_sync=await wait_data(0x09,sync_mark,8.0)
                    if dev_sync is None:
                        emit("DEV_SYNC espontáneo no llegó; solicitando 0x09 una vez…")
                        sync_mark=len(messages)
                        await tx(0x09,b"",3,0)
                        dev_sync=await wait_data(0x09,sync_mark,5.0)

                    props=parse_dev_sync_properties(dev_sync)
                    device_pid=parse_dev_sync_pid(dev_sync)
                    pid_source="DEV_SYNC/NEW_PID"
                    cap=props.get(22)

                    battery_payload=props.get(3)
                    battery_percent=(int(battery_payload[0]) if battery_payload and len(battery_payload)>=1 else None)
                    if battery_percent is not None and not (0<=battery_percent<=100):
                        battery_percent=None
                    rep["single_face_install"]["candidate"].update({
                        "battery_percent_seen_during_install":battery_percent,
                        "raw_header_hex":raw[:16].hex(),
                        "oem_stream_size":len(oem_stream),
                        "deflate_size":len(deflated),
                        "oem_stream_sha256":hashlib.sha256(oem_stream).hexdigest(),
                        "oem_crc16":f"0x{crc16_8005(deflated):04X}",
                        "oem_header_hex":oem_stream[:20].hex()
                    })
                    rep["single_face_install"]["live_bindings"]={
                        "analog_hour":{"source":"real MARKET 2D7F analog engine","continuous_live":True},
                        "analog_minute":{"source":"real MARKET 2D7F analog engine","continuous_live":True},
                        "analog_second":{"source":"real MARKET 2D7F analog engine","continuous_live":True},
                        "time":{"source":"MARKET fields 0x8001/0x8002","continuous_live":True},
                        "steps":{"source":"MARKET field 0x8009","continuous_live":True},
                        "heart_rate":{"source":"MARKET field 0x800E","continuous_live":True},
                        "battery":{"source":"MARKET field 0x8013","continuous_live":True,
                                   "value_seen_during_install":battery_percent}
                    }
                    emit("DATOS · agujas LIVE · hora LIVE · pasos LIVE · pulso LIVE · batería LIVE")

                    if device_pid is None:
                        pid_mark=len(messages)
                        await tx(0x1F,b"",3,0)
                        pid_payload=await wait_data(0x1F,pid_mark,3.0)
                        if pid_payload is not None and len(pid_payload)>=2:
                            candidate_pid=int.from_bytes(pid_payload[:2],"little")
                            if candidate_pid>0:device_pid=candidate_pid;pid_source="direct NEW_PID"

                    if device_pid is None and customer_id not in (None,0,255):
                        device_pid=int(customer_id);pid_source="legacy customer_id"
                    if device_pid is None and customer_id==255 and hardware_tuple==(3,1,1,1):
                        device_pid=102;pid_source="validated model-102 fallback"

                    if cap is None:
                        cap_mark=len(messages)
                        await tx(0x16,b"",3,0)
                        cap=await wait_data(0x16,cap_mark,3.0)
                    has_dial_compress=(bool(cap[2]&0x20) if cap is not None and len(cap)>=3 else None)

                    face_slots=None;slot_error=None
                    if device_pid is not None:
                        try:face_slots=await asyncio.to_thread(fetch_face_slots,device_pid)
                        except Exception as ex:slot_error=repr(ex)
                    if face_slots is None and device_pid==102:
                        face_slots={"device_id":102,"source":"verified OEM snapshot 2026-09-27",
                                    "custom_show_order":6,"custom_index":5,"market_show_order":7,
                                    "market_index":6,"face_count":6,"editable_id":406}
                    rep["single_face_install"]["slot_navigation"]={
                        "pid":device_pid,"pid_source":pid_source,"customer_id":customer_id,
                        "hardware_tuple":hardware_tuple,"dev_sync_hex":dev_sync.hex() if dev_sync else None,
                        "dev_sync_properties":{str(k):v.hex() for k,v in props.items()},
                        "face_slots":face_slots,"face_config_error":slot_error
                    }
                    rep["single_face_install"]["function_control"]={
                        "payload_hex":cap.hex() if cap else None,
                        "has_dial_compress":has_dial_compress,
                        "fallback_used":has_dial_compress is None,
                        "fallback_mode":"raw WF" if has_dial_compress is None else None
                    }
                    if not face_slots or face_slots.get("custom_index") is None:
                        raise RuntimeError("No se pudo resolver el slot editable de la esfera; no se seleccionará un índice a ciegas.")

                    # Compression is optional in the OEM SDK. Unknown capability must
                    # fall back to the raw WF, never to compressed data.
                    file_bytes=oem_stream if has_dial_compress is True else raw
                    rep["single_face_install"]["transfer_compressed"]=has_dial_compress is True
                    rep["single_face_install"]["transfer_size"]=len(file_bytes)

                    emit("4/9 · Abriendo transferencia OEM · esperando WATCH_FACE_INFO 0x84 real…")
                    pre=None;state_attempts=[]
                    for attempt in range(1,4):
                        before_mark=len(messages)
                        await tx(0x84,b"",3,0)
                        pre_payload=await wait_data(0x84,before_mark,5.0)
                        info=dial_info(pre_payload)
                        state_attempts.append({"attempt":attempt,"received":info is not None,
                                               "raw_hex":pre_payload.hex() if pre_payload else None})
                        if info is not None:
                            pre=info;break
                        await asyncio.sleep(.7)
                    rep["single_face_install"]["file_state_gate"]={"attempts":state_attempts,"ready":pre is not None}
                    rep["single_face_install"]["pre_dial_info"]=pre
                    if pre is None:
                        raise RuntimeError("El reloj ACKeó comandos pero no devolvió WATCH_FACE_INFO 0x84; transferencia NO iniciada para evitar falsos positivos.")

                    chunks=[file_bytes[i:i+300] for i in range(0,len(file_bytes),300)]
                    emit("5/9 · Instalando la esfera NUEVA en MARKET cmd=3 · "+str(len(chunks))+" bloques…")
                    dynamic_transfer=await transfer_slot(3,"DYNAMIC-MARKET",file_bytes,chunks)
                    rep["single_face_install"]["dynamic_market_transfer"]=dynamic_transfer

                    def market_id_ok(info):
                        if not info:return False
                        raw_hex=(info.get("cmd3_raw") or "").lower()
                        wanted=market_bin_id.lower()
                        try: reverse=bytes.fromhex(wanted)[::-1].hex()
                        except Exception: reverse=wanted
                        return raw_hex in (wanted,reverse)

                    emit("6/9 · MARKET transferido; esperando que el firmware registre BinID "+market_bin_id.upper()+"…")
                    registration_attempts=[]
                    post=None
                    for reg_try in range(1,6):
                        post_mark=len(messages)
                        await tx(0x84,b"",3,0)
                        post_payload=await wait_data(0x84,post_mark,5.0)
                        post=dial_info(post_payload)
                        registered=market_id_ok(post)
                        registration_attempts.append({"attempt":reg_try,"dial_info":post,"registered":registered})
                        if registered:break
                        await asyncio.sleep(1.4)
                    rep["single_face_install"]["post_dial_info"]=post
                    rep["single_face_install"]["market_registration"]={
                        "expected_bin_id_hex":market_bin_id,
                        "verified":market_id_ok(post),
                        "attempts":registration_attempts
                    }
                    state_changed=bool(pre and post and pre.get("raw_hex")!=post.get("raw_hex"))
                    rep["single_face_install"]["dial_state_changed"]=state_changed

                    emit("7/9 · Seleccionando y verificando el slot MARKET nuevo…")
                    market_index=face_slots.get("market_index")
                    if market_index is None:
                        raise RuntimeError("UtraWatch no resolvió el índice MARKET de este reloj")
                    market_index=int(market_index)
                    selection_attempts=[]
                    selection_verified=False
                    selected_info=None
                    sel_status=None
                    for select_try in range(1,5):
                        _,sel_status,_=await tx83_wait(bytes([1,market_index&255]),3.0)
                        await asyncio.sleep(1.6 if select_try==1 else 2.2)
                        verify_mark=len(messages)
                        await tx(0x84,b"",3,0)
                        selected_payload=await wait_data(0x84,verify_mark,5.0)
                        selected_info=dial_info(selected_payload)
                        index_ok=bool(selected_info and selected_info.get("index")==market_index)
                        binid_ok=market_id_ok(selected_info)
                        ok=bool(sel_status==1 and index_ok and binid_ok)
                        selection_attempts.append({
                            "attempt":select_try,"status":sel_status,
                            "dial_info":selected_info,
                            "index_ok":index_ok,"market_bin_id_ok":binid_ok,
                            "verified":ok
                        })
                        if ok:
                            selection_verified=True
                            break
                    if sel_status!=1:
                        raise RuntimeError("El reloj rechazó la selección del slot MARKET "+str(market_index))
                    selection={
                        "index":market_index,
                        "show_order":face_slots.get("market_show_order"),
                        "status":sel_status,
                        "verified":selection_verified,
                        "expected_market_bin_id_hex":market_bin_id,
                        "dial_info":selected_info,
                        "attempts":selection_attempts
                    }
                    rep["single_face_install"]["selection_lock"]=selection
                    rep["single_face_install"]["market_attempt"]={
                        "attempted":True,
                        "transfer_cmd":3,
                        "bin_id_hex":market_bin_id,
                        "registration_verified":market_id_ok(post),
                        "selection_verified":selection_verified
                    }
                    rep["single_face_install"]["factory_faces_deleted"]=False
                    rep["single_face_install"]["factory_faces_note"]="UtraWatch no expone comando de borrado para esferas integradas en firmware; sólo se reemplazaron los slots regrabables."

                    emit("8/9 · Postcheck de conexión y selección…")
                    connected=bool(getattr(c,"is_connected",False))
                    transfer_ok=bool(dynamic_transfer.get("ok") and connected)
                    registration_ok=bool(rep["single_face_install"].get("market_registration",{}).get("verified"))
                    all_ok=bool(transfer_ok and registration_ok and sel_status==1 and selection_verified)
                    rep["single_face_install"]["protocol_acks_sent"]=protocol_acks_sent
                    rep["single_face_install"]["wire_protocol"]={
                        "final_dev_type":wire_dev_type,"next_n":tx_n,
                        "note":"CEProtocolB byte1=device_type; byte3=N"
                    }
                    rep["single_face_install"]["classification"]=(
                        "approved_market_face_installed_and_selected" if all_ok else
                        "approved_market_face_registered_selection_pending" if transfer_ok and registration_ok else
                        "approved_market_face_transferred_registration_pending" if transfer_ok else
                        "approved_market_face_install_failed"
                    )
                    rep["single_face_install"]["connected_end"]=connected
                    rep["single_face_install"]["phase"]="complete"
                    emit("9/9 · V1.22 FINALIZADA · "+rep["single_face_install"]["classification"])
                    return rep
                finally:
                    if c:
                        try:await asyncio.wait_for(c.disconnect(),timeout=5)
                        except Exception as ex:rep["errors"].append("disconnect: "+repr(ex))

            def done(result,error):
                rep["connection"]=dict(getattr(self,"connection_state",{}))
                if result is not None: result["connection"]=rep["connection"]
                if error:
                    if pair: rep["windows_binding_repair"]["installation_error"]=repr(error)
                    rep["errors"].append(type(error).__name__+": "+str(error))
                    rep["single_face_install"]["phase"]="error"
                    self.report=rep;self.show()
                    append("V1.22 FALLÓ · "+repr(error))
                    append("DIAGNÓSTICO JSON · "+json.dumps(rep,ensure_ascii=False,separators=(",",":")))
                    self.status.set("V1.22 terminó con error. COPIAR DIAGNÓSTICO.")
                    return
                self.report=result;self.show()
                append("DIAGNÓSTICO JSON · "+json.dumps(result,ensure_ascii=False,separators=(",",":")))
                append("ESFERA ÚNICA · "+result["single_face_install"]["classification"]+".")
                self.status.set("V1.22 finalizada. Revisá el reloj y COPIAR DIAGNÓSTICO.")
            self.run_async(asyncio.wait_for(work(),timeout=360),done)
        def repair_binding():
            if self.ble_busy:
                append("Esperá a que termine la operación Bluetooth actual.")
                return
            selected=dict(self.selected or {})
            address=selected.get("address")
            if not address:
                messagebox.showinfo("Reparar vínculo", "Primero seleccioná tu reloj.",parent=w)
                return
            if not messagebox.askyesno("Reparar vínculo de Windows",
                    "Se quitará únicamente el vínculo Bluetooth de Windows de " +
                    selected.get("name","reloj") + " (" + address + ").\n\n" +
                    "Después se intentará emparejar y se continuará con la instalación de la esfera. " +
                    "La reparación es de mejor esfuerzo: si Windows no puede consultar el vínculo, la app igualmente continuará con emparejamiento directo a esta misma dirección.\n\n" +
                    "No restaura el reloj de fábrica ni borra sus esferas. ¿Continuar?",parent=w):
                return
            from windows_binding import repair_selected
            def emit_repair(message):
                self.ui_queue.put(lambda text=message:append(text))
            def repaired(result,error):
                if error:
                    rep=self.base_report()
                    rep["windows_binding_repair"]=dict(getattr(self,"binding_repair",{}))
                    rep["errors"].append(repr(error))
                    self.report=rep;self.show()
                    append("REPARACIÓN DETENIDA · "+repr(error))
                    append("DIAGNÓSTICO JSON · "+json.dumps(rep,ensure_ascii=False))
                    return
                append("REPARACIÓN · continuando con emparejamiento e instalación…")
                ota_lab(pair=True)
            self.run_async(repair_selected(self,address,emit_repair),repaired)
        primary_test.configure(text="REPARAR VÍNCULO E INSTALAR V1.22",command=repair_binding)
        ttk.Button(row,text="INSTALAR SIN REPARAR",command=ota_lab).pack(side="left",padx=4)
        append("V1.22 LISTA · 1º REPARAR VÍNCULO E INSTALAR V1.22; 2º CONFIRMAR EL RELOJ; 3º COPIAR DIAGNÓSTICO. Quita sólo su vínculo Windows y solicita emparejar antes de consultar GATT.")

        ttk.Button(row,text="CAPTURAR 90 s",command=capture).pack(side="left",padx=4)
        append("La instalación sólo comienza después de confirmar una conexión ATT operativa.")
    def check_update(self):
        self.status.set("Buscando actualización…")
        def work():
            url=VERSION_URL+"?cache_bust="+str(int(time.time()*1000))
            req=urllib.request.Request(url,headers={"User-Agent":"RelojLab/"+APP_VERSION,"Cache-Control":"no-cache, no-store","Pragma":"no-cache"})
            with urllib.request.urlopen(req,timeout=15) as r:meta=json.loads(r.read().decode("utf-8"))
            if ver_tuple(meta["version"])<=ver_tuple(APP_VERSION):return ("current",meta,None)
            install_dir=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"RelojLab")
            os.makedirs(install_dir,exist_ok=True)
            target=os.path.join(install_dir,"RelojLab-"+meta["version"]+".exe")
            temp=target+".download"
            req=urllib.request.Request(meta["exe_url"]+"?v="+meta["version"],headers={"User-Agent":"RelojLab/"+APP_VERSION,"Cache-Control":"no-cache"})
            with urllib.request.urlopen(req,timeout=180) as r,open(temp,"wb") as out:
                while True:
                    chunk=r.read(1024*1024)
                    if not chunk:break
                    out.write(chunk)
            with open(temp,"rb") as chk:magic=chk.read(2)
            if os.path.getsize(temp)<5_000_000 or magic!=b"MZ":raise RuntimeError("La descarga no es un EXE válido.")
            if meta.get("sha256"):
                with open(temp,"rb") as downloaded:digest=hashlib.file_digest(downloaded,"sha256").hexdigest()
                if digest!=meta["sha256"]:raise RuntimeError("La descarga no coincide con la versión publicada (SHA-256).")
            os.replace(temp,target)
            return ("ready",meta,target)
        def done(r,e):
            if e:
                self.status.set("Error al actualizar."); messagebox.showerror("Actualización","No se pudo actualizar.\n\n"+repr(e)); return
            state,meta,target=r
            if state=="current":
                self.status.set("Ya tenés la última versión."); messagebox.showinfo("Actualización","Reloj Lab "+APP_VERSION+" ya está actualizado."); return
            self.status.set("Actualización validada. Reiniciando…")
            env=os.environ.copy()
            env["PYINSTALLER_RESET_ENVIRONMENT"]="1"
            env.pop("_PYI_APPLICATION_HOME_DIR",None)
            env.pop("_MEIPASS2",None)
            try:
                subprocess.Popen([target],cwd=os.path.dirname(target),env=env,close_fds=True)
            except Exception as ex:
                messagebox.showerror("Actualización","Se descargó correctamente, pero no se pudo abrir:\n"+repr(ex)); return
            self.root.after(1500,self.close_app)
        self.run_thread(work,done)
    def show(self):
        self.text.delete("1.0","end"); self.text.insert("end",json.dumps(self.report,ensure_ascii=False,indent=2))
    def save(self):
        if not self.report:messagebox.showinfo("Diagnóstico","Primero ejecutá el diagnóstico."); return
        p=filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("JSON","*.json")],initialfile="reloj-diagnostico-v"+APP_VERSION+".json")
        if p:
            with open(p,"w",encoding="utf-8") as f:json.dump(self.report,f,ensure_ascii=False,indent=2)
            self.status.set("Diagnóstico guardado.")
if __name__=="__main__":
    root=tk.Tk(); App(root); root.mainloop()
