# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v210 as v210

AppV173 = v210.AppV210

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
