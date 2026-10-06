# Compatibility entrypoint for the existing Windows build workflow.
import tkinter as tk
import app_v184 as v184

AppV173 = v184.AppV184

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
