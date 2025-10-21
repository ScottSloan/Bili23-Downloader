import gettext

_ = gettext.gettext

area_data = {
    "label": _("显示区域"),
    "value": 5,
    "min_value": 1,
    "max_value": 5,
    "data": {
        1: "20%",
        2: "40%",
        3: "60%",
        4: "80%",
        5: "100%"
    }
}

alpha_data = {
    "label": _("不透明度"),
    "value": 80,
    "min_value": 10,
    "max_value": 100,
    "data": {}
}

speed_data = {
    "label": _("弹幕速度"),
    "value": 5,
    "min_value": 1,
    "max_value": 5,
    "data": {
        1: _("极慢"),
        2: _("较慢"),
        3: _("适中"),
        4: _("较快"),
        5: _("极快")
    }
}

density_data = {
    "label": _("弹幕密度"),
    "value": 1,
    "min_value": 1,
    "max_value": 3,
    "data": {
        1: _("正常"),
        2: _("较多"),
        3: _("重叠")
    }
}