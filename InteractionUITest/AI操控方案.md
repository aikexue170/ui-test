# AI 语音操控方案（调研 + 设计）

> 目标：用户说一句话（经 STT 转文字）→ AI 判断当前页面上该点哪个控件 → **自动点一次**，不做 agent loop。
> 本文的对比数据来自本机实测，不是推测。

---

## 一、结论（先说答案）

**推荐：工具调用（function calling）+ 页面动作注册表，正则只做"零延迟快速通道"。**

明确**不推荐**"让模型自由输出文本、再用正则从文本里抠出按钮名"——实测它在三种 AI 方案里准确率最低、延迟最高。

三条硬规则：

1. **id 比文字可靠**。不要让模型输出"主动训练"这种中文，让它输出 `active_training` 这种 id。中文有同音字、ASR 误识别、标点差异，模型输出文字再匹配等于把错误从模型层挪到字符串层。
2. **enum 收口**。工具的 `action_id` 用 `enum` 限定为"当前页面真实存在的动作 id + `none`"。这样模型**物理上不可能**吐出页面上不存在的按钮，越界问题在解码层就消失了。
3. **回表校验 + 永远提供 `none`**。拿到 id 后必须在本页动作表里再查一次；`none` 表示"没听懂/没有这个功能"，此时**不点任何东西**，给用户一个语音或视觉反馈。宁可不动，不可点错。

---

## 二、实测对比（本机数据）

**测试环境**：llama-server r9716（本机 ROCm 构建），模型 `Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf`（Q4，GPU 全量 offload）；
两个场景：**A 首页**（3 个按钮 + none）、**B 主动训练手势页**（28 个候选 + none）；
测试语句是**自然口语**（含同音字误识别），不是照着按钮文字念。

### 场景 A：首页（候选 3 + none）

| 方案 | 准确率 | 平均耗时 |
|---|---|---|
| ① **工具调用** | **12/12 = 100%** | **1524 ms** |
| ② JSON Schema 约束输出 | 11/12 = 91.7% | 2528 ms |
| ③ 自由文本 + 正则提取 | 9/12 = 75.0% | 5704 ms |
| ④ 纯关键词正则（不用 AI） | 5/12 = 41.7% | ~0 ms |
| ⑤ 正则优先 + LLM 兜底 | **12/12 = 100%** | 1478 ms |

### 场景 B：主动训练手势页（候选 28 + none）

| 方案 | 准确率 | 平均耗时 |
|---|---|---|
| ① **工具调用** | **11/12 = 91.7%** | 1561 ms |
| ② JSON Schema 约束输出 | 10/12 = 83.3% | 3503 ms |
| ③ 自由文本 + 正则提取 | 7/12 = 58.3% | 5231 ms |
| ④ 纯关键词正则（不用 AI） | 9/12 = 75.0% | ~0 ms |
| ⑤ 正则优先 + LLM 兜底 | 10/12 = 83.3% | **537 ms** |

### 从数据里读出来的四件事

1. **工具调用在准确率和延迟上都最好**，压过 JSON Schema。原因：llama.cpp 的 `response_format: json_schema` 走的是语法约束解码，逐 token 校验语法树，生成明显更慢（2.5–3.5 s）。
2. **"自由文本 + 正则" 是最差的一档**（58–75%，5 s+）。模型会啰嗦、会加解释、会换行、会输出中文标点，正则要么抠不到、要么抠错；而且输出越长越慢。**你提到的"正则文本"那条路，实测不建议走。**
3. **纯正则（不用 AI）快但脆**。首页只有 41.7%——因为用户不会照着按钮文字说话（"让我自己试着发力"、"机器带着我动就行"、"照镜子那个模式"全部落空）。手势页 75%，看着还行，但它会犯**子串重叠**的致命错误：说"我要练**环状**抓握"（ASR 把"环形"听成"环状"），正则匹配到了子串"抓握"，指向了**另一个手势**——**静默点错，比不点更糟**。
4. **混合方案的价值取决于页面**。手势页 9/12 被正则 0 ms 拦下，平均延迟从 1.5 s 降到 0.5 s；首页只有 1/12 命中，混合 ≈ 纯工具调用。所以正则快速通道是"锦上添花"，不是主力。

### 延迟说明（重要）

那 ~1.5 s 主要花在**模型的思考 token** 上。我试了四种关思考的办法，该模型仍然输出 `reasoning_content`：

