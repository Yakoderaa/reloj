# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v220 as v220

AppV173 = v220.AppV220

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
