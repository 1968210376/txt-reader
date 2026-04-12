"""
TXT 小说朗读工具 (Edge-TTS版)
功能：朗读指定文件夹下的txt文件，支持上下章切换、暂停、变速等
使用微软Edge在线语音，效果接近真人
"""

import os
import sys
import glob
import asyncio
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import tempfile
import subprocess

# 中文语音选项
CHINESE_VOICES = [
    ("晓晓 (女声, 自然)", "zh-CN-XiaoxiaoNeural"),
    ("云扬 (男声, 自然)", "zh-CN-YunyangNeural"),
    ("云希 (男声, 年轻)", "zh-CN-YunxiNeural"),
    ("晓艺 (女声, 新闻)", "zh-CN-XiaoyiNeural"),
    ("云健 (男声, 新闻)", "zh-CN-YunjianNeural"),
    ("晓晓-多风格 (女声)", "zh-CN-XiaoxiaoNeural"),
    ("晓秋 (女声, 温柔)", "zh-CN-XiaoqiuNeural"),
    ("晓睿 (女声, 活泼)", "zh-CN-XiaoruiNeural"),
    ("晓双 (女声, 儿童故事)", "zh-CN-XiaoshuangNeural"),
    ("晓颜 (女声, 客服)", "zh-CN-XiaoyanNeural"),
    ("晓悠 (女声, 儿童)", "zh-CN-XiaoyouNeural"),
    ("云野 (男声, 广播)", "zh-CN-YunyeNeural"),
]