| 尝试 | 结果 |
|---|---|
| 服务端 `--reasoning off` | 仍输出 reasoning_content |
| `chat_template_kwargs: {"enable_thinking": false}` | 无效 |
| `reasoning_effort: "none"` | 无效 |
| `reasoning_budget: 0` | 无效 |

配合 `max_tokens`：如果给太小（64），思考会把预算吃光，工具调用的 JSON 参数被截断 → **解析失败**。实测必须给到 512 左右。
**结论**：单次点击 1.5 s 实属可用，但想压到 300 ms 级需要换非思考模型。这是可选优化，不是阻塞项。

---

## 三、推荐架构

```
 麦克风
   │
   ▼
[STT 工作线程]  Qwen3-ASR（ai 环境，torch）
   │  pyqtSignal(str) ── 跨线程安全
   ▼
[IntentRouter  主线程]
   │
   ├─(1) 正则快速通道：别名命中且无歧义 → 直接出 id（0 ms）
   │
   ├─(2) 未命中 → 取「当前页面动作表」
   │        └─ HTTP → llama-server /v1/chat/completions  (tools + enum)
   │             └─ 返回 {"action_id": "..."}
   │        ※ 网络/模型等待期间界面不能卡 → 把这次请求也放工作线程，回来再 emit
   │
   ├─(3) 回表校验：id 必须存在于当前页动作表，否则丢弃
   │
   └─(4) 在主线程执行 action.run()
            ├─ QPushButton  → btn.click()
            └─ 自定义卡片    → 注册表里给的回调（见第五节，有坑）
```

建议新增目录 `InteractionUITest/app/ai/`：

| 文件 | 职责 |
|---|---|
| `actions.py` | **动作注册表**：每个页面 → `[{id, label, desc, aliases, run}]`。唯一事实来源，同时喂给 工具 schema / 正则 / 回表校验 |
| `llm.py` | OpenAI 兼容客户端（llama-server），负责拼工具、发请求、解析 tool_calls |
| `server.py` | **自动拉起 llama-server**：探活 → 没有才起 → 关窗口只收自己起的，省掉手动敲启动指令 |
| `router.py` | `IntentRouter`：正则 → LLM → 校验 → 执行；含超时、失败静默 |
| `voice.py` | STT 工作线程（改造 `TTS-LLM-STT/stt_demo.py`），`pyqtSignal(str)` 吐文本 |

---

## 四、动作注册表：怎么写

这是整个方案的基石。**AI 只认 id，id 到"怎么点"的映射留在 Python 里。**

```python
# app/ai/actions.py
from app.gesture_config import GESTURE_GROUPS

def home_actions(window):
    """首页：3 个 GlassActionCard + 顶栏返回主页"""
    return [
        dict(id="active_training",  label="主动训练",
             desc="患者主动发力，系统做意图识别与辅助动作",
             aliases=["主动训练", "主动", "自己发力", "自己动"],
             run=lambda: window.home.active_requested.emit()),
        dict(id="passive_training", label="被动训练",
             desc="机器带动患者循环执行规范动作",
             aliases=["被动训练", "被动", "机器带动", "帮我活动"],
             run=lambda: window.home.passive_requested.emit()),
        dict(id="mirror_training",  label="镜像训练",
             desc="手势校准与实时预测",
             aliases=["镜像训练", "镜像", "照镜子"],
             run=lambda: window.home.mirror_requested.emit()),
        dict(id="go_home", label="返回主页",
             desc="停留在康复训练选择页",
             aliases=["返回主页"], run=lambda: window.home.home_requested.emit()),
    ]

def gesture_page_actions(page):
    a = [dict(id="back", label="返回", desc="返回康复训练选择页",
              aliases=["返回", "回去", "上一页", "退出"], run=lambda: page.back_requested.emit()),
         dict(id="next", label="下一步", desc="确认当前选择并进入下一步",
              aliases=["下一步", "继续", "确定"], run=page.next_step)]
    for i, g in enumerate(GESTURE_GROUPS):
        a.append(dict(id=f"tab_{i+1}", label=g, desc=f"切换到「{g}」阶段分组",
                      aliases=[g],
                      run=(lambda n=g: page.selector.set_active_group(n))))
    for g in GESTURE_GROUPS[next(iter(GESTURE_GROUPS))]:
        a.append(dict(id=f"gesture_{g}", label=g, desc=f"选择手势「{g}」",
                      aliases=[g], run=(lambda n=g: _toggle_gesture(page, n))))
    return a
```

