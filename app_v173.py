# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v216 as v216

AppV173 = v216.AppV216

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
