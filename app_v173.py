# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v209 as v209

AppV173 = v209.AppV209

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