> ⚠️ 手势列表要**覆盖所有分组**（`GESTURE_GROUPS` 里的全部 20 个手势），不能只列当前 Tab 可见的。
> 因为 AI 可能说"我想练布氏五期的环形抓握"——**动作表描述的是"这个页面上能做什么"，不是"此刻屏幕上画了什么"**。执行时先 `set_active_group` 再点卡片即可。

### 工具定义（发给模型的部分）

```python
tools = [{
  "type": "function",
  "function": {
    "name": "click_button",
    "description": "点击当前界面上的一个控件",
    "parameters": {
      "type": "object",
      "properties": {
        "action_id": {
          "type": "string",
          "enum": [a["id"] for a in actions] + ["none"],   # ← 关键：枚举收口
        }
      },
      "required": ["action_id"],
    },
  },
}]
```

**不要把 `reason`（理由字段）加进去**。实测它会拖长输出、增加截断风险，而单次点击根本不需要理由。要调试就开日志。

发给模型的 user 内容：

```
当前页面可用控件：
- active_training: 主动训练 —— 患者主动发力，系统做意图识别与辅助动作
- passive_training: 被动训练 —— 机器带动患者循环执行规范动作
- mirror_training: 镜像训练 —— 手势校准与实时预测
- none: 当前页面上没有与用户意图匹配的控件

用户说：「让我自己试着发力」
```

---

## 五、Qt 落地细节（实测踩出来的坑）

### 1. 本项目有两类"按钮"，点击方式不同

| 控件 | 类型 | 怎么点 |
|---|---|---|
| `◀ 返回`、`下一步 ▶`、6 个阶段 Tab | `QPushButton` | 有 `.click()`，直接调 |
| 首页三个大卡片（`GlassActionCard`） | `QFrame` 子类 | **没有 `.click()`**，走注册表里的 `run`（发信号） |
| 手势卡（`GestureImageCard`） | `QFrame` 子类 | **没有 `.click()`**，见下一条 |

> 实测确认：`QPushButton.click` 存在，`GestureImageCard.click` 不存在。
> **不要用 `QTest.mouseClick` 按坐标模拟点击**——坐标随布局变化，脆弱且难排查。走注册表直调最稳。

### 2. 手势卡的状态存在两处，只改一处会脱同步 ⚠️

`GestureImageCard` 自己记一个 `_checked`，而 `GestureStageSelector` 另有 `_selected` 集合（`selected()` 返回的是后者）。

实测：

```python
sel._visible_cards["五指伸展"].setChecked(True)          # 卡片显示 ✓
sel.selected()                                            # → []   ← 不同步！
```

**正确做法**——模拟"用户真的点了一下"：

```python
def _toggle_gesture(page, name):
    sel = page.selector
    group = next(g for g, items in GESTURE_GROUPS.items() if name in items)
    sel.set_active_group(group)                # ① 先切到该手势所在分组
    card = sel._visible_cards[name]            # ② 再取卡片（见下条）
    card.setChecked(not card.isChecked())      # ③ 翻转视觉状态
    card.clicked.emit()                        # ④ 让 selector 同步集合
```

### 3. `_visible_cards` 只包含"当前 Tab"的卡片

切到别的分组后，旧分组的卡片就不在字典里了，直接查会 `KeyError`。
**必须先 `set_active_group(...)` 再查表**（上面代码的 ① ② 顺序不能反）。

### 4. 选中状态跨 Tab 保留，但页面切换会被清空

- 在同一页面内换 Tab，已选手势**保留**（符合原设计）。
- 从别的页面进入 `active`/`passive` 时，`window.py:48` 会自动 `reset_selection()`——**自动化不要假设上次选中的还在**。

### 5. 线程安全（最容易出事的地方）

ASR 推理和 LLM 的 HTTP 请求都必须放**工作线程**（9B 模型一次 1.5 s，直接卡死界面）。
但 **Qt 控件只能在主线程碰**。所以：

```python
class VoiceWorker(QThread):
    recognized = pyqtSignal(str)      # 只 emit，不碰控件
    ...
    self.recognized.emit(text)

# 主线程
worker.recognized.connect(router.handle_text)   # 自动排队到 GUI 线程
```

