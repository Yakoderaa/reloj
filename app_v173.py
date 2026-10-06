# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v203 as v203

AppV173 = v203.AppV203

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
