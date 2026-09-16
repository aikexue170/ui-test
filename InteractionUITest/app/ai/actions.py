"""动作注册表：把「页面上能点的东西」变成一份 AI 认得的清单。

设计要点（见 AI操控方案.md）：

* **id 是英文标识符，label 才是中文**。模型输出 id，中文只用来喂上下文。
* 注册表是唯一事实来源：工具调用的 enum、正则快速通道、回表校验都从它派生。
* `run` 是真正执行点击的回调。**不要用坐标模拟鼠标**——本项目里的
  GlassActionCard / GestureImageCard 是 QFrame 子类，没有 .click()，
  统一在这里做适配。
* 手势页的动作表列的是「这个页面上能做什么」，覆盖全部 20 个手势，
  而不是「此刻屏幕上画了什么」。执行时先切分组再点卡片。
* `fast=True` 表示允许走正则快速通道，只给确定性极高的命令开。
"""

from app.gesture_config import GESTURE_GROUPS


def _action(action_id, label, desc, run, aliases=(), fast=False):
    return {
        "id": action_id,
        "label": label,
        "desc": desc,
        "run": run,
        "aliases": list(aliases),
        "fast": bool(fast),
    }


# ---------------------------------------------------------------- 首页
def _home_actions(window):
    home = window.home
    return [
        _action(
            "active_training", "主动训练",
            "进入主动训练模式：患者自己发力，系统做意图识别与辅助动作",
            lambda: home.active_requested.emit(),
            aliases=["主动训练", "主动"],
        ),
        _action(
            "passive_training", "被动训练",
            "进入被动训练模式：机器带动患者循环执行规范动作",
            lambda: home.passive_requested.emit(),
            aliases=["被动训练", "被动"],
        ),
        _action(
            "mirror_training", "镜像训练",
            "进入镜像训练模式：手势校准与实时预测",
            lambda: home.mirror_requested.emit(),
            aliases=["镜像训练", "镜像"],
        ),
        _action(
            "go_home", "返回主页",
            "停留在康复训练选择页（首页）",
            lambda: home.home_requested.emit(),
            aliases=["返回主页", "主页"],
            fast=True,
        ),
    ]


# ---------------------------------------------------------------- 镜像训练菜单
def _mirror_actions(window):
    mirror = window.mirror
    return [
        _action(
            "mirror_add_gesture", "添加手势",
            "进入手势采集与模型校准流程",
            lambda: mirror.gesture_requested.emit(),
            aliases=["添加手势", "手势采集"],
        ),
        _action(
            "mirror_rehab", "康复训练",
            "加载模型并开始实时预测的康复训练",
            lambda: mirror.rehab_requested.emit(),
            aliases=["康复训练"],
        ),
        _action(
            "back", "返回主页",
            "回到康复训练选择页（首页）",
            lambda: mirror.back_requested.emit(),
            aliases=["返回", "回去", "上一页", "退出"],
            fast=True,
        ),
    ]


# ---------------------------------------------------------------- 手势选择页
def _gesture_actions(page):
    selector = page.selector
    items = [
        _action(
            "back", "返回",
            "返回康复训练选择页（首页）",
            lambda: page.back_requested.emit(),
            aliases=["返回", "回去", "上一页", "退出"],
            fast=True,
        ),
        _action(
            "next", "下一步",
            "确认当前已选手势并进入下一步",
            page.next_step,
            aliases=["下一步", "继续", "确定"],
            fast=True,
        ),
    ]

    for index, group_name in enumerate(GESTURE_GROUPS):
        items.append(
            _action(
                "tab_%d" % (index + 1), group_name,
                "把下方手势列表切换到「%s」阶段分组" % group_name,
                (lambda name=group_name: selector.set_active_group(name)),
                aliases=[group_name],
            )
        )

    for group_name, gestures in GESTURE_GROUPS.items():
        for gesture in gestures:
            items.append(
                _action(
                    "gesture_" + gesture, gesture,
                    "勾选手势「%s」；当前阶段分组里就有它时直接勾选，"
                    "没有才自动切到含它的分组" % gesture,
                    (lambda name=gesture: selector.set_gesture_selected(name, True)),
                    aliases=[gesture],
                )
            )

    # 同一手势可能在多个分组出现，按 id 去重
    unique = {}
    for item in items:
        unique.setdefault(item["id"], item)
    return list(unique.values())


# ---------------------------------------------------------------- 对外接口
PAGE_LABELS = {
    "home": "康复训练选择页（首页）",
    "active": "选择主动训练手势页",
    "passive": "选择被动训练手势页",
    "mirror": "镜像训练菜单页",
}


def page_id_of(window):
    """当前正在显示的页面标识。"""
    widget = window.currentWidget()
    return widget.property("page_id") if widget is not None else None


def build_registry(window):
    """返回 {页面标识: [动作, ...]}。"""
    return {
        "home": _home_actions(window),
        "active": _gesture_actions(window.active),
        "passive": _gesture_actions(window.passive),
        "mirror": _mirror_actions(window),
    }
