import asyncio, json, platform, sys, threading, tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timezone
from bleak import BleakScanner, BleakClient
import urllib.request, tempfile, os, subprocess, time, hashlib, queue, math

APP_VERSION="1.19.0"
VERSION_URL="https://raw.githubusercontent.com/Yakoderaa/reloj/main/version.json"
OAD_SERVICE="f000ffc0-0451-4000-b000-000000000000"
CONTROL_SERVICE="0000e91a-0000-1000-8000-00805f9b34fb"
NOTIFY_UUIDS=["f000ffc2-0451-4000-b000-000000000000","0000b001-0000-1000-8000-00805f9b34fb"]

def ver_tuple(v):
    try:return tuple(int(x) for x in v.strip().lstrip("vV").split("."))
    except:return (0,)

class App:
    def __init__(self,root):
        self.root=root; root.title("Reloj Lab V1.19"); root.geometry("1000x700")
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
        ttk.Label(top,text="V1.19 · esfera única OEM").pack(side="left",padx=12)
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
        primary_test=ttk.Button(row,text="INSTALAR ESFERA SINCRONIZADA V1.19")
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
                append("V1.19 NO INICIADA · Bluetooth ocupado.")
                return
            append("V1.19 · GATT DIRECTO E91A · consulta sólo el servicio de la esfera durante la instalación. Conserva validación ATT, dos intentos y diagnóstico por intento; no reinicia Bluetooth.")
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

            def build_exact_reference_customize():
                # Exact approved reference, cropped to the physical 240x296 display.
                # UtraWatch CUSTOMIZE cBinFile:
                # 10-byte config + 240*296 BGR565 pixels.
                import base64,zlib
                packed='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'
                raw=zlib.decompress(base64.b64decode(packed))
                expected='61b86e4f5f998a436c88785e14436b00d797a705dcea6879e96a7828c4cb62a2'
                if len(raw)!=142090 or hashlib.sha256(raw).hexdigest()!=expected:
                    raise RuntimeError("Referencia visual V1.19 embebida corrupta")
                if raw[:10].hex()!="000000000002f0002801":
                    raise RuntimeError("Cabecera CUSTOMIZE V1.19 inválida")
                folder=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),
                                    "RelojLab","wf-analysis-v086")
                os.makedirs(folder,exist_ok=True)
                path=os.path.join(folder,"exact-approved-reference-v086.bin")
                with open(path,"wb") as fh:fh.write(raw)
                return path,raw,240,296

            def build_live_customize(base_raw,battery_percent=None):
                # CUSTOMIZE supports three live firmware fields:
                # time_pos plus one field above and one below the time.
                # UtraWatch exposes: date=1, sleep=2, heart=4, steps=8.
                # Use time at the top, steps above it and heart rate below it.
                raw=bytearray(base_raw)
                if len(raw)!=142090 or raw[5]!=2:
                    raise RuntimeError("Base CUSTOMIZE V1.19 inválida")

                # Live metadata. Target orange sampled from the approved design:
                # RGB ~= (239,83,64) -> BGR565 0x429D -> little-endian 9d42.
                raw[0]=0       # time at top
                raw[1]=8       # live steps
                raw[2]=4       # live heart rate
                raw[3]=0x9D
                raw[4]=0x42
                raw[5]=2

                w=240;h=296;pix0=10
                def setpix(x,y,v=0):
                    if 0<=x<w and 0<=y<h:
                        off=pix0+((y*w+x)*2)
                        raw[off]=(v>>8)&255
                        raw[off+1]=v&255

                # Remove the four baked sample-value areas from the approved raster.
                # Keep the central analog artwork untouched for visual continuity.
                for x0,y0,x1,y1 in [
                    (5,15,102,68),      # old 10:09
                    (174,13,238,66),    # old 87%
                    (3,235,120,294),    # old 8,426 pasos
                    (143,235,239,294),  # old 72 lpm
                ]:
                    for yy in range(y0,y1):
                        for xx in range(x0,x1):
                            setpix(xx,yy,0)

                # Battery is not an official live CUSTOMIZE complication.
                # Render the battery value read from DEV_SYNC at install time.
                font={
                    "0":["01110","10001","10011","10101","11001","10001","01110"],
                    "1":["00100","01100","00100","00100","00100","00100","01110"],
                    "2":["01110","10001","00001","00010","00100","01000","11111"],
                    "3":["11110","00001","00001","01110","00001","00001","11110"],
                    "4":["00010","00110","01010","10010","11111","00010","00010"],
                    "5":["11111","10000","10000","11110","00001","00001","11110"],
                    "6":["01110","10000","10000","11110","10001","10001","01110"],
                    "7":["11111","00001","00010","00100","01000","01000","01000"],
                    "8":["01110","10001","10001","01110","10001","10001","01110"],
                    "9":["01110","10001","10001","01111","00001","00001","01110"],
                    "%":["10001","00010","00100","01000","10001","00000","00000"],
                    "-":["00000","00000","11111","00000","00000","00000","00000"],
                }
                def text5(txt,x,y,scale=2,color=0x429D):
                    for ch in txt:
                        pat=font.get(ch,font["-"])
                        for ry,row in enumerate(pat):
                            for rx,on in enumerate(row):
                                if on=="1":
                                    for sy in range(scale):
                                        for sx in range(scale):
                                            setpix(x+rx*scale+sx,y+ry*scale+sy,color)
                        x+=6*scale

                battery_text=(str(int(battery_percent))+"%") if battery_percent is not None else "--%"
                # Right-align in the same upper-right area as the approved design.
                x=max(174,236-len(battery_text)*12)
                text5(battery_text,x,27,2,0x429D)

                return bytes(raw),battery_text
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
                emit("1/9 · Cargando diseño aprobado 240×296; los datos se vincularán al reloj tras DEV_SYNC…")
                path,raw,target_w,target_h=await asyncio.to_thread(build_exact_reference_customize)
                expected_cmd2=None
                oem_stream=None
                deflated=None
                rep["single_face_install"]["candidate"]={
                    "path":path,
                    "format":"UtraWatch CUSTOMIZE cBinFile · referencia aprobada + datos vivos",
                    "visual_mode":"approved raster + firmware live fields",
                    "target_source":"approved target image",
                    "width":target_w,"height":target_h,
                    "picture_mode":2,
                    "dynamic_fields":{
                        "time":"firmware live",
                        "steps":"firmware live · CUSTOMIZE value 8",
                        "heart_rate":"firmware live · CUSTOMIZE value 4",
                        "battery":"read from watch at install time"
                    },
                    "static_analog_note":"Las agujas/segundero del raster siguen siendo gráficos; V1.19 no los declara dinámicos.",
                    "base_raw_size":len(raw),
                    "base_raw_sha256":hashlib.sha256(raw).hexdigest()
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
                    raw,battery_text=build_live_customize(raw,battery_percent)
                    expected_cmd2=raw[:6].hex()
                    oem_stream,deflated=await asyncio.to_thread(oem_dial_compress,raw)
                    rep["single_face_install"]["candidate"].update({
                        "battery_percent_at_install":battery_percent,
                        "battery_text":battery_text,
                        "raw_size":len(raw),
                        "raw_sha256":hashlib.sha256(raw).hexdigest(),
                        "raw_header_hex":raw[:10].hex(),
                        "expected_cmd2_hex":expected_cmd2,
                        "oem_stream_size":len(oem_stream),
                        "deflate_size":len(deflated),
                        "oem_stream_sha256":hashlib.sha256(oem_stream).hexdigest(),
                        "oem_crc16":f"0x{crc16_8005(deflated):04X}",
                        "oem_header_hex":oem_stream[:20].hex()
                    })
                    rep["single_face_install"]["live_bindings"]={
                        "time":{"source":"watch firmware clock","time_pos":raw[0]},
                        "steps":{"source":"watch firmware","field_value":raw[1]},
                        "heart_rate":{"source":"watch firmware","field_value":raw[2]},
                        "battery":{"source":"DEV_SYNC DATA_TYPE_BATTERY_INFO=3","value_at_install":battery_percent,
                                   "continuous_live":False}
                    }
                    emit("DATOS · hora firmware LIVE · pasos LIVE · pulso LIVE · batería="+battery_text)

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
                    emit("5/9 · Instalando referencia exacta en CUSTOMIZE cmd=2 · "+str(len(chunks))+" bloques…")
                    exact_transfer=await transfer_slot(2,"EXACT-CUSTOMIZE",file_bytes,chunks)
                    rep["single_face_install"]["exact_customize_transfer"]=exact_transfer

                    emit("6/9 · CUSTOMIZE exacto completo; esperando aplicación física…")
                    await asyncio.sleep(4.0)

                    emit("7/9 · Seleccionando y verificando el slot CUSTOMIZE exacto…")
                    post_mark=len(messages)
                    await tx(0x84,b"",3,0)
                    post_payload=await wait_data(0x84,post_mark,5.0)
                    post=dial_info(post_payload)
                    rep["single_face_install"]["post_dial_info"]=post
                    state_changed=bool(pre and post and pre.get("raw_hex")!=post.get("raw_hex"))
                    rep["single_face_install"]["dial_state_changed"]=state_changed

                    custom_index=face_slots.get("custom_index")
                    if custom_index is None:
                        raise RuntimeError("UtraWatch no resolvió el índice CUSTOMIZE de este reloj")
                    custom_index=int(custom_index)
                    selection_attempts=[]
                    selection_verified=False
                    selected_info=None
                    sel_status=None
                    for select_try in range(1,4):
                        _,sel_status,_=await tx83_wait(bytes([1,custom_index&255]),3.0)
                        await asyncio.sleep(1.4 if select_try==1 else 2.0)
                        verify_mark=len(messages)
                        await tx(0x84,b"",3,0)
                        selected_payload=await wait_data(0x84,verify_mark,5.0)
                        selected_info=dial_info(selected_payload)
                        index_ok=bool(selected_info and selected_info.get("index")==custom_index)
                        cmd2_ok=bool(selected_info and selected_info.get("cmd2_hex")==expected_cmd2)
                        ok=bool(sel_status==1 and index_ok and cmd2_ok)
                        selection_attempts.append({
                            "attempt":select_try,"status":sel_status,
                            "dial_info":selected_info,
                            "index_ok":index_ok,"cmd2_metadata_ok":cmd2_ok,
                            "verified":ok
                        })
                        if ok:
                            selection_verified=True
                            break
                    if sel_status!=1:
                        raise RuntimeError("El reloj rechazó la selección del slot CUSTOMIZE "+str(custom_index))
                    selection={
                        "index":custom_index,
                        "show_order":face_slots.get("custom_show_order"),
                        "status":sel_status,
                        "verified":selection_verified,
                        "expected_cmd2_hex":expected_cmd2,
                        "dial_info":selected_info,
                        "attempts":selection_attempts
                    }
                    rep["single_face_install"]["selection_lock"]=selection

                    rep["single_face_install"]["market_attempt"]={
                        "attempted":False,
                        "reason":"V1.19 usa exclusivamente CUSTOMIZE, la ruta ya confirmada visualmente en V0.83"
                    }
                    rep["single_face_install"]["factory_faces_deleted"]=False
                    rep["single_face_install"]["factory_faces_note"]="UtraWatch no expone comando de borrado para esferas integradas en firmware; sólo se reemplazaron los slots regrabables."

                    emit("8/9 · Postcheck de conexión y selección…")
                    connected=bool(getattr(c,"is_connected",False))
                    transfer_ok=bool(exact_transfer.get("ok") and connected)
                    all_ok=bool(transfer_ok and sel_status==1 and selection_verified)
                    rep["single_face_install"]["protocol_acks_sent"]=protocol_acks_sent
                    rep["single_face_install"]["wire_protocol"]={
                        "final_dev_type":wire_dev_type,"next_n":tx_n,
                        "note":"CEProtocolB byte1=device_type; byte3=N"
                    }
                    rep["single_face_install"]["classification"]=(
                        "exact_approved_reference_installed_and_selected" if all_ok else
                        "exact_approved_reference_transferred_selection_pending" if transfer_ok and sel_status==1 else
                        "exact_approved_reference_install_failed"
                    )
                    rep["single_face_install"]["connected_end"]=connected
                    rep["single_face_install"]["phase"]="complete"
                    emit("9/9 · V1.19 FINALIZADA · "+rep["single_face_install"]["classification"])
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
                    append("V1.19 FALLÓ · "+repr(error))
                    append("DIAGNÓSTICO JSON · "+json.dumps(rep,ensure_ascii=False,separators=(",",":")))
                    self.status.set("V1.19 terminó con error. COPIAR DIAGNÓSTICO.")
                    return
                self.report=result;self.show()
                append("DIAGNÓSTICO JSON · "+json.dumps(result,ensure_ascii=False,separators=(",",":")))
                append("ESFERA ÚNICA · "+result["single_face_install"]["classification"]+".")
                self.status.set("V1.19 finalizada. Revisá el reloj y COPIAR DIAGNÓSTICO.")
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
        primary_test.configure(text="REPARAR VÍNCULO E INSTALAR V1.19",command=repair_binding)
        ttk.Button(row,text="INSTALAR SIN REPARAR",command=ota_lab).pack(side="left",padx=4)
        append("V1.19 LISTA · 1º REPARAR VÍNCULO E INSTALAR V1.19; 2º CONFIRMAR EL RELOJ; 3º COPIAR DIAGNÓSTICO. Quita sólo su vínculo Windows y solicita emparejar antes de consultar GATT.")

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
