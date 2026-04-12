import tkinter as tk

root = tk.Tk()
root.title("测试窗口")
root.geometry("800x600")

# 简单按钮测试
frame = tk.Frame(root)
frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

btn1 = tk.Button(frame, text="上一章", bg='#4CAF50', fg='white', font=('Arial', 14), width=12, height=2)
btn1.pack(side=tk.LEFT, padx=10)

btn2 = tk.Button(frame, text="朗读", bg='#2196F3', fg='white', font=('Arial', 14), width=12, height=2)
btn2.pack(side=tk.LEFT, padx=10)

btn3 = tk.Button(frame, text="暂停", bg='#FF9800', fg='white', font=('Arial', 14), width=12, height=2)
btn3.pack(side=tk.LEFT, padx=10)

btn4 = tk.Button(frame, text="停止", bg='#f44336', fg='white', font=('Arial', 14), width=12, height=2)
btn4.pack(side=tk.LEFT, padx=10)

btn5 = tk.Button(frame, text="下一章", bg='#4CAF50', fg='white', font=('Arial', 14), width=12, height=2)
btn5.pack(side=tk.LEFT, padx=10)

root.mainloop()
