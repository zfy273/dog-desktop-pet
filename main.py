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
            image=app.current_dog_photo,
            bg=cfg["transparent_color"],
            bd=0,
            highlightthickness=0,
        )
        self.label.pack()

        self.label.bind("<Button-1>", self.on_left_click)
        self.label.bind("<Button-3>", app.show_dog_menu)

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

        # 压扁状态（被捶打）
        self.squash_level = 0.0  # 0=正常, 1=完全压扁
        self.original_w = self.w
        self.original_h = self.h
        self._squash_photo = None  # 保持动态图片引用防止GC

    def _random_speed(self):
        """每只狗独立随机速度和方向，应用当前皮肤的速度倍率"""
        cfg = self.app.config
        speed_mult = self.app.dog_skins[self.app.current_skin]["speed_multiplier"]
        speed = random.uniform(cfg["move_speed_min"], cfg["move_speed_max"]) * speed_mult
        self.dx = speed * random.choice([-1, 1]) * (0.4 + random.random() * 0.6)
        self.dy = speed * random.choice([-1, 1]) * (0.4 + random.random() * 0.6)
        if abs(self.dx) < 0.3:
            self.dx = 1.0 if self.dx >= 0 else -1.0
        if abs(self.dy) < 0.3:
            self.dy = 1.0 if self.dy >= 0 else -1.0

    def update(self):
        cfg = self.app.config

        # 压扁恢复（5秒内逐渐恢复，类似海绵回弹）
        if self.squash_level > 0:
            self.squash_level -= 1.0 / 167  # 约5秒恢复（30ms/帧）
            if self.squash_level < 0:
                self.squash_level = 0
            self._update_squash_image()
            if self.squash_level == 0:
                # 恢复完成，切回正常皮肤图片
                self.apply_current_skin()

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
        """左键点击：手从上落下捶打这只狗，狗被压扁"""
        self.app.spawn_hand(self)
        self.app._call_plugins("on_dog_click", self, event)

    def squash(self):
        """被捶打：完全压扁"""
        self.squash_level = 1.0
        self._update_squash_image()

    def _update_squash_image(self):
        """根据压扁程度动态缩放图片，保持底部位置不变"""
        original_img = self.app.dog_skins[self.app.current_skin]["original"]
        # 压扁：高度减小60%，宽度增加30%（类似海绵）
        new_w = int(self.original_w * (1 + 0.3 * self.squash_level))
        new_h = max(1, int(self.original_h * (1 - 0.6 * self.squash_level)))
        squashed = original_img.resize((new_w, new_h), _LANCZOS)
        bg = Image.new("RGB", squashed.size, (255, 0, 255))
        bg.paste(squashed, (0, 0), squashed)
        self._squash_photo = ImageTk.PhotoImage(bg)
        self.label.configure(image=self._squash_photo)
        # 保持底部位置不变
        bottom = self.y + self.h
        self.w = new_w
        self.h = new_h
        self.y = max(0, bottom - new_h)
        self.window.geometry(f"{self.w}x{self.h}+{int(self.x)}+{int(self.y)}")

    def apply_current_skin(self):
        """切换到当前皮肤，保持底部位置不变"""
        skin = self.app.dog_skins[self.app.current_skin]
        photo = skin["photo"]
        w = skin["w"]
        h = skin["h"]
        bottom = self.y + self.h
        self.original_w = w
        self.original_h = h
        self.w = w
        self.h = h
        self.y = max(0, bottom - h)
        self.label.configure(image=photo)
        self.window.geometry(f"{self.w}x{self.h}+{int(self.x)}+{int(self.y)}")

    def destroy(self):
        self.window.destroy()


class Egg:
    """鸵鸟蛋：重力掉落 -> 10~20秒后旋转孵化 -> 小狗破蛋飞出"""

    def __init__(self, app, x, y):
        self.app = app
        cfg = app.config

        # 选择蛋图片：当前皮肤有自定义蛋则用皮肤的，否则用默认
        skin = app.dog_skins[app.current_skin]
        if skin["egg_photo"] is not None:
            self.egg_photo = skin["egg_photo"]
            self.egg_spin_frames = skin["egg_spin_frames"]
        else:
            self.egg_photo = app.egg_photo
            self.egg_spin_frames = app.egg_spin_frames
        self.w = self.egg_photo.width()
        self.h = self.egg_photo.height()
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
            image=self.egg_photo,
            bg=cfg["transparent_color"],
            bd=0,
            highlightthickness=0,
        )
        self.label.pack()
        self.label.bind("<Button-3>", app.show_egg_menu)

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
            self.label.configure(image=self.egg_spin_frames[self.spin_frame])
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


