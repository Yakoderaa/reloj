# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v208 as v208

AppV173 = v208.AppV208

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
