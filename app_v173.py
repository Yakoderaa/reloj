# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v206 as v206

AppV173 = v206.AppV206

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
