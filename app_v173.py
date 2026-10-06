# Compatibility entrypoint for the existing Windows build workflow.
import tkinter as tk
import app_v186 as v186

AppV173 = v186.AppV186

if __name__=='__main__':
    root=tk.Tk();AppV173(root);root.mainloop()
