# Compatibility entrypoint for the existing Windows build workflow.
import tkinter as tk
import app_v193 as v193

AppV173 = v193.AppV193

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
