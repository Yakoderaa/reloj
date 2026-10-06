# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v197 as v197

AppV173 = v197.AppV197

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
