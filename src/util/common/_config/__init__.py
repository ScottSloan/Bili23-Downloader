"""
配置系统的内部实现

包名带下划线是因为 `util/common/config.py` 这个公开模块必须保留原名 ——
全仓库一百多处 `from util.common.config import config` 不能动。
同名的模块与包在 Python 里无法共存，所以机器实现放在这里，
`config.py` 只负责把它们组装成对外的 config 单例。
"""
