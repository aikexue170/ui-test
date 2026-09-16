# AGEN.md — 本仓库的 AI 改动记录

> 面向：接手本项目的开发者，以及**下一个在本仓库工作的 AI Agent**。
> 改动时间：2026-09-16
> 改动者：AI Agent（DeepSeek Harness），在用户逐步验收下完成。
> 阅读顺序建议：先读本文件 → 再读 `InteractionUITest/项目导航.md`（结构导航）→ 需要改 AI 部分时读 `InteractionUITest/AI操控方案.md`（设计与实测数据）。

---

## 0. 一句话总结

原本是一个**只有 4 个页面的 PyQt5 静态界面壳**（点击按钮切页，不做任何实际业务）。
本次给它加了一层**语音操控**：用户说一句话 → 本地 LLM 判断当前页面上该点哪个控件 → 自动点一次。
整个过程不依赖云服务，模型和语音识别全部跑在本机。

---

## 1. 改动前的原始状态

| | |
|---|---|
| 位置 | `InteractionUITest/`（主）、`TTS-LLM-STT/`（语音实验脚本） |
| 技术栈 | Python 3.12 + PyQt5 5.15.10，没有 C++ Qt，没有 `.ui`/`.qrc` 文件，界面全是手写代码 |
| 规模 | 1188 行 Python |
| 能力 | 4 个页面（首页 / 主动训练手势选择 / 被动训练手势选择 / 镜像训练菜单）、手势图片卡片、分期 Tab 切换、返回跳转 |
| 没有的东西 | 登录、数据库、设备连接、模型加载、语音识别、任何 AI |
| 版本控制 | **不是 git 仓库**，没有任何 git 配置 |

原始代码里唯一为将来预留的接口是 `app/window.py` 的 `navigate_requested` 信号（注释写着"给将来的语音线程用"）。

---

## 2. Agent 做了什么

### 2.1 新增：`InteractionUITest/app/ai/`（9 个文件，1296 行）

| 文件 | 行数 | 职责 |
|---|---|---|
| `config.py` | 86 | 全部可调参数，均可用环境变量覆盖 |
| `actions.py` | 158 | **动作注册表**：4 个页面共 63 个可点动作，每个带 id / 中文标签 / 给模型看的描述 / 执行回调 / 正则别名 |
| `llm.py` | 124 | 调用本地 llama-server 的 OpenAI 兼容接口，用**工具调用**选出一个动作 id（只用标准库 `urllib`，不引入 requests） |
| `router.py` | 229 | 意图路由：正则快速通道 → LLM → 回表校验 → 执行；含 QThread 生命周期铁律 |
| `voice.py` | 165 | Qwen3-ASR 录音识别工作线程（改造自 `TTS-LLM-STT/stt_demo.py`） |
| `overlay.py` | 139 | 窗口底部的悬浮控制条（🎤 按钮 + 状态反馈） |
| `server.py` | 210 | **自动拉起/探测 llama-server**，省掉手动敲启动指令 |
| `controller.py` | 163 | 把上面几件装配到窗口上 |
| `__init__.py` | 22 | 包说明 + 延迟导入 |

### 2.2 修改的既有文件（3 个，都是小改）

| 文件 | 改了什么 |
|---|---|
| `app/window.py` | 末尾挂 `AiController`；新增 `closeEvent` 调 `ai.shutdown()` 收线程 |
| `app/widgets/gesture_cards.py` | 新增公开方法 `GestureStageSelector.set_gesture_selected()`，供自动化"等价于点一下卡片"地勾选手势 |
| `app/gesture_config.py` | 新增 `group_of_gesture(name)` 助手函数 |

### 2.3 新增文档（2 个，672 行）

| 文件 | 内容 |
|---|---|
| `InteractionUITest/项目导航.md` | 359 行。面向不熟悉 Qt 的读者：文件职责表、页面跳转图、6 个必懂的 Qt 概念、三种画界面的方式、改动速查表、AI 模块使用说明、踩坑记录 |
| `InteractionUITest/AI操控方案.md` | 313 行。方案调研与设计：5 种实现方式的**实测对比数据**、动作注册表设计、Qt 落地细节、环境安装 |

### 2.4 顺带做掉的环境工作

- 在 `~/miniconda3/envs/ai` 里装了 `PyQt5==5.15.10`（该环境原本只有它没有 PyQt5，而 torch/transformers 只在这个环境里）。
  安装前做过 `pip install --dry-run`，确认只新增 3 个包、无依赖冲突、且该环境没有 opencv（Linux 上 Qt 插件加载失败的头号元凶）。

---

## 3. 最终能力

```
用户说话
   ↓
VoiceWorker (QThread)  Qwen3-ASR 0.6B        ← ai 环境的 torch
   ↓  pyqtSignal(str)  跨线程安全
IntentRouter（主线程）
   ├─(1) 正则快速通道：fast=True 的动作别名命中 → 0.14ms 出结果，不调模型
   ├─(2) 未命中 → LlmWorker (QThread) → llama-server 工具调用
   │        tools=[{click_button: {action_id: <当前页动作 id 枚举>}}]
   ├─(3) 回表校验：id 必须在"当前页动作表"里，否则丢弃
   └─(4) 主线程执行 action["run"]()
   ↓
LlamaServerManager：启动时探测 /health，没有服务就自动拉起 llama-server
```

