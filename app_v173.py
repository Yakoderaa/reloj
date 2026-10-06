# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v219 as v219

AppV173 = v219.AppV219

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
