# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v222 as v222

AppV173 = v222.AppV222

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
