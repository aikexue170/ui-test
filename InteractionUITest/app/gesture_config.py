SELECTABLE_GESTURES = {
    "五指屈曲": {
        "model_label": 1,
        "glove_label": 1,
        "video": "视频最新/SS-16.mp4",
        "image": "SS-16.png",
    },
    "食指指向伸展": {
        "model_label": 2,
        "glove_label": 2,
        "video": "视频最新/SS-17.mp4",
        "image": "SS-17.png",
    },
    "拇指指尖捏取": {
        "model_label": 3,
        "glove_label": 3,
        "video": "视频最新/SS-24.mp4",
        "image": "SS-24.png",
    },
    "拇食中指伸展": {
        "model_label": 4,
        "glove_label": 4,
        "video": "视频最新/SS-13.mp4",
        "image": "SS-13.png",
    },
    "四指伸展": {
        "model_label": 5,
        "glove_label": 5,
        "video": "视频最新/SS-14.mp4",
        "image": "SS-14.png",
    },
    "食中指伸展": {
        "model_label": 6,
        "glove_label": 6,
        "video": "视频最新/SS-12.mp4",
        "image": "SS-12.png",
    },
    "拇指竖起": {
        "model_label": 7,
        "glove_label": 7,
        "video": "视频最新/SS-11.mp4",
        "image": "SS-11.png",
    },
    "五指伸展": {
        "model_label": 8,
        "glove_label": 8,
        "video": "视频最新/SS-15.mp4",
        "image": "SS-15.png",
    },
    "中指屈曲": {
        "model_label": 9,
        "glove_label": 9,
        "video": "视频最新/SS-3.mp4",
        "image": "SS-3.png",
    },
    "抓握": {
        "model_label": 10,
        "glove_label": 10,
        "video": "视频最新/SS-18.mp4",
        "image": "SS-18.png",
    },
    "小指屈曲": {
        "model_label": 11,
        "glove_label": 11,
        "video": "视频最新/SS-7.mp4",
        "image": "SS-7.png",
    },
    "无名指屈曲": {
        "model_label": 12,
        "glove_label": 12,
        "video": "视频最新/SS-5.mp4",
        "image": "SS-5.png",
    },
    "四支点抓取": {
        "model_label": 13,
        "glove_label": 13,
        "video": "视频最新/SS-25.mp4",
        "image": "SS-25.png",
    },
    "棍状物抓握": {
        "model_label": 14,
        "glove_label": 14,
        "video": "视频最新/SS-19.mp4",
        "image": "SS-19.png",
    },
    "拇指屈曲": {
        "model_label": 15,
        "glove_label": 15,
        "video": "视频最新/SS-10.mp4",
        "image": "SS-10.png",
    },
    "环形抓握": {
        "model_label": 16,
        "glove_label": 16,
        "video": "视频最新/SS-21.mp4",
        "image": "SS-21.png",
    },
    "球体抓握": {
        "model_label": 17,
        "glove_label": 17,
        "video": "视频最新/SS-22.mp4",
        "image": "SS-22.png",
    },
    "三指球体抓握": {
        "model_label": 18,
        "glove_label": 18,
        "video": "视频最新/SS-23.mp4",
        "image": "SS-23.png",
    },
    "食指屈曲": {
        "model_label": 19,
        "glove_label": 19,
        "video": "视频最新/SS-1.mp4",
        "image": "SS-1.png",
    },
    "食指伸展抓握": {
        "model_label": 20,
        "glove_label": 20,
        "video": "视频最新/SS-20.mp4",
        "image": "SS-20.png",
    },
}

GESTURE_GROUPS = {
    "布氏一期": ["五指伸展", "五指屈曲"],
    "布氏二期": ["五指伸展", "五指屈曲", "拇指屈曲", "抓握"],
    "布氏三期": ["五指伸展", "五指屈曲", "拇指竖起", "食中指伸展", "四指伸展", "球体抓握"],
    "布氏四期": ["食指屈曲", "中指屈曲", "拇指竖起", "食中指伸展", "四指伸展", "棍状物抓握"],
    "布氏五期": ["棍状物抓握", "食指伸展抓握", "环形抓握", "球体抓握", "拇指指尖捏取"],
    "自由选择": [
        "五指屈曲",
        "食指指向伸展",
        "拇指指尖捏取",
        "拇食中指伸展",
        "四指伸展",
        "食中指伸展",
        "拇指竖起",
        "五指伸展",
        "中指屈曲",
        "抓握",
        "小指屈曲",
        "无名指屈曲",
        "四支点抓取",
        "棍状物抓握",
        "拇指屈曲",
        "环形抓握",
        "球体抓握",
        "三指球体抓握",
        "食指屈曲",
        "食指伸展抓握",
    ],
}

MODEL_LABEL_NAMES = {
    "0": "休息",
    "1": "五指屈曲",
    "2": "食指指向伸展",
    "3": "拇指指尖捏取",
    "4": "拇食中指伸展",
    "5": "四指伸展",
    "6": "食中指伸展",
    "7": "拇指竖起",
    "8": "五指伸展",
    "9": "中指屈曲",
    "10": "抓握",
    "11": "小指屈曲",
    "12": "无名指屈曲",
    "13": "四支点抓取",
    "14": "棍状物抓握",
    "15": "拇指屈曲",
    "16": "环形抓握",
    "17": "球体抓握",
    "18": "三指球体抓握",
    "19": "食指屈曲",
    "20": "食指伸展抓握",
}

MODEL_TO_GLOVE_LABEL = {
    0: 0,
    1: 1,
    2: 2,
    3: 3,
    4: 4,
    5: 5,
    6: 6,
    7: 7,
    8: 8,
    9: 9,
    10: 10,
    11: 11,
    12: 12,
    13: 13,
    14: 14,
    15: 15,
    16: 16,
    17: 17,
    18: 18,
    19: 19,
    20: 20,
}

REST_VIDEO_CANDIDATES = ("手掌放松6秒v.mp4", "手掌放松2秒v.mp4", "休息.mp4")


def model_label_for_gesture(gesture_name):
    return int(SELECTABLE_GESTURES[gesture_name]["model_label"])


def glove_label_for_model(model_label):
    return MODEL_TO_GLOVE_LABEL.get(int(model_label))


def video_name_for_gesture(gesture_name):
    return SELECTABLE_GESTURES[gesture_name]["video"]


def image_name_for_gesture(gesture_name):
    return SELECTABLE_GESTURES[gesture_name].get("image", "")


def group_of_gesture(gesture_name):
    """手势所属的第一个分期分组名；该手势不存在时返回 None。"""
    for group_name, gestures in GESTURE_GROUPS.items():
        if gesture_name in gestures:
            return group_name
    return None


def video_name_for_model_label(model_label):
    model_label = int(model_label)
    for config in SELECTABLE_GESTURES.values():
        if int(config["model_label"]) == model_label:
            return config["video"]
    return ""
