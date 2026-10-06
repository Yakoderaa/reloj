# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v213 as v213

AppV173 = v213.AppV213

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
