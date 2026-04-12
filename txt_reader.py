"""
TXT 小说朗读工具 (Edge-TTS版)
"""

import os
import glob
import asyncio
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import tempfile
import subprocess

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
        self.root.geometry("900x700")
        
        self.folder_path = tk.StringVar()
        self.current_file_index = -1
        self.txt_files = []
        self.is_playing = False
        self.is_paused = False
        self.is_stopped = False
        self.speech_rate = tk.IntVar(value=0)
        self.current_content = ""
        self.selected_voice = tk.StringVar(value="晓晓(女声)")  # 默认晓晓
        
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
        
        self.listbox = tk.Listbox(list_frame, font=('Microsoft YaHei', 10), height=10)
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        
        scrollbar = tk.Scrollbar(self.listbox, orient=tk.VERTICAL, command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)
        
        self.listbox.bind('<<ListboxSelect>>', self.on_select_file)
        self.listbox.bind('<Double-Button-1>', lambda e: self.play_selected())
        
        # ===== 内容预览 =====
        preview_frame = tk.Frame(self.root, padx=10)
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(preview_frame, text="内容预览:", font=('Microsoft YaHei', 10)).pack(anchor=tk.W)
        
        self.text_content = tk.Text(preview_frame, font=('Microsoft YaHei', 10), height=8, wrap=tk.WORD)
        self.text_content.pack(fill=tk.BOTH, expand=True, pady=5)
        
        preview_scrollbar = tk.Scrollbar(self.text_content, orient=tk.VERTICAL, command=self.text_content.yview)
        preview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_content.config(yscrollcommand=preview_scrollbar.set)
        
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
        tk.Label(self.root, text="快捷键: 空格=暂停 | ←=上一章 | →=下一章 | Esc=停止",
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
                self.text_content.delete('1.0', tk.END)
                self.text_content.insert('1.0', content[:1500])
                self.current_content = content
                self.status_var.set(f"当前: {os.path.basename(filepath)}")
            except Exception as e:
                messagebox.showerror("错误", f"读取文件失败: {e}")
                
    def play_selected(self):
        if not self.txt_files:
            messagebox.showwarning("警告", "请先加载文件！")
            return
        if self.current_file_index < 0:
            self.current_file_index = 0
            self.listbox.selection_set(0)
            self.preview_file()
        self.start_reading()
    
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
            # 未播放，执行播放
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
        import edge_tts
        
        filepath = self.txt_files[self.current_file_index]
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return
        
        paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
        
        for para in paragraphs:
            if self.is_stopped:
                break
            while self.is_paused and not self.is_stopped:
                import time
                time.sleep(0.1)
            if self.is_stopped:
                break
            try:
                self.speak_paragraph(para)
            except:
                continue
                
        if not self.is_stopped:
            self.root.after(0, self.on_reading_complete)
            
    def speak_paragraph(self, text):
        import edge_tts
        if not text.strip():
            return
            
        voice = self.selected_voice.get()
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
        self.status_var.set(f"朗读完成")
        
    def stop_reading(self):
        self.is_stopped = True
        self.is_playing = False
        self.is_paused = False
        self.btn_play.config(text="▶ 播放")
        self.status_var.set("已停止")
        
    def prev_chapter(self):
        if self.current_file_index > 0:
            self.stop_reading()
            self.current_file_index -= 1
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.current_file_index)
            self.listbox.see(self.current_file_index)
            self.preview_file()
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
        else:
            self.status_var.set("已经是最后一章了！")
            
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    TxtReader().run()
