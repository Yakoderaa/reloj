# Compatibility entrypoint for the existing Windows build workflow.
import tkinter as tk
import app_v187 as v187

AppV173 = v187.AppV187

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
