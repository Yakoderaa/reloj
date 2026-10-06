# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v204 as v204

AppV173 = v204.AppV204

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