**为什么用工具调用而不是"让模型输出文本再用正则抠"**：实测工具调用准确率最高（100% / 91.7%），
自由文本 + 正则只有 58%~75% 且慢 3 倍；纯正则 0ms 但会把"环状抓握"错配成"抓握"。
完整数据见 `AI操控方案.md`。

---

## 4. 怎么运行

```bash
cd InteractionUITest

# 完整语音操控（推荐）—— 不需要手动起 llama-server，程序会自己拉起
~/miniconda3/envs/ai/bin/python main.py

# 只调界面 / 没有 torch 时（麦克风按钮自动置灰，仍可用文字/正则通道）
~/miniconda3/envs/test/bin/python main.py
```

界面里点左下角 **🎤 语音操控** → 说话 → 再点一次结束 → 自动识别并点击。

没有麦克风时用 `AI_TEXT_DEBUG=1`，悬浮条上会多一个输入框，打字回车即可。

### 本地 LLM 服务的处理规则

程序启动时探测 `http://127.0.0.1:8081/health`：

| 情况 | 行为 |
|---|---|
| 已经有服务在跑 | 直接用它，**不重复起第二个**；关窗口**也不会杀它** |
| 没有服务 | 自动按下面这条命令拉起，日志写 `~/.cache/ui-test/llama-server.log` |
| 关窗口 | 只结束"自己拉起来的"那个进程，不留孤儿 |

```bash
# 等价的命令（排查时可手动跑）
~/llama.cpp/build/bin/llama-server -m ~/模型/Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf \
    --host 127.0.0.1 --port 8081 -ngl 99 -c 8192 --jinja
```

### 常用环境变量

`AI_ENABLE`（总开关）、`AI_VOICE`、`AI_TEXT_DEBUG`、`AI_LLM_URL`、`AI_LLM_MODEL`、
`AI_LLM_AUTOSTART`、`AI_LLAMA_SERVER`、`AI_LLAMA_EXTRA_ARGS`、`AI_ASR_MODEL`、`AI_REGEX_FIRST`。
完整表格见 `项目导航.md` 7.3 节。

---

## 5. 踩过的坑（**改代码前务必先看这一节**）

这四个都是真实发生过、排查过的，不是假想。

### 5.1 QThread 生命周期 → SIGABRT（最严重）

**症状**：说完话、界面进入"正在判断该点哪里…"，1~2 秒后进程被 `SIGABRT` 杀掉（systemd 报 Signal 6，退出码 134）。

**根因**：`LlmWorker` 是 `QThread` 且没有 C++ 父对象，生命周期完全由 Python 引用计数决定。
QThread 内部的收尾顺序是：

```
run() 返回 -> sip 释放包装引用 -> d->running = false -> emit finished
                                ^^^ 这个窗口里，线程还没被标记为结束
```

原来的代码在 `finished_with_id` 槽里写 `self._worker = None`，最后一个引用可能落在这个窗口里被释放，
于是 `QThread::~QThread()` 检测到 `running == true` → `qFatal` → abort。

**铁律**（`router.py` 顶部有同样的说明）：
1. worker 的引用**只能在线程发出 `finished` 之后释放**；`IntentRouter` 用 `self._workers` 集合持有强引用，
   只在 `_release_worker()` 里 `discard`。
2. `finished_with_id` / `failed` 的槽里**绝对不许动引用**；判断"忙不忙"看 `self._busy`，**不要用 `isRunning()`**。
3. 关窗口要先把线程等回来：`closeEvent` → `AiController.shutdown()` → `IntentRouter.shutdown()`。
4. 语音线程同理，见 `controller._voice_workers`。
5. 这是个**窄窗口竞态**，平时跑一百次可能都不复现 —— 不要因为"我这儿没事"就改回原来的写法。

> 注意：`server.py` 里那个几十秒的启动任务**故意用 `threading.Thread` 而不是 QThread**，就是为了绕开这条规则。

### 5.2 手势属于多个分期分组 → AI 把用户拽去别的分期

20 个手势里**有 14 个属于多个分组**（如「五指伸展」同时在一期/二期/三期/自由选择里）。

原来的代码一律 `group_of_gesture(name)`（返回第一个包含它的分组）然后切过去，
结果在布氏三期说"五指伸展"会跳到**布氏一期**。

**正确规则**：当前分组里有这个手势就**原地勾选**，只有当前分组确实没有时才切分组。
实现在 `gesture_cards.py:set_gesture_selected()`，**不要再在别处重复写切分组逻辑**（原来就是两处重复才踩的坑）。

### 5.3 悬浮条被切页压到下面

`QStackedLayout` 每次 `setCurrentWidget` 都会 `raise()` 当前页，把悬浮条盖住（视觉上灰蒙蒙的）。
修法：`controller` 里监听 `window.page_changed` 重新 `reposition()`（内部会 `raise_()`）。
**改窗口结构时别把这个连接删了。**

