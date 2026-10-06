# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v218 as v218

AppV173 = v218.AppV218

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
