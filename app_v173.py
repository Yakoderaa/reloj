# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v199 as v199

AppV173 = v199.AppV199

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
