# Compatibility entrypoint for the existing Windows build workflow.
import tkinter as tk
import app_v188 as v188

AppV173 = v188.AppV188

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
