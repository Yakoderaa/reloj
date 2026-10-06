# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v205 as v205

AppV173 = v205.AppV205

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
