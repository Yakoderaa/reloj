# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v217 as v217

AppV173 = v217.AppV217

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
