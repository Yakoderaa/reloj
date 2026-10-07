# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v224 as v224

AppV173 = v224.AppV224

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
