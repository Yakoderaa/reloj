# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v202 as v202

AppV173 = v202.AppV202

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
