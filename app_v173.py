# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v215 as v215

AppV173 = v215.AppV215

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
