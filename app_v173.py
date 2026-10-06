# Compatibility entrypoint for the existing Windows build workflow.
import tkinter as tk
import app_v195 as v195

AppV173 = v195.AppV195

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
