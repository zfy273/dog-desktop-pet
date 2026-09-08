# -*- coding: utf-8 -*-
"""
小狗桌宠
- 显示在桌面最上层，四处游荡
- 左键点击任意一只狗 -> 生出一颗鸵鸟蛋（重力掉落到底部）
- 鸵鸟蛋 10~20 秒后开始孵化：飞快旋转 -> 小狗破蛋飞出 -> 蛋消失
- 每只狗的移动速度独立随机
- 右键 -> 弹出菜单（新增一颗蛋 / 退出）
- 支持 config.json 配置
- 支持 plugins/ 目录插件扩展
"""

import tkinter as tk
from tkinter import messagebox
import random
import sys
import os
import json
import importlib.util
import traceback
from PIL import Image, ImageTk

# ========== Pillow 兼容性处理 ==========
# Pillow 9.1.0 之前用 Image.LANCZOS，之后用 Image.Resampling.LANCZOS
try:
    from PIL.Image import Resampling
    _LANCZOS = Resampling.LANCZOS
    _BICUBIC = Resampling.BICUBIC
except (ImportError, AttributeError):
    _LANCZOS = Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.BILINEAR
    _BICUBIC = Image.BICUBIC if hasattr(Image, "BICUBIC") else Image.BILINEAR


# ========== 默认配置 ==========
DEFAULT_CONFIG = {
    "dog_width": 140,
    "egg_width": 90,
    "move_speed_min": 0.6,
    "move_speed_max": 6.5,
    "gravity": 0.6,
    "hatch_min_ms": 10000,
    "hatch_max_ms": 20000,
    "spin_ticks": 45,
    "spin_frame_count": 12,
    "animate_interval": 30,
    "change_dir_chance": 0.02,
    "max_dogs": 50,
    "max_eggs": 30,
    "transparent_color": "magenta",
    "enable_plugins": True,
}


def load_config(base_dir):
    """读取 config.json，不存在或格式错误时返回默认配置"""
    config = DEFAULT_CONFIG.copy()
    config_path = os.path.join(base_dir, "config.json")
    if not os.path.exists(config_path):
        return config, "config.json 不存在，使用默认配置"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            user_config = json.load(f)
        config.update(user_config)
        return config, "config.json 加载成功"
    except Exception as e:
        return config, f"config.json 读取失败（{e}），使用默认配置"