class TxtReader:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("TXT 小说朗读工具 (Edge真人语音版)")
        self.root.geometry("900x750")
        self.root.resizable(True, True)
        
        # 状态变量
        self.folder_path = tk.StringVar()
        self.current_file_index = -1
        self.txt_files = []
        self.is_playing = False
        self.is_paused = False
        self.is_stopped = False
        self.speech_rate = tk.IntVar(value=0)
        self.current_content = ""
        self.selected_voice = tk.StringVar(value=CHINESE_VOICES[0][1])
        self.temp_file = None
        
        # 创建界面
        self.create_widgets()
        
    def create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 文件夹选择区域
        frame_folder = ttk.LabelFrame(main_frame, text="文件夹路径", padding=10)
        frame_folder.pack(fill=tk.X, pady=5)
        
        entry_frame = ttk.Frame(frame_folder)
        entry_frame.pack(fill=tk.X)
        ttk.Entry(entry_frame, textvariable=self.folder_path).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(entry_frame, text="浏览", command=self.select_folder, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Button(entry_frame, text="加载文件", command=self.load_files, width=10).pack(side=tk.LEFT)
        
        # 文件列表区域
        frame_list = ttk.LabelFrame(main_frame, text="文件列表", padding=10)
        frame_list.pack(fill=tk.BOTH, expand=True, pady=5)
        
        list_frame = ttk.Frame(frame_list)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=('Microsoft YaHei', 10))
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)
        
        self.listbox.bind('<<ListboxSelect>>', self.on_select_file)
        self.listbox.bind('<Double-Button-1>', lambda e: self.play_selected())
        
        # 内容预览区域
        frame_content = ttk.LabelFrame(main_frame, text="内容预览", padding=10)
        frame_content.pack(fill=tk.BOTH, expand=True, pady=5)
        
        content_frame = ttk.Frame(frame_content)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        self.text_content = tk.Text(content_frame, font=('Microsoft YaHei', 10), wrap=tk.WORD, height=10)
        self.text_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar_content = ttk.Scrollbar(content_frame, command=self.text_content.yview)
        scrollbar_content.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_content.config(yscrollcommand=scrollbar_content.set)
        
        # 控制按钮区域
        frame_control = ttk.LabelFrame(main_frame, text="控制面板", padding=15)
        frame_control.pack(fill=tk.X, pady=5)
        
        # 第一行：导航按钮
        btn_frame = ttk.Frame(frame_control)
        btn_frame.pack(fill=tk.X, pady=10)
        
        for i in range(5):
            btn_frame.columnconfigure(i, weight=1, uniform='btn')
        
        btn_font = ('Microsoft YaHei', 12)
        
        self.btn_prev = tk.Button(btn_frame, text="上一章", command=self.prev_chapter, 
                                   font=btn_font, height=2, bg='#4CAF50', fg='white')
        self.btn_prev.grid(row=0, column=0, padx=8, pady=5, sticky='ew')
        
        self.btn_play = tk.Button(btn_frame, text="开始朗读", command=self.play_selected,
                                   font=btn_font, height=2, bg='#2196F3', fg='white')
        self.btn_play.grid(row=0, column=1, padx=8, pady=5, sticky='ew')
        
        self.btn_pause = tk.Button(btn_frame, text="暂停 / 继续", command=self.toggle_pause,
                                    font=btn_font, height=2, bg='#FF9800', fg='white')
        self.btn_pause.grid(row=0, column=2, padx=8, pady=5, sticky='ew')
        
        self.btn_stop = tk.Button(btn_frame, text="停止", command=self.stop_reading,
                                   font=btn_font, height=2, bg='#f44336', fg='white')
        self.btn_stop.grid(row=0, column=3, padx=8, pady=5, sticky='ew')
        
        self.btn_next = tk.Button(btn_frame, text="下一章", command=self.next_chapter,
                                   font=btn_font, height=2, bg='#4CAF50', fg='white')
        self.btn_next.grid(row=0, column=4, padx=8, pady=5, sticky='ew')
        
        # 第二行：语速和声音控制
        control_frame = ttk.Frame(frame_control)
        control_frame.pack(fill=tk.X, pady=10)
        
        # 声音选择 (放在前面，更重要)
        voice_frame = ttk.Frame(control_frame)
        voice_frame.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(voice_frame, text="语音:", font=('Microsoft YaHei', 11)).pack(side=tk.LEFT)
        self.voice_combo = ttk.Combobox(voice_frame, textvariable=self.selected_voice, width=25, state='readonly')
        self.voice_combo.pack(side=tk.LEFT, padx=10)
        # 设置语音选项
        voice_display = [f"{v[0]}" for v in CHINESE_VOICES]
        self.voice_combo['values'] = voice_display
        self.voice_combo.current(0)
        self.voice_combo.bind('<<ComboboxSelected>>', self.change_voice)
        
        # 语速控制
        speed_frame = ttk.Frame(control_frame)
        speed_frame.pack(side=tk.LEFT, padx=20)
        
        ttk.Label(speed_frame, text="语速:", font=('Microsoft YaHei', 11)).pack(side=tk.LEFT)
        ttk.Scale(speed_frame, from_=-50, to=50, variable=self.speech_rate, 
                  orient=tk.HORIZONTAL, length=150, command=self.update_rate).pack(side=tk.LEFT, padx=10)
        self.rate_label = ttk.Label(speed_frame, text="0%", font=('Microsoft YaHei', 11, 'bold'), width=5)
        self.rate_label.pack(side=tk.LEFT)
        
        # 快捷键提示
        hint_frame = ttk.Frame(frame_control)
        hint_frame.pack(fill=tk.X, pady=5)
        ttk.Label(hint_frame, text="快捷键: [空格] 暂停/继续 | [←] 上一章 | [→] 下一章 | [Esc] 停止", 
                  font=('Microsoft YaHei', 10), foreground='gray').pack()
        
        # 状态栏
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=5)
        self.status_var = tk.StringVar(value="就绪 - 请选择文件夹并加载文件 (使用微软Edge真人语音)")
        ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN, 
                  font=('Microsoft YaHei', 10), padding=5).pack(fill=tk.X)
        
        # 绑定快捷键
        self.root.bind('<space>', lambda e: self.toggle_pause())
        self.root.bind('<Left>', lambda e: self.prev_chapter())
        self.root.bind('<Right>', lambda e: self.next_chapter())
        self.root.bind('<Escape>', lambda e: self.stop_reading())
        
    def change_voice(self, event=None):
        """切换声音"""
        idx = self.voice_combo.current()
        if 0 <= idx < len(CHINESE_VOICES):
            self.selected_voice.set(CHINESE_VOICES[idx][1])
                
    def select_folder(self):
        """选择文件夹"""
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path.set(folder)
            self.load_files()
            
    def load_files(self):
        """加载txt文件"""
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
            filename = os.path.basename(filepath)
            self.listbox.insert(tk.END, f"{i+1}. {filename}")
            
        self.status_var.set(f"已加载 {len(self.txt_files)} 个文件 - 双击或选择后点击朗读")
        self.current_file_index = -1
        
    def on_select_file(self, event):
        """选择文件事件"""
        selection = self.listbox.curselection()
        if selection:
            self.current_file_index = selection[0]
            self.preview_file()
            
    def preview_file(self):
        """预览文件内容"""
        if 0 <= self.current_file_index < len(self.txt_files):
            filepath = self.txt_files[self.current_file_index]
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                preview = content[:1500] + "..." if len(content) > 1500 else content
                self.text_content.delete('1.0', tk.END)
                self.text_content.insert('1.0', preview)
                self.current_content = content
                self.status_var.set(f"当前: {os.path.basename(filepath)}")
            except Exception as e:
                messagebox.showerror("错误", f"读取文件失败: {e}")
                
    def play_selected(self):
        """朗读选中的文件"""
        if not self.txt_files:
            messagebox.showwarning("警告", "请先加载文件！")
            return
            
        if self.current_file_index < 0:
            self.current_file_index = 0
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(0)
            self.listbox.see(0)
            self.preview_file()
            
        self.start_reading()
        
    def start_reading(self):
        """开始朗读"""
        if not (0 <= self.current_file_index < len(self.txt_files)):
            return
            
        self.stop_reading()
        self.is_playing = True
        self.is_paused = False
        self.is_stopped = False
        
        filepath = self.txt_files[self.current_file_index]
        self.status_var.set(f"正在朗读: {os.path.basename(filepath)}")
        self.btn_play.config(text="朗读中...")
        
        thread = threading.Thread(target=self.read_content_thread, daemon=True)
        thread.start()
        
    def read_content_thread(self):
        """朗读内容线程"""
        import edge_tts
        
        filepath = self.txt_files[self.current_file_index]
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"读取文件失败: {e}"))
            return
        
        # 分段处理，支持暂停
        paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
        
        for para in paragraphs:
            if self.is_stopped:
                break
            while self.is_paused and not self.is_stopped:
                import time
                time.sleep(0.1)
            if self.is_stopped:
                break
            
            # 使用edge-tts生成音频并播放
            try:
                self.speak_paragraph(para)
            except Exception as e:
                print(f"朗读出错: {e}")
                continue
                
        if not self.is_stopped:
            self.root.after(0, self.on_reading_complete)
            
    def speak_paragraph(self, text):
        """朗读单个段落"""
        import edge_tts
        
        if not text.strip():
            return
            
        # 获取当前选择的语音
        voice = self.selected_voice.get()
        rate = f"{'+' if self.speech_rate.get() >= 0 else ''}{self.speech_rate.get()}%"
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            temp_path = tmp.name
            
        try:
            # 异步生成语音
            async def generate():
                communicate = edge_tts.Communicate(text, voice, rate=rate)
                await communicate.save(temp_path)
            
            asyncio.run(generate())
            
            # 使用系统播放器播放
            if os.path.exists(temp_path):
                # Windows使用媒体播放器静默播放
                import winsound
                # 将mp3转换为wav或使用其他方式播放
                # 使用Windows Media Player
                self.play_mp3(temp_path)
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
    def play_mp3(self, mp3_path):
        """播放MP3文件"""
        # 使用Windows Media Player播放
        import time
        
        # 创建播放器
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(mp3_path)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                if self.is_stopped:
                    pygame.mixer.music.stop()
                    break
                while self.is_paused and not self.is_stopped:
                    time.sleep(0.1)
                time.sleep(0.05)
                
            pygame.mixer.quit()
        except ImportError:
            # 没有pygame，使用PowerShell播放
            ps_cmd = f'''
            Add-Type -AssemblyName presentationCore
            $player = New-Object System.Windows.Media.MediaPlayer
            $player.Open("{mp3_path}")
            $player.Play()
            Start-Sleep -Milliseconds 100
            while ($player.Position -lt $player.NaturalDuration.TimeSpan -and $player.HasAudio) {{
                Start-Sleep -Milliseconds 100
            }}
            $player.Close()
            '''
            subprocess.run(['powershell', '-Command', ps_cmd], capture_output=True)
            
    def on_reading_complete(self):
        """朗读完成回调"""
        self.is_playing = False
        self.is_paused = False
        self.btn_play.config(text="开始朗读")
        self.status_var.set(f"朗读完成: {os.path.basename(self.txt_files[self.current_file_index])}")
        
    def toggle_pause(self):
        """暂停/继续"""
        if not self.is_playing:
            return
            
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.status_var.set("已暂停 - 按空格或点击按钮继续")
            self.btn_pause.config(text="点击继续")
        else:
            self.status_var.set("继续朗读...")
            self.btn_pause.config(text="暂停 / 继续")
                
    def stop_reading(self):
        """停止朗读"""
        self.is_stopped = True
        self.is_playing = False
        self.is_paused = False
        self.btn_play.config(text="开始朗读")
        self.btn_pause.config(text="暂停 / 继续")
        self.status_var.set("已停止")
        
    def prev_chapter(self):
        """上一章"""
        if self.current_file_index > 0:
            self.stop_reading()
            self.current_file_index -= 1
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.current_file_index)
            self.listbox.see(self.current_file_index)
            self.preview_file()
            if self.is_playing:
                self.start_reading()
        else:
            messagebox.showinfo("提示", "已经是第一章了！")
            
    def next_chapter(self):
        """下一章"""
        if self.current_file_index < len(self.txt_files) - 1:
            self.stop_reading()
            self.current_file_index += 1
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.current_file_index)
            self.listbox.see(self.current_file_index)
            self.preview_file()
            if self.is_playing:
                self.start_reading()
        else:
            messagebox.showinfo("提示", "已经是最后一章了！")
            
    def update_rate(self, value):
        """更新语速"""
        rate = int(float(value))
        self.speech_rate.set(rate)
        self.rate_label.config(text=f"{rate}%")
            
    def run(self):
        """运行程序"""
        self.root.mainloop()


if __name__ == "__main__":
    app = TxtReader()
    app.run()
