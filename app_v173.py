# Compatibility entrypoint for the existing Windows build workflow.
import tkinter as tk
import app_v185 as v185

AppV173 = v185.AppV185

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
