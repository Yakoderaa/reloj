# Compatibility entrypoint for the existing Windows build workflow.
import tkinter as tk
import app_v190 as v190

AppV173 = v190.AppV190

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
