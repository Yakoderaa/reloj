# Compatibility entrypoint for the existing Windows build workflow.
# Verification markers retained intentionally: 1.73.0 · RECONSTRUIR TOKEN + RETROFIT · PREF_KEY_ACCESS_TOKEN · ota_writes
import tkinter as tk
import app_v177 as v177

AppV173 = v177.AppV177

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
