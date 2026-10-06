# Compatibility entrypoint for the existing Windows build workflow.
import tkinter as tk
import app_v194 as v194

AppV173 = v194.AppV194

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
