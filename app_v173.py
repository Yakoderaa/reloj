# Compatibility entrypoint for the existing Windows build workflow.
import tkinter as tk
import app_v192 as v192

AppV173 = v192.AppV192

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
