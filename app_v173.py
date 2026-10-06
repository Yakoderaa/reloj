# Compatibility entrypoint for the existing Windows build workflow.
import tkinter as tk
import app_v191 as v191

AppV173 = v191.AppV191

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
