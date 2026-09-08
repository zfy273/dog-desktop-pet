# -*- coding: utf-8 -*-
"""
示例插件：活动监视器
在控制台打印各种事件信息，演示所有钩子方法的用法。
要启用此插件，保持本文件在 plugins/ 目录下即可。
要禁用，删除本文件或改名为下划线开头（如 _example.py）。
"""


class Plugin:
    def __init__(self, app):
        self.app = app
        self.name = "活动监视器"
        self.frame_count = 0
        print(f"[插件] {self.name} 已初始化")

    def on_dog_spawn(self, dog):
        """一只狗被创建时调用"""
        print(f"[插件] 新狗出生！位置：({int(dog.x)}, {int(dog.y)})，"
              f"速度：({dog.dx:.2f}, {dog.dy:.2f})")

    def on_egg_spawn(self, egg):
        """一颗蛋被创建时调用"""
        print(f"[插件] 新蛋出现！位置：({int(egg.x)}, {int(egg.y)})，"
              f"将在 {egg.hatch_delay/1000:.1f} 秒后孵化")

    def on_hatch(self, egg, dog):
        """蛋孵化出狗时调用"""
        print(f"[插件] 蛋孵化成功！位置：({int(egg.x)}, {int(egg.y)})")

    def on_dog_click(self, dog, event):
        """狗被左键点击时调用"""
        print(f"[插件] 狗被点击！位置：({int(dog.x)}, {int(dog.y)})")

    def on_update(self, app):
        """每一帧更新时调用（约33fps）"""
        self.frame_count += 1
        # 每100帧（约3秒）打印一次统计
        if self.frame_count % 100 == 0:
            print(f"[插件] 运行统计：{len(app.dogs)} 只狗，"
                  f"{len(app.eggs)} 颗蛋，已运行 {self.frame_count} 帧")

    def on_quit(self, app):
        """程序退出时调用"""
        print(f"[插件] {self.name} 退出，共运行 {self.frame_count} 帧")
