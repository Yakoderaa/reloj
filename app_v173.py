# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v214 as v214

AppV173 = v214.AppV214

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
