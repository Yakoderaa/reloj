# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v207 as v207

AppV173 = v207.AppV207

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
