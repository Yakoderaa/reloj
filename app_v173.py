# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v221 as v221

AppV173 = v221.AppV221

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