class Hand:
    """捶打动画：手从上方落下，打到狗后狗被压扁，手停留几帧后消失"""

    def __init__(self, app, target_dog):
        self.app = app
        self.target = target_dog
        cfg = app.config
        self.w = app.hand_w
        self.h = app.hand_h

        self.window = tk.Toplevel(app.root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-transparentcolor", cfg["transparent_color"])
        self.window.configure(bg=cfg["transparent_color"])

        self.label = tk.Label(
            self.window,
            image=app.hand_photo,
            bg=cfg["transparent_color"],
            bd=0,
            highlightthickness=0,
        )
        self.label.pack()

        # 初始位置在狗的正上方（高出屏幕一段距离）
        self.x = target_dog.x + target_dog.w // 2 - self.w // 2
        self.y = target_dog.y - self.h - 200
        self.dy = 0.0
        self.hit = False
        self.stay_ticks = 0
        self.window.geometry(f"{self.w}x{self.h}+{int(self.x)}+{int(self.y)}")

    def update(self):
        if not self.hit:
            # 重力加速下落
            self.dy += 2.5
            self.y += self.dy
            # 检测是否打到狗（手的底部到达狗的上部）
            dog_top = self.target.y + self.target.h * 0.15
            if self.y + self.h >= dog_top:
                self.hit = True
                self.target.squash()
                self.stay_ticks = 6  # 打中后停留6帧
            self.window.geometry(f"+{int(self.x)}+{int(self.y)}")
        else:
            self.stay_ticks -= 1
            if self.stay_ticks <= 0:
                self.destroy()
                return False
        return True

    def destroy(self):
        self.window.destroy()
        if self in self.app.hands:
            self.app.hands.remove(self)


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

    def on_collision(self, dog1, dog2):
        """两只狗相撞时调用"""
        pass

    def on_speak(self, dog, text):
        """狗说话时调用"""
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

        # ---- 扫描 skins/ 目录加载所有皮肤包 ----
        self.dog_skins = {}  # {id: {"photo","original","w","h","name","speed_multiplier","egg_photo"}}
        skins_dir = os.path.join(self.base_dir, "skins")
        if os.path.exists(skins_dir):
            for skin_dir_name in sorted(os.listdir(skins_dir)):
                skin_dir = os.path.join(skins_dir, skin_dir_name)
                if not os.path.isdir(skin_dir):
                    continue
                skin_json_path = os.path.join(skin_dir, "skin.json")
                if not os.path.exists(skin_json_path):
                    continue
                try:
                    with open(skin_json_path, "r", encoding="utf-8") as f:
                        skin_config = json.load(f)
                except Exception as e:
                    print(f"[警告] 皮肤 {skin_dir_name} 的 skin.json 加载失败：{e}")
                    continue

                skin_id = skin_config.get("id", skin_dir_name)
                skin_name = skin_config.get("name", skin_dir_name)
                dog_image_file = skin_config.get("dog_image", "dog.png")
                egg_image_file = skin_config.get("egg_image", None)
                skin_width = skin_config.get("width", cfg["dog_width"])
                speed_multiplier = float(skin_config.get("speed_multiplier", 1.0))

                dog_image_path = os.path.join(skin_dir, dog_image_file)
                if not os.path.exists(dog_image_path):
                    print(f"[警告] 皮肤 {skin_name} 的狗图片不存在：{dog_image_path}")
                    continue
                try:
                    skin_img = Image.open(dog_image_path).convert("RGBA")
                except Exception as e:
                    print(f"[警告] 皮肤 {skin_name} 图片加载失败：{e}")
                    continue

                skin_ratio = skin_width / skin_img.width
                skin_h = max(1, int(skin_img.height * skin_ratio))
                skin_resized = skin_img.resize((skin_width, skin_h), _LANCZOS)
                skin_bg = Image.new("RGB", skin_resized.size, (255, 0, 255))
                skin_bg.paste(skin_resized, (0, 0), skin_resized)
                photo = ImageTk.PhotoImage(skin_bg)

                # 皮肤自定义蛋图片（可选）
                egg_photo = None
                egg_spin_frames = None
                if egg_image_file:
                    egg_image_path = os.path.join(skin_dir, egg_image_file)
                    if os.path.exists(egg_image_path):
                        try:
                            egg_img = Image.open(egg_image_path).convert("RGBA")
                            egg_ratio = cfg["egg_width"] / egg_img.width
                            egg_h = max(1, int(egg_img.height * egg_ratio))
                            egg_resized = egg_img.resize((cfg["egg_width"], egg_h), _LANCZOS)
                            egg_bg = Image.new("RGB", egg_resized.size, (255, 0, 255))
                            egg_bg.paste(egg_resized, (0, 0), egg_resized)
                            egg_photo = ImageTk.PhotoImage(egg_bg)
                            # 预生成旋转帧
                            egg_spin_frames = []
                            for i in range(cfg["spin_frame_count"]):
                                angle = 360 / cfg["spin_frame_count"] * i
                                rotated = egg_resized.rotate(angle, resample=_BICUBIC, expand=False)
                                rbg = Image.new("RGB", egg_resized.size, (255, 0, 255))
                                rbg.paste(rotated, (0, 0), rotated)
                                egg_spin_frames.append(ImageTk.PhotoImage(rbg))
                        except Exception as e:
                            print(f"[警告] 皮肤 {skin_name} 的蛋图片加载失败：{e}")

                self.dog_skins[skin_id] = {
                    "photo": photo,
                    "original": skin_resized,
                    "w": skin_width,
                    "h": skin_h,
                    "name": skin_name,
                    "speed_multiplier": speed_multiplier,
                    "egg_photo": egg_photo,
                    "egg_spin_frames": egg_spin_frames,
                }

        if not self.dog_skins:
            messagebox.showerror(
                "启动失败",
                "没有找到任何可用皮肤！\n请确认 skins/ 目录中至少有一个皮肤包（含 skin.json 和图片）。"
            )
            sys.exit(1)

        # 当前皮肤（默认第一个）
        self.current_skin = list(self.dog_skins.keys())[0]
        _cur = self.dog_skins[self.current_skin]
        self.current_dog_photo = _cur["photo"]
        self.dog_w = _cur["w"]
        self.dog_h = _cur["h"]

        # ---- 加载手部图片（捶打动画）----
        hand_path = os.path.join(img_dir, "hand.webp")
        if not os.path.exists(hand_path):
            messagebox.showerror(
                "启动失败",
                f"找不到手部素材：\n{hand_path}\n\n请确认 images 文件夹中有 hand.webp"
            )
            sys.exit(1)
        try:
            hand_original = Image.open(hand_path).convert("RGBA")
        except Exception as e:
            messagebox.showerror("启动失败", f"加载手部素材失败：\n{e}")
            sys.exit(1)
        hand_w = 100
        hand_ratio = hand_w / hand_original.width
        hand_h = max(1, int(hand_original.height * hand_ratio))
        hand_resized = hand_original.resize((hand_w, hand_h), _LANCZOS)
        hand_bg = Image.new("RGB", hand_resized.size, (255, 0, 255))
        hand_bg.paste(hand_resized, (0, 0), hand_resized)
        self.hand_photo = ImageTk.PhotoImage(hand_bg)
        self.hand_w = hand_w
        self.hand_h = hand_h

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
        self.hands = []
        self.plugins = []

        # ---- 事件总线 ----
        self.event_bus = {}  # {event_name: [callback, ...]}

        # ---- 插件注册的自定义右键菜单项 ----
        self.custom_dog_menu_items = []  # [(label, callback)]
        self.custom_egg_menu_items = []  # [(label, callback)]

        # ---- 先加载插件（插件可注册自定义菜单项）----
        if cfg["enable_plugins"]:
            self._load_plugins()

        # ---- 右键菜单 ----
        # 狗的菜单（带换肤子菜单 + 插件自定义项）
        self.dog_menu = tk.Menu(self.root, tearoff=0)
        self.dog_menu.add_command(label="新增一颗蛋", command=lambda: self.spawn_egg())
        self.dog_menu.add_separator()
        self.skin_menu = tk.Menu(self.dog_menu, tearoff=0)
        for skin_id, skin_data in self.dog_skins.items():
            self.skin_menu.add_command(
                label=skin_data["name"],
                command=lambda sid=skin_id: self.change_skin(sid)
            )
        self.dog_menu.add_cascade(label="换肤", menu=self.skin_menu)
        # 插件注册的自定义菜单项
        for label, callback in self.custom_dog_menu_items:
            self.dog_menu.add_command(label=label, command=callback)
        self.dog_menu.add_separator()
        self.dog_menu.add_command(label="退出", command=self.quit)

        # 蛋的菜单（插件自定义项）
        self.egg_menu = tk.Menu(self.root, tearoff=0)
        self.egg_menu.add_command(label="新增一颗蛋", command=lambda: self.spawn_egg())
        for label, callback in self.custom_egg_menu_items:
            self.egg_menu.add_command(label=label, command=callback)
        self.egg_menu.add_separator()
        self.egg_menu.add_command(label="退出", command=self.quit)

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

    # ========== 事件总线 ==========
    def subscribe(self, event_name, callback):
        """插件订阅事件"""
        if event_name not in self.event_bus:
            self.event_bus[event_name] = []
        self.event_bus[event_name].append(callback)

    def publish(self, event_name, *args, **kwargs):
        """发布事件，通知所有订阅者"""
        callbacks = self.event_bus.get(event_name, [])
        for cb in callbacks:
            try:
                cb(*args, **kwargs)
            except Exception as e:
                print(f"[EventBus] {event_name} 回调出错: {e}")

    # ========== 插件注册自定义菜单 ==========
    def register_dog_menu_item(self, label, callback):
        """插件注册狗的右键菜单项（需在菜单创建前调用）"""
        self.custom_dog_menu_items.append((label, callback))

    def register_egg_menu_item(self, label, callback):
        """插件注册蛋的右键菜单项（需在菜单创建前调用）"""
        self.custom_egg_menu_items.append((label, callback))

    # ========== 狗相撞检测 ==========
    def _check_collisions(self):
        """检测狗之间的碰撞，触发 on_collision 钩子"""
        dogs = self.dogs
        for i in range(len(dogs)):
            for j in range(i + 1, len(dogs)):
                d1, d2 = dogs[i], dogs[j]
                # 简单矩形碰撞检测
                if (d1.x < d2.x + d2.w and d1.x + d1.w > d2.x and
                        d1.y < d2.y + d2.h and d1.y + d1.h > d2.y):
                    self._call_plugins("on_collision", d1, d2)
                    self.publish("collision", d1, d2)

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

    def spawn_hand(self, target_dog):
        """生成一只手，从上落下捶打目标狗"""
        hand = Hand(self, target_dog)
        self.hands.append(hand)

    def animate(self):
        for dog in self.dogs:
            dog.update()
        for egg in self.eggs:
            egg.update()
        for hand in self.hands[:]:
            hand.update()
        self._check_collisions()
        self._call_plugins("on_update", self)
        self.root.after(self.config["animate_interval"], self.animate)

    def change_skin(self, skin_name):
        """切换所有狗的皮肤，保持底部位置不变"""
        if skin_name not in self.dog_skins:
            return
        self.current_skin = skin_name
        skin = self.dog_skins[skin_name]
        self.current_dog_photo = skin["photo"]
        self.dog_w = skin["w"]
        self.dog_h = skin["h"]
        for dog in self.dogs:
            dog.apply_current_skin()

    def show_dog_menu(self, event):
        """右键狗：弹出带换肤的菜单"""
        self.dog_menu.tk_popup(event.x_root, event.y_root)

    def show_egg_menu(self, event):
        """右键蛋：弹出简单菜单"""
        self.egg_menu.tk_popup(event.x_root, event.y_root)

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