class Dog:
    """每只狗对应一个无边框透明置顶窗口"""

    def __init__(self, app, x=None, y=None, fly_out=False):
        self.app = app
        cfg = app.config
        self.w = app.dog_w
        self.h = app.dog_h

        self.window = tk.Toplevel(app.root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-transparentcolor", cfg["transparent_color"])
        self.window.configure(bg=cfg["transparent_color"])

        self.label = tk.Label(
            self.window,
            image=app.dog_photo,
            bg=cfg["transparent_color"],
            bd=0,
            highlightthickness=0,
        )
        self.label.pack()

        self.label.bind("<Button-1>", self.on_left_click)
        self.label.bind("<Button-3>", app.show_menu)

        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        if x is None:
            x = random.randint(0, max(0, screen_w - self.w))
        if y is None:
            y = random.randint(0, max(0, screen_h - self.h))
        x = max(0, min(x, screen_w - self.w))
        y = max(0, min(y, screen_h - self.h))
        self.x = float(x)
        self.y = float(y)
        self.window.geometry(f"{self.w}x{self.h}+{int(self.x)}+{int(self.y)}")

        self.fly_out = fly_out
        self.fly_ticks = 0
        if fly_out:
            self.dy = -9.0
            self.dx = random.uniform(-3.5, 3.5)
        else:
            self._random_speed()

    def _random_speed(self):
        """每只狗独立随机速度和方向"""
        cfg = self.app.config
        speed = random.uniform(cfg["move_speed_min"], cfg["move_speed_max"])
        self.dx = speed * random.choice([-1, 1]) * (0.4 + random.random() * 0.6)
        self.dy = speed * random.choice([-1, 1]) * (0.4 + random.random() * 0.6)
        if abs(self.dx) < 0.3:
            self.dx = 1.0 if self.dx >= 0 else -1.0
        if abs(self.dy) < 0.3:
            self.dy = 1.0 if self.dy >= 0 else -1.0

    def update(self):
        cfg = self.app.config

        if self.fly_out:
            self.fly_ticks += 1
            self.dy += 0.45
            self.x += self.dx
            self.y += self.dy
            screen_h = self.window.winfo_screenheight()
            if self.y >= screen_h - self.h:
                self.y = screen_h - self.h
            if self.fly_ticks >= 25:
                self.fly_out = False
                self._random_speed()
            self.window.geometry(f"+{int(self.x)}+{int(self.y)}")
            return

        self.x += self.dx
        self.y += self.dy

        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()

        if self.x <= 0:
            self.x = 0
            self.dx = abs(self.dx)
        elif self.x >= screen_w - self.w:
            self.x = screen_w - self.w
            self.dx = -abs(self.dx)

        if self.y <= 0:
            self.y = 0
            self.dy = abs(self.dy)
        elif self.y >= screen_h - self.h:
            self.y = screen_h - self.h
            self.dy = -abs(self.dy)

        if random.random() < cfg["change_dir_chance"]:
            self.dx += random.uniform(-1.0, 1.0)
            self.dy += random.uniform(-1.0, 1.0)
            speed = (self.dx ** 2 + self.dy ** 2) ** 0.5
            if speed > cfg["move_speed_max"] * 1.5:
                scale = cfg["move_speed_max"] / speed
                self.dx *= scale
                self.dy *= scale

        self.window.geometry(f"+{int(self.x)}+{int(self.y)}")

    def on_left_click(self, event):
        """左键点击：生出一颗鸵鸟蛋"""
        offset_x = random.randint(-20, 20)
        self.app.spawn_egg(self.x + offset_x + self.w // 4, self.y)
        self.app._call_plugins("on_dog_click", self, event)

    def destroy(self):
        self.window.destroy()


class Egg:
    """鸵鸟蛋：重力掉落 -> 10~20秒后旋转孵化 -> 小狗破蛋飞出"""

    def __init__(self, app, x, y):
        self.app = app
        cfg = app.config
        self.w = app.egg_w
        self.h = app.egg_h
        self.hatched = False
        self.spinning = False
        self.spin_frame = 0
        self.spin_ticks = 0

        self.window = tk.Toplevel(app.root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-transparentcolor", cfg["transparent_color"])
        self.window.configure(bg=cfg["transparent_color"])

        self.label = tk.Label(
            self.window,
            image=app.egg_photo,
            bg=cfg["transparent_color"],
            bd=0,
            highlightthickness=0,
        )
        self.label.pack()
        self.label.bind("<Button-3>", app.show_menu)

        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        x = max(0, min(x, screen_w - self.w))
        y = max(0, min(y, screen_h - self.h))
        self.x = float(x)
        self.y = float(y)
        self.window.geometry(f"{self.w}x{self.h}+{int(self.x)}+{int(self.y)}")

        self.vy = 0.0
        self.landed = False

        self.hatch_delay = random.randint(cfg["hatch_min_ms"], cfg["hatch_max_ms"])
        self.window.after(self.hatch_delay, self.start_spin)

    def update(self):
        cfg = self.app.config

        if self.spinning:
            self.spin_frame = (self.spin_frame + 1) % cfg["spin_frame_count"]
            self.label.configure(image=self.app.egg_spin_frames[self.spin_frame])
            self.spin_ticks += 1
            if self.spin_ticks >= cfg["spin_ticks"]:
                self.do_hatch()
            return

        if self.landed:
            return
        self.vy += cfg["gravity"]
        self.y += self.vy
        screen_h = self.window.winfo_screenheight()
        if self.y >= screen_h - self.h:
            self.y = screen_h - self.h
            self.vy = 0.0
            self.landed = True
        self.window.geometry(f"+{int(self.x)}+{int(self.y)}")

    def start_spin(self):
        if self.hatched:
            return
        self.hatched = True
        self.spinning = True

    def do_hatch(self):
        spawn_x = self.x + self.w // 2 - self.app.dog_w // 2
        spawn_y = self.y - self.app.dog_h // 3
        dog = self.app.spawn_dog(spawn_x, spawn_y, fly_out=True)
        self.app._call_plugins("on_hatch", self, dog)
        if self in self.app.eggs:
            self.app.eggs.remove(self)
        self.destroy()

    def destroy(self):
        self.window.destroy()


class PluginBase:
    """插件基类，子类可重写需要的钩子方法"""

    def __init__(self, app):
        self.app = app

    def on_dog_spawn(self, dog):
        """一只狗被创建时调用"""
        pass

    def on_egg_spawn(self, egg):
        """一颗蛋被创建时调用"""
        pass

    def on_hatch(self, egg, dog):
        """蛋孵化出狗时调用"""
        pass

    def on_dog_click(self, dog, event):
        """狗被左键点击时调用"""
        pass

    def on_update(self, app):
        """每一帧更新时调用"""
        pass

    def on_quit(self, app):
        """程序退出时调用"""
        pass


class App:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config, self.config_msg = load_config(self.base_dir)
        cfg = self.config

        self.root = tk.Tk()
        self.root.withdraw()

        img_dir = os.path.join(self.base_dir, "images")

        # ---- 加载狗图片 ----
        dog_path = os.path.join(img_dir, "dogdogdog.png")
        if not os.path.exists(dog_path):
            messagebox.showerror(
                "启动失败",
                f"找不到小狗素材：\n{dog_path}\n\n请确认 images 文件夹中有 dogdogdog.png"
            )
            sys.exit(1)
        try:
            dog_original = Image.open(dog_path).convert("RGBA")
        except Exception as e:
            messagebox.showerror("启动失败", f"加载小狗素材失败：\n{e}")
            sys.exit(1)

        dog_ratio = cfg["dog_width"] / dog_original.width
        dog_h = max(1, int(dog_original.height * dog_ratio))
        dog_resized = dog_original.resize((cfg["dog_width"], dog_h), _LANCZOS)
        dog_bg = Image.new("RGB", dog_resized.size, (255, 0, 255))
        dog_bg.paste(dog_resized, (0, 0), dog_resized)
        self.dog_photo = ImageTk.PhotoImage(dog_bg)
        self.dog_w = cfg["dog_width"]
        self.dog_h = dog_h

        # ---- 加载鸵鸟蛋图片 ----
        egg_path = os.path.join(img_dir, "鸵鸟蛋.webp")
        if not os.path.exists(egg_path):
            messagebox.showerror(
                "启动失败",
                f"找不到鸵鸟蛋素材：\n{egg_path}\n\n请确认 images 文件夹中有 鸵鸟蛋.webp"
            )
            sys.exit(1)
        try:
            egg_original = Image.open(egg_path).convert("RGBA")
        except Exception as e:
            messagebox.showerror("启动失败", f"加载鸵鸟蛋素材失败：\n{e}")
            sys.exit(1)

        egg_ratio = cfg["egg_width"] / egg_original.width
        egg_h = max(1, int(egg_original.height * egg_ratio))
        egg_resized = egg_original.resize((cfg["egg_width"], egg_h), _LANCZOS)

        egg_bg = Image.new("RGB", egg_resized.size, (255, 0, 255))
        egg_bg.paste(egg_resized, (0, 0), egg_resized)
        self.egg_photo = ImageTk.PhotoImage(egg_bg)
        self.egg_w = cfg["egg_width"]
        self.egg_h = egg_h

        # 预生成蛋的旋转帧
        self.egg_spin_frames = []
        for i in range(cfg["spin_frame_count"]):
            angle = 360 / cfg["spin_frame_count"] * i
            rotated = egg_resized.rotate(angle, resample=_BICUBIC, expand=False)
            bg = Image.new("RGB", egg_resized.size, (255, 0, 255))
            bg.paste(rotated, (0, 0), rotated)
            self.egg_spin_frames.append(ImageTk.PhotoImage(bg))

        # ---- 列表 ----
        self.dogs = []
        self.eggs = []
        self.plugins = []

        # ---- 右键菜单 ----
        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="新增一颗蛋", command=lambda: self.spawn_egg())
        self.menu.add_separator()
        self.menu.add_command(label="退出", command=self.quit)

        # ---- 加载插件 ----
        if cfg["enable_plugins"]:
            self._load_plugins()

        # 初始一只狗
        self.spawn_dog()

        self.animate()
        self.root.mainloop()

    def _load_plugins(self):
        """扫描 plugins/ 目录加载插件"""
        plugins_dir = os.path.join(self.base_dir, "plugins")
        if not os.path.exists(plugins_dir):
            return
        for filename in sorted(os.listdir(plugins_dir)):
            if not filename.endswith(".py") or filename.startswith("_"):
                continue
            filepath = os.path.join(plugins_dir, filename)
            try:
                spec = importlib.util.spec_from_file_location(filename[:-3], filepath)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, "Plugin"):
                    plugin = module.Plugin(self)
                    self.plugins.append(plugin)
                    print(f"[Plugin] 已加载: {filename}")
                else:
                    print(f"[Plugin] 跳过 {filename}：未找到 Plugin 类")
            except Exception as e:
                print(f"[Plugin] 加载 {filename} 失败: {e}")
                traceback.print_exc()

    def _call_plugins(self, method_name, *args):
        """调用所有插件的指定钩子方法"""
        for plugin in self.plugins:
            try:
                method = getattr(plugin, method_name, None)
                if method:
                    method(*args)
            except Exception as e:
                print(f"[Plugin] {plugin.__class__.__name__}.{method_name} 出错: {e}")

    def spawn_dog(self, x=None, y=None, fly_out=False):
        if len(self.dogs) >= self.config["max_dogs"]:
            return None
        dog = Dog(self, x, y, fly_out=fly_out)
        self.dogs.append(dog)
        self._call_plugins("on_dog_spawn", dog)
        return dog

    def spawn_egg(self, x=None, y=None):
        if len(self.eggs) >= self.config["max_eggs"]:
            return
        if x is None:
            x = random.randint(0, self.root.winfo_screenwidth() - self.egg_w)
        if y is None:
            y = 0
        egg = Egg(self, x, y)
        self.eggs.append(egg)
        self._call_plugins("on_egg_spawn", egg)

    def animate(self):
        for dog in self.dogs:
            dog.update()
        for egg in self.eggs:
            egg.update()
        self._call_plugins("on_update", self)
        self.root.after(self.config["animate_interval"], self.animate)

    def show_menu(self, event):
        self.menu.tk_popup(event.x_root, event.y_root)

    def quit(self):
        self._call_plugins("on_quit", self)
        for dog in self.dogs:
            dog.destroy()
        for egg in self.eggs:
            egg.destroy()
        self.root.destroy()
        sys.exit(0)


def main():
    """带全局异常捕获的入口"""
    try:
        App()
    except Exception as e:
        error_detail = traceback.format_exc()
        print("=" * 50)
        print("程序启动失败，错误详情：")
        print("=" * 50)
        print(error_detail)
        print("=" * 50)
        # 尝试弹出错误框
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "小狗桌宠启动失败",
                f"错误信息：{e}\n\n"
                f"排查步骤：\n"
                f"1. 确认 Python 版本 >= 3.7（当前 {sys.version.split()[0]}）\n"
                f"2. 确认已安装 Pillow：pip install Pillow\n"
                f"3. 确认 images 文件夹中有 dogdogdog.png 和 鸵鸟蛋.webp\n"
                f"4. 详细错误已输出到控制台，请截图反馈\n\n"
                f"完整堆栈：\n{error_detail[:500]}"
            )
            root.destroy()
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
