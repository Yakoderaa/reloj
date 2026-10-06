# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v211 as v211

AppV173 = v211.AppV211

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
