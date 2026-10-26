# 粘贴历史

Windows 剪贴板历史工具：后台监听复制内容，用快捷键呼出记录并重新复制。

## 使用

1. 运行 `粘贴历史.exe`，或先执行 `build.bat` 打包。
2. 程序会进入系统托盘，关闭窗口后仍在后台运行。
3. 默认快捷键：`Ctrl+Shift+V`（若被占用则尝试 `Ctrl+Alt+V`）。
4. 可在窗口或托盘菜单中勾选「开机启动」。

历史记录保存在 `%APPDATA%\PasteHistory\`。

## 从源码运行

```bat
python -m pip install -r requirements.txt
pythonw main.py
```

仅需 Python 3，以及 `requirements.txt` 中的托盘与打包依赖。
