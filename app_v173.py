# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v200 as v200

AppV173 = v200.AppV200

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
