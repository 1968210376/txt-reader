"""
TXT 小说朗读工具 (Edge-TTS版)
支持卡拉OK式文字跟随高亮
"""

import os
import glob
import asyncio
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import tempfile
import subprocess
import re

CHINESE_VOICES = [
    ("晓晓(女声)", "zh-CN-XiaoxiaoNeural"),
    ("云扬(男声)", "zh-CN-YunyangNeural"),
    ("云希(男声年轻)", "zh-CN-YunxiNeural"),
    ("晓艺(女声新闻)", "zh-CN-XiaoyiNeural"),
    ("云健(男声新闻)", "zh-CN-YunjianNeural"),
    ("晓秋(女声温柔)", "zh-CN-XiaoqiuNeural"),
]


class TxtReader:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("TXT 小说朗读工具")
        self.root.geometry("1000x800")
        
        self.folder_path = tk.StringVar()
        self.current_file_index = -1
        self.txt_files = []
        self.is_playing = False
        self.is_paused = False
        self.is_stopped = False
        self.speech_rate = tk.IntVar(value=0)
        self.current_content = ""
        self.selected_voice = tk.StringVar(value="晓晓(女声)")
        
        # 卡拉OK相关
        self.current_paragraph_index = 0
        self.paragraphs = []
        self.highlight_tag = "highlight"
        
        self.create_widgets()
        
    def create_widgets(self):
        # ===== 顶部：文件夹选择 =====
        top_frame = tk.Frame(self.root, padx=10, pady=10)
        top_frame.pack(fill=tk.X)
        
        tk.Label(top_frame, text="文件夹:", font=('Microsoft YaHei', 10)).pack(side=tk.LEFT)
        tk.Entry(top_frame, textvariable=self.folder_path, font=('Microsoft YaHei', 10), width=50).pack(side=tk.LEFT, padx=10)
        tk.Button(top_frame, text="浏览", command=self.select_folder, font=('Microsoft YaHei', 10), width=6).pack(side=tk.LEFT, padx=3)
        tk.Button(top_frame, text="加载", command=self.load_files, font=('Microsoft YaHei', 10), width=6).pack(side=tk.LEFT)
        
        # ===== 文件列表 =====
        list_frame = tk.Frame(self.root, padx=10)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(list_frame, text="文件列表:", font=('Microsoft YaHei', 10)).pack(anchor=tk.W)
        
        self.listbox = tk.Listbox(list_frame, font=('Microsoft YaHei', 10), height=6)
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        
        scrollbar = tk.Scrollbar(self.listbox, orient=tk.VERTICAL, command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)
        
        self.listbox.bind('<<ListboxSelect>>', self.on_select_file)
        self.listbox.bind('<Double-Button-1>', lambda e: self.toggle_play_pause())
        
        # ===== 内容显示（卡拉OK区域）=====
        content_frame = tk.Frame(self.root, padx=10)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(content_frame, text="朗读内容:", font=('Microsoft YaHei', 10)).pack(anchor=tk.W)
        
        # 使用Text组件显示内容，支持高亮
        self.text_content = tk.Text(content_frame, font=('Microsoft YaHei', 14), wrap=tk.WORD,
                                     bg='#1a1a2e', fg='#e0e0e0', insertbackground='white',
                                     selectbackground='#4CAF50', spacing1=5, spacing3=5)
        self.text_content.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 配置高亮样式
        self.text_content.tag_configure(self.highlight_tag, foreground='#00ff00', font=('Microsoft YaHei', 14, 'bold'))
        self.text_content.tag_configure("paragraph", foreground='#b0b0b0')
        
        content_scrollbar = tk.Scrollbar(self.text_content, orient=tk.VERTICAL, command=self.text_content.yview)
        content_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_content.config(yscrollcommand=content_scrollbar.set)
        
        # ===== 控制按钮 =====
        btn_frame = tk.Frame(self.root, padx=10, pady=15)
        btn_frame.pack(fill=tk.X)
        
        self.btn_prev = tk.Button(btn_frame, text="上一章", command=self.prev_chapter,
                                   bg='#4CAF50', fg='white', font=('Microsoft YaHei', 14, 'bold'), width=12, height=2)
        self.btn_prev.pack(side=tk.LEFT, padx=15, expand=True)
        
        self.btn_play = tk.Button(btn_frame, text="▶ 播放", command=self.toggle_play_pause,
                                   bg='#2196F3', fg='white', font=('Microsoft YaHei', 14, 'bold'), width=12, height=2)
        self.btn_play.pack(side=tk.LEFT, padx=15, expand=True)
        
        self.btn_next = tk.Button(btn_frame, text="下一章", command=self.next_chapter,
                                   bg='#4CAF50', fg='white', font=('Microsoft YaHei', 14, 'bold'), width=12, height=2)
        self.btn_next.pack(side=tk.LEFT, padx=15, expand=True)
        
        # ===== 进度条 =====
        progress_frame = tk.Frame(self.root, padx=10)
        progress_frame.pack(fill=tk.X)
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100, length=400)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.progress_label = tk.Label(progress_frame, text="0%", font=('Microsoft YaHei', 10), width=6)
        self.progress_label.pack(side=tk.LEFT)
        
        # ===== 设置区域 =====
        settings_frame = tk.Frame(self.root, padx=10, pady=5)
        settings_frame.pack(fill=tk.X)
        
        tk.Label(settings_frame, text="语音:", font=('Microsoft YaHei', 10)).pack(side=tk.LEFT)
        voice_options = [v[0] for v in CHINESE_VOICES]
        self.voice_combo = tk.OptionMenu(settings_frame, self.selected_voice, *voice_options, command=self.change_voice)
        self.voice_combo.config(font=('Microsoft YaHei', 10))
        self.voice_combo.pack(side=tk.LEFT, padx=10)
        tk.Label(settings_frame, text="语速:", font=('Microsoft YaHei', 10)).pack(side=tk.LEFT, padx=(20, 0))
        tk.Scale(settings_frame, from_=-50, to=50, orient=tk.HORIZONTAL, variable=self.speech_rate, 
                 length=150, font=('Microsoft YaHei', 9)).pack(side=tk.LEFT, padx=5)
        
        # ===== 快捷键提示 =====
        tk.Label(self.root, text="快捷键: 空格=播放/暂停 | ←=上一章 | →=下一章 | Esc=停止",
                 font=('Microsoft YaHei', 9), fg='gray').pack(pady=5)
        
        # ===== 状态栏 =====
        self.status_var = tk.StringVar(value="就绪")
        tk.Label(self.root, textvariable=self.status_var, font=('Microsoft YaHei', 10), 
                 bg='#f0f0f0', relief=tk.SUNKEN, padx=10, pady=5).pack(fill=tk.X, padx=10, pady=5)
        
        # 绑定快捷键
        self.root.bind('<space>', lambda e: self.toggle_play_pause())
        self.root.bind('<Left>', lambda e: self.prev_chapter())
        self.root.bind('<Right>', lambda e: self.next_chapter())
        self.root.bind('<Escape>', lambda e: self.stop_reading())
        
    def change_voice(self, selection):
        idx = [v[0] for v in CHINESE_VOICES].index(selection)
        self.selected_voice.set(CHINESE_VOICES[idx][1])
                
    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path.set(folder)
            self.load_files()
            
    def load_files(self):
        folder = self.folder_path.get()
        if not folder:
            messagebox.showwarning("警告", "请先选择文件夹！")
            return
        if not os.path.isdir(folder):
            messagebox.showerror("错误", "文件夹不存在！")
            return
            
        self.txt_files = sorted(glob.glob(os.path.join(folder, "*.txt")))
        
        if not self.txt_files:
            messagebox.showinfo("提示", "该文件夹下没有txt文件！")
            return
            
        self.listbox.delete(0, tk.END)
        for i, filepath in enumerate(self.txt_files):
            self.listbox.insert(tk.END, f"{i+1}. {os.path.basename(filepath)}")
            
        self.status_var.set(f"已加载 {len(self.txt_files)} 个文件")
        self.current_file_index = -1
        
    def on_select_file(self, event):
        selection = self.listbox.curselection()
        if selection:
            self.current_file_index = selection[0]
            self.preview_file()
            
    def preview_file(self):
        if 0 <= self.current_file_index < len(self.txt_files):
            filepath = self.txt_files[self.current_file_index]
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 分段处理
                self.paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
                self.current_content = content
                
                # 显示内容
                self.display_content()
                self.status_var.set(f"当前: {os.path.basename(filepath)}")
            except Exception as e:
                messagebox.showerror("错误", f"读取文件失败: {e}")
    
    def display_content(self, highlight_index=-1):
        """显示内容，支持高亮当前段落"""
        self.text_content.config(state=tk.NORMAL)
        self.text_content.delete('1.0', tk.END)
        
        for i, para in enumerate(self.paragraphs):
            if i == highlight_index:
                self.text_content.insert(tk.END, para + '\n\n', self.highlight_tag)
            else:
                self.text_content.insert(tk.END, para + '\n\n', "paragraph")
        
        self.text_content.config(state=tk.DISABLED)
        
        # 滚动到高亮段落
        if highlight_index >= 0:
            self.scroll_to_paragraph(highlight_index)
    
    def scroll_to_paragraph(self, index):
        """滚动到指定段落"""
        # 计算大致位置
        lines_before = sum(len(self.paragraphs[i]) // 50 + 2 for i in range(index))
        self.text_content.see(f'{lines_before + 1}.0')
        self.text_content.see(f'{lines_before + 3}.0')
                
    def toggle_play_pause(self):
        """播放/暂停切换"""
        if not self.txt_files:
            messagebox.showwarning("警告", "请先加载文件！")
            return
        
        if self.is_playing:
            # 正在播放，执行暂停
            self.is_paused = True
            self.is_playing = False
            self.btn_play.config(text="▶ 播放")
            self.status_var.set("已暂停")
        else:
            if self.is_paused:
                # 从暂停恢复
                self.is_paused = False
                self.is_playing = True
                self.btn_play.config(text="⏸ 暂停")
                self.status_var.set(f"正在朗读: {os.path.basename(self.txt_files[self.current_file_index])}")
            else:
                # 新播放
                if self.current_file_index < 0:
                    self.current_file_index = 0
                    self.listbox.selection_set(0)
                    self.preview_file()
                self.current_paragraph_index = 0
                self.start_reading()
        
    def start_reading(self):
        if not (0 <= self.current_file_index < len(self.txt_files)):
            return
        self.stop_reading()
        self.is_playing = True
        self.is_paused = False
        self.is_stopped = False
        
        self.status_var.set(f"正在朗读: {os.path.basename(self.txt_files[self.current_file_index])}")
        self.btn_play.config(text="⏸ 暂停")
        
        threading.Thread(target=self.read_content_thread, daemon=True).start()
        
    def read_content_thread(self):
        """朗读内容线程 - 卡拉OK式"""
        for i, para in enumerate(self.paragraphs):
            if self.is_stopped:
                break
            
            self.current_paragraph_index = i
            
            # 更新高亮
            self.root.after(0, lambda idx=i: self.highlight_paragraph(idx))
            
            while self.is_paused and not self.is_stopped:
                import time
                time.sleep(0.1)
            
            if self.is_stopped:
                break
            
            try:
                self.speak_paragraph(para)
            except Exception as e:
                print(f"朗读出错: {e}")
                continue
            
            # 更新进度
            progress = ((i + 1) / len(self.paragraphs)) * 100
            self.root.after(0, lambda p=progress: self.update_progress(p))
                
        if not self.is_stopped:
            self.root.after(0, self.on_reading_complete)
    
    def highlight_paragraph(self, index):
        """高亮显示当前段落"""
        self.display_content(highlight_index=index)
            
    def update_progress(self, progress):
        """更新进度条"""
        self.progress_var.set(progress)
        self.progress_label.config(text=f"{int(progress)}%")
            
    def speak_paragraph(self, text):
        import edge_tts
        if not text.strip():
            return
            
        voice = CHINESE_VOICES[[v[0] for v in CHINESE_VOICES].index(self.selected_voice.get())][1]
        rate = f"{'+' if self.speech_rate.get() >= 0 else ''}{self.speech_rate.get()}%"
        
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            temp_path = tmp.name
            
        try:
            async def generate():
                communicate = edge_tts.Communicate(text, voice, rate=rate)
                await communicate.save(temp_path)
            asyncio.run(generate())
            if os.path.exists(temp_path):
                self.play_mp3(temp_path)
        finally:
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
    def play_mp3(self, mp3_path):
        import time
        ps_cmd = f'''
        Add-Type -AssemblyName presentationCore
        $player = New-Object System.Windows.Media.MediaPlayer
        $player.Open("{mp3_path.replace(os.sep, '/')}")
        $player.Play()
        while ($player.Position -lt $player.NaturalDuration.TimeSpan -and $player.HasAudio) {{
            Start-Sleep -Milliseconds 100
        }}
        $player.Close()
        '''
        process = subprocess.Popen(['powershell', '-Command', ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        while process.poll() is None:
            if self.is_stopped:
                process.terminate()
                break
            while self.is_paused and not self.is_stopped:
                time.sleep(0.1)
            time.sleep(0.1)
            
    def on_reading_complete(self):
        self.is_playing = False
        self.is_paused = False
        self.btn_play.config(text="▶ 播放")
        self.status_var.set("朗读完成")
        self.update_progress(100)
        self.display_content(-1)
        
    def stop_reading(self):
        self.is_stopped = True
        self.is_playing = False
        self.is_paused = False
        self.btn_play.config(text="▶ 播放")
        self.status_var.set("已停止")
        self.update_progress(0)
        
    def prev_chapter(self):
        if self.current_file_index > 0:
            self.stop_reading()
            self.current_file_index -= 1
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.current_file_index)
            self.listbox.see(self.current_file_index)
            self.preview_file()
            self.update_progress(0)
        else:
            self.status_var.set("已经是第一章了！")
            
    def next_chapter(self):
        if self.current_file_index < len(self.txt_files) - 1:
            self.stop_reading()
            self.current_file_index += 1
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.current_file_index)
            self.listbox.see(self.current_file_index)
            self.preview_file()
            self.update_progress(0)
        else:
            self.status_var.set("已经是最后一章了！")
            
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    TxtReader().run()
