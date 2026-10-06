# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v212 as v212

AppV173 = v212.AppV212

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
