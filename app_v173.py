# Compatibility entrypoint for the existing build workflow.
import tkinter as tk
import app_v201 as v201

AppV173 = v201.AppV201

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