项目已经预留好了入口：`window.navigate_requested.emit(page_id)`（`window.py:12,39`）。**注意它只接页面 id**（`home/active/passive/mirror`），手势级操作要自己加一条信号。

### 6. `next_step()` 现在是空实现

`training_gesture_select_page.py:58` 里有注释说明是占位。AI 点它不会有任何可见效果，属预期。

---

## 六、PyQt5 装到 `ai` 环境（已实测可行）

**为什么要装**：ASR 模型（torch/transformers）只在 `ai` 环境里，而界面必须和它**同进程**才能共享控件和信号。跨进程要另做 IPC，不值得。

**现状**：

| 环境 | Python | PyQt5 | torch |
|---|---|---|---|
| `ai` | 3.12.13 | ❌ 无 | ✅ 2.12.1+rocm7.2、transformers 5.16.1 |
| `test` | — | ✅ 5.15.10 | 无（已在用这个跑界面） |

**安装命令**：

```bash
~/miniconda3/envs/ai/bin/python -m pip install PyQt5==5.15.10
```

**实测风险评估**（`pip install --dry-run` 已跑过）：

- 只会新增 3 个包：`PyQt5-5.15.10`、`PyQt5-Qt5-5.15.19`、`PyQt5_sip-12.19.0`——与能正常运行的 `test` 环境**完全同版本**。
- `pip check`：**无依赖冲突**。
- `ai` 里**没有 opencv-python**——这是 Linux 上 Qt 插件加载失败（`Could not load the Qt platform plugin "xcb"`）最常见的元凶，这里不存在。
- 系统库齐全：`libxcb-xinerama`、`libxkbcommon-x11`、`libGL`、`libEGL` 均 OK。

**两条注意**：

1. **用 pip，不要用 `conda install pyqt`**。conda 的 `qt` 包会带自己的 Qt 并可能改动 numpy，而你的 torch 是 ROCm 专用构建，numpy 2.4.4 被牵动风险不划算。pip 路线已验证干净。
2. 装完后 matplotlib 可能自动改选 Qt5Agg 后端。跑无头脚本时显式设 `MPLBACKEND=Agg` 即可。

**STT 改造提示**：现有 `stt_demo.py` 是控制台交互（`input()` 阻塞、每次启动加载模型）。集成到界面需要改成：
① 模型启动时后台加载一次并常驻；② 录音触发改成按钮或 VAD，不再靠回车；③ 识别结果通过 `pyqtSignal(str)` 抛出。

---

## 七、落地步骤建议

1. **环境**：`pip install PyQt5==5.15.10` 到 `ai`；用 `ai` 的 python 跑一次 `main.py` 确认界面能起来。
2. **抽动作注册表**：新建 `app/ai/actions.py`，先把首页 + 镜像页（动作少、最好验证）接上。
3. **接工具调用**：写 `llm.py` + `router.py` + `server.py`，先用文字输入联调（`AI_TEXT_DEBUG=1`），把"文字 → 点对按钮"跑通。
   **不需要手动起 llama-server**：`server.py` 会探测 `http://127.0.0.1:8081/health`，没有才按下面这条命令自动拉起（已在跑就不重起，关窗口只收自己起的）。
   ```bash
   ~/llama.cpp/build/bin/llama-server -m ~/模型/Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf \
       --host 127.0.0.1 --port 8081 -ngl 99 -c 8192 --jinja
   ```
   注意：单次请求 `max_tokens` 给 **512**；给 64 会因为思考 token 把 JSON 参数截断。
4. **再接手势页**：动作多（28 个）、坑集中在手势卡，按第五节的写法处理。
5. **最后接 STT**：改造 `stt_demo.py` 成 `voice.py` 工作线程，接到 `router.handle_text`。
6. **加反馈**：`none` 或校验失败时，在界面上给一句"没听懂，请再说一次"，否则用户不知道是没识别还是没反应。

**可选优化**（不阻塞）：
- 服务端开 prompt 缓存：同一页面的菜单文本固定，前缀命中可省 prefill。
- 把"页面上下文"在一段会话里只在页面变化时重建，避免每句话都重发长菜单。
- 若嫌 1.5 s 慢，换非思考模型或更小的模型（但需重测准确率）。
