# TXT 小说朗读工具

一个简单易用的小说朗读工具，支持电脑端和手机端使用。

## 功能特点

- 支持选择文件夹批量加载txt文件
- 上一章/下一章快速切换
- 暂停/继续/停止控制
- 语速和音调调节
- 多种中文语音选择
- 支持手机浏览器使用

## 文件说明

| 文件 | 说明 |
|------|------|
| `index.html` | 网页版，可在手机浏览器中使用 |
| `txt_reader.py` | Python桌面版，功能更完善 |
| `reader.bat` | Windows批处理版，简单轻量 |

## 使用方法

### 网页版 (推荐手机使用)

直接用浏览器打开 `index.html` 文件即可使用。

### Python桌面版

```bash
# 安装依赖
pip install edge-tts pygame

# 运行
python txt_reader.py
```

### Windows批处理版

双击 `reader.bat` 运行。

## 在线访问

部署后可通过链接在线访问。
