# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v223 as v223

AppV173 = v223.AppV223

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
