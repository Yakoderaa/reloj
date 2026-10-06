# Compatibility entrypoint for the existing Windows build workflow.
import tkinter as tk
import app_v189 as v189

AppV173 = v189.AppV189

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