### 5.4 不要用 `pkill -f llama-server`

`-f` 匹配完整命令行，会把执行这条命令的 shell 自己也匹配上，导致命令无声中断（排查时极易误判）。
用 `pkill -x llama-server`。

### 5.5 操作层面的两个坑

- **手势卡状态存在两处**：卡片自己的 `_checked` 和 selector 的 `_selected`。
  只调 `card.setChecked(True)` 会出现"界面打勾了但 `selected()` 还是空"。用 `set_gesture_selected()`。
- **不要用 `QTest.mouseClick` 按坐标模拟点击**：本项目卡片是 `QFrame` 子类，没有 `.click()`，坐标又随布局变化。统一走动作注册表。

---

## 6. 验证情况

所有结论都经过实机验证，不是纸面推演。

| 项目 | 结果 |
|---|---|
| 5 种实现方式对比（真实模型，2 个场景 23 条自然口语） | 工具调用 100% / 91.7%，自由文本+正则 75% / 58.3% |
| 真实模型端到端（首页/手势页/镜像页，含 ASR 错别字） | 8/8 符合预期 |
| 连续 12 轮真实模型压力（每轮新建 QThread） | 无 SIGABRT，23.8s 完成 |
| 手势矩阵：6 分组 × 各自分组的所有手势（43 组） | 43/43 原地勾选，无跳转 |
| 跨分组自动切换 + 显式 tab 切换 | 全部正确 |
| 完整语音链路（假麦克风喂真实录音 → 真实 ASR → 真实 LLM） | 通过 |
| 冷启动自动拉起服务 → 跑指令 → 关窗口无孤儿进程 | 通过 |
| 已有服务时：不重复起、不误杀 | 通过 |
| 失败路径（找不到二进制 / 找不到模型 / 关闭自动启动 / 关闭 AI） | 提示清晰，行为正确 |
| 全部文件 `py_compile` | 通过 |

---

## 7. 环境

| 环境 | Python | PyQt5 | torch | 能跑什么 |
|---|---|---|---|---|
| `ai` | 3.12.13 | 5.15.10（本次新装） | 2.12.1+rocm7.2 | 界面 + AI 点击 + **语音识别** |
| `test` | — | 5.15.10 | 无 | 界面 + AI 点击（麦克风按钮自动置灰） |

- GPU：AMD Radeon RX 9070 XT（ROCm），16 GB 显存
- LLM：`~/模型/Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf`（Q4，5.3 GB）
- ASR：`~/模型/Qwen--Qwen3-ASR-0.6B-hf`
- llama.cpp：`~/llama.cpp/build/bin/llama-server`（r9716，ROCm 构建），**不在 PATH 上**

---

## 8. 已知限制 / 没做的事

- **单次点击，不做 agent loop**。一次请求只点一个控件，没有多步任务规划。
- **单次 AI 判断约 1.2~2.3 秒**，主要花在模型的思考 token 上。试过四种关思考的参数
  （`--reasoning off`、`chat_template_kwargs.enable_thinking=false`、`reasoning_effort=none`、`reasoning_budget=0`）
  在该模型上**全部无效**。要压到 300ms 级需要换非思考模型。
- **`max_tokens` 不能调小**：思考 token 会吃掉预算，给 64 会把工具参数 JSON 截断导致解析失败。默认 512。
- **正则快速通道只给"返回/下一步"这类确定性极高的命令开**（`fast=True`）。
  给手势名开快速通道会踩子串重叠的坑（"环状抓握"含"抓握"）。默认 `fast=False` 走模型更安全。
- **手势页的"下一步"是空实现**（原始代码就是占位），AI 点它没有可见效果。
- **镜像页的"添加手势/康复训练"只发信号、没人接收**（原始代码就是占位）。
- 没有 DPI / 分辨率适配，字号写死 px。
- 语音模型首次加载约 3~5 秒（之后常驻），所以**第一句话会慢一点**。
- **未决问题**：当前"在布氏一期说球体抓握（一期没有这个手势）"的行为是**自动切到布氏三期**再勾选。
  也可以改成"不切、提示这个分期没有该手势"。前者省事，后者更严谨（避免 AI 擅自带用户离开医生选定的分期）。**尚未与用户确认。**

---

## 9. 给下一个 Agent 的建议

1. **改 AI 相关代码前，先读 `app/ai/router.py` 顶部关于 QThread 的说明**，以及本文件第 5 节。
2. **加新页面的 AI 操作只需要改 `app/ai/actions.py` 一个文件** —— 工具调用的 enum、正则别名、回表校验全部从这张表自动派生。模板见 `项目导航.md` 7.4 节。
3. **不要把"怎么点"散落到 `actions.py` 之外**。动作注册表是唯一事实来源，5.2 那个 bug 就是逻辑散在两处造成的。
4. 改动后至少跑一遍：手势矩阵（`43/43`）、QThread 回归、冷启动自动拉起。
5. 未决问题见第 8 节最后一条，动手前先问用户。
