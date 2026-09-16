# 康复界面独立测试程序

本文件夹包含独立运行所需的 Python 源码、手势图片和启动入口。界面提取自原项目 `Huishou_2`，运行时不依赖原项目目录，可将整个文件夹复制到其他位置。

## 启动

使用已有的 Python + PyQt5 环境，双击 `start.bat`，或者在该环境终端执行：

```powershell
python main.py
```

如尚未安装 PyQt5，先在所用环境执行：

```powershell
python -m pip install -r requirements.txt
```

`start.bat` 默认使用 PATH 中的 `python`。需要指定环境时，可设置环境变量 `UI_TEST_PYTHON` 为该环境的 `python.exe` 完整路径，或直接使用该 Python 运行 `main.py`。

## 保留的四个页面

| 页面标识 | 界面 | 进入方式 |
| --- | --- | --- |
| `home` | 康复训练选择（提供的截图） | 启动直接显示 |
| `active` | 选择主动训练手势 | 点击主动训练 |
| `passive` | 选择被动训练手势 | 点击被动训练 |
| `mirror` | 镜像训练菜单 | 点击镜像训练 |

保留原有样式、手势阶段切换、手势选择和返回操作。主动／被动页面的“下一步”和镜像页面的“添加手势／康复训练”仅保留展示，不进入后续页面。所有返回按钮都回到本程序的康复训练选择页；起始页上的“返回主页”仍停留在起始页。

不包含登录、数据库、设备连接、实际训练、模型加载和语音识别。

## 后续接入语音

页面路由集中在 `app/window.py`，界面入口是 `main.py`。在 Qt 主线程中可以调用：

```python
window.show_page("active")
window.show_page("home")
```

若语音处理在工作线程中，通过信号请求切换，让 Qt 在界面线程中执行：

```python
window.navigate_requested.emit("active")
```

只接受上表的四种页面标识，未知标识保持当前页面。可监听 `window.page_changed` 获取切换后的页面标识。这里仅提供页面切换入口，具体语音处理由后续自行添加。

## 文件位置

- `main.py`、`start.bat`：启动入口。
- `app/window.py`：四个页面的创建和切换。
- `app/pages/`：训练选择、镜像菜单、主动／被动手势选择。
- `app/widgets/`：原有卡片、手势选择器及顶部栏。
- `app/theme.py`：原有界面样式及背景绘制。
- `app/gesture_config.py`：手势分组及图片映射。
- `assets/gestures/`：本程序使用的手势图片。

关闭窗口即可退出。程序不会自动安装依赖或修改原项目。
