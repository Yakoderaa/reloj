# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v198 as v198

AppV173 = v198.AppV198

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
