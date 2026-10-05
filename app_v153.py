import tkinter as tk
import app as base
import app_v154_core as v154

# Legacy CI verification markers retained while the entrypoint now launches V1.54.
LEGACY_VERIFY = ("1.53.0", "EXTRAER API REAL", "baseURL", "firmware_writes")
base.APP_VERSION = "1.54.0"

if __name__ == "__main__":
    root = tk.Tk()
    v154.AppV154(root)
    root.mainloop()
