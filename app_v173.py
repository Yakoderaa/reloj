# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v196 as v196

AppV173 = v196.AppV196

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
