# -*- coding: utf-8 -*-
"""
小狗桌宠
- 显示在桌面最上层，四处游荡
- 左键点击任意一只狗 -> 生出一颗鸵鸟蛋（重力掉落到底部）
- 鸵鸟蛋 10~20 秒后开始孵化：飞快旋转 -> 小狗破蛋飞出 -> 蛋消失
- 每只狗的移动速度独立随机
- 右键 -> 弹出菜单（新增一只狗 / 新增一颗蛋 / 退出）
"""

import tkinter as tk
import random
import sys
import os
from PIL import Image, ImageTk

# ========== 配置 ==========
DOG_WIDTH = 140              # 狗的显示宽度（像素）
EGG_WIDTH = 90               # 鸵鸟蛋的显示宽度
MOVE_SPEED_MIN = 0.6         # 狗移动速度下限（像素/帧），慢的慢悠悠
MOVE_SPEED_MAX = 6.5         # 狗移动速度上限，快的飞快窜
GRAVITY = 0.6                # 蛋的重力加速度（像素/帧²）
HATCH_MIN_MS = 10000         # 孵化最短时间（毫秒）
HATCH_MAX_MS = 20000         # 孵化最长时间
SPIN_TICKS = 45              # 孵化旋转持续帧数（45*30ms≈1.35秒）
SPIN_FRAME_COUNT = 12        # 旋转一圈的帧数
ANIMATE_INTERVAL = 30        # 动画帧间隔（毫秒），约33fps
CHANGE_DIR_CHANCE = 0.02     # 狗每帧随机变向概率
MAX_DOGS = 50                # 最大狗数量
MAX_EGGS = 30                # 最大蛋数量
TRANSPARENT_COLOR = "magenta"  # 窗口透明色
# ==========================


class Dog:
    """每只狗对应一个无边框透明置顶窗口"""

    def __init__(self, app, x=None, y=None, fly_out=False):
        self.app = app
        self.w = app.dog_w
        self.h = app.dog_h

        # 创建窗口
        self.window = tk.Toplevel(app.root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-transparentcolor", TRANSPARENT_COLOR)
        self.window.configure(bg=TRANSPARENT_COLOR)

        self.label = tk.Label(
            self.window,
            image=app.dog_photo,
            bg=TRANSPARENT_COLOR,
            bd=0,
            highlightthickness=0,
        )
        self.label.pack()

        self.label.bind("<Button-1>", self.on_left_click)
        self.label.bind("<Button-3>", app.show_menu)

        # 初始位置
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

        # 破蛋飞出模式：先向上弹，再恢复正常游荡
        self.fly_out = fly_out
        self.fly_ticks = 0
        if fly_out:
            self.dy = -9.0
            self.dx = random.uniform(-3.5, 3.5)
        else:
            self._random_speed()

    def _random_speed(self):
        """每只狗独立随机速度和方向"""
        speed = random.uniform(MOVE_SPEED_MIN, MOVE_SPEED_MAX)
        self.dx = speed * random.choice([-1, 1]) * (0.4 + random.random() * 0.6)
        self.dy = speed * random.choice([-1, 1]) * (0.4 + random.random() * 0.6)
        if abs(self.dx) < 0.3:
            self.dx = 1.0 if self.dx >= 0 else -1.0
        if abs(self.dy) < 0.3:
            self.dy = 1.0 if self.dy >= 0 else -1.0

    def update(self):
        # 破蛋飞出阶段：受重力下落，到期后切换为正常游荡
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

        # 正常游荡
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

        if random.random() < CHANGE_DIR_CHANCE:
            self.dx += random.uniform(-1.0, 1.0)
            self.dy += random.uniform(-1.0, 1.0)
            speed = (self.dx ** 2 + self.dy ** 2) ** 0.5
            if speed > MOVE_SPEED_MAX * 1.5:
                scale = MOVE_SPEED_MAX / speed
                self.dx *= scale
                self.dy *= scale

        self.window.geometry(f"+{int(self.x)}+{int(self.y)}")

    def on_left_click(self, event):
        """左键点击：生出一颗鸵鸟蛋"""
        offset_x = random.randint(-20, 20)
        self.app.spawn_egg(self.x + offset_x + self.w // 4, self.y)

    def destroy(self):
        self.window.destroy()


class Egg:
    """鸵鸟蛋：重力掉落 -> 10~20秒后旋转孵化 -> 小狗破蛋飞出"""

    def __init__(self, app, x, y):
        self.app = app
        self.w = app.egg_w
        self.h = app.egg_h
        self.hatched = False
        self.spinning = False
        self.spin_frame = 0
        self.spin_ticks = 0

        # 创建窗口
        self.window = tk.Toplevel(app.root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-transparentcolor", TRANSPARENT_COLOR)
        self.window.configure(bg=TRANSPARENT_COLOR)

        self.label = tk.Label(
            self.window,
            image=app.egg_photo,
            bg=TRANSPARENT_COLOR,
            bd=0,
            highlightthickness=0,
        )
        self.label.pack()
        self.label.bind("<Button-3>", app.show_menu)

        # 初始位置
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        x = max(0, min(x, screen_w - self.w))
        y = max(0, min(y, screen_h - self.h))
        self.x = float(x)
        self.y = float(y)
        self.window.geometry(f"{self.w}x{self.h}+{int(self.x)}+{int(self.y)}")

        # 物理
        self.vy = 0.0
        self.landed = False

        # 安排孵化倒计时
        self.hatch_delay = random.randint(HATCH_MIN_MS, HATCH_MAX_MS)
        self.window.after(self.hatch_delay, self.start_spin)

    def update(self):
        if self.spinning:
            # 飞快旋转：逐帧切换旋转图片
            self.spin_frame = (self.spin_frame + 1) % SPIN_FRAME_COUNT
            self.label.configure(image=self.app.egg_spin_frames[self.spin_frame])
            self.spin_ticks += 1
            if self.spin_ticks >= SPIN_TICKS:
                self.do_hatch()
            return

        # 重力下落
        if self.landed:
            return
        self.vy += GRAVITY
        self.y += self.vy
        screen_h = self.window.winfo_screenheight()
        if self.y >= screen_h - self.h:
            self.y = screen_h - self.h
            self.vy = 0.0
            self.landed = True
        self.window.geometry(f"+{int(self.x)}+{int(self.y)}")

    def start_spin(self):
        """倒计时结束，开始旋转孵化动画"""
        if self.hatched:
            return
        self.hatched = True  # 防止重复触发
        self.spinning = True

    def do_hatch(self):
        """旋转结束：小狗破蛋飞出，蛋消失"""
        # 在蛋的位置生成一只狗，带飞出动画
        spawn_x = self.x + self.w // 2 - self.app.dog_w // 2
        spawn_y = self.y - self.app.dog_h // 3
        self.app.spawn_dog(spawn_x, spawn_y, fly_out=True)
        # 移除并销毁蛋
        if self in self.app.eggs:
            self.app.eggs.remove(self)
        self.destroy()

    def destroy(self):
        self.window.destroy()


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()

        base_dir = os.path.dirname(os.path.abspath(__file__))
        img_dir = os.path.join(base_dir, "images")

        # ---- 加载狗图片 ----
        dog_path = os.path.join(img_dir, "dogdogdog.png")
        if not os.path.exists(dog_path):
            tk.messagebox.showerror("错误", f"找不到图片：{dog_path}")
            sys.exit(1)
        dog_original = Image.open(dog_path).convert("RGBA")
        dog_ratio = DOG_WIDTH / dog_original.width
        dog_h = max(1, int(dog_original.height * dog_ratio))
        dog_resized = dog_original.resize((DOG_WIDTH, dog_h), Image.Resampling.LANCZOS)
        dog_bg = Image.new("RGB", dog_resized.size, (255, 0, 255))
        dog_bg.paste(dog_resized, (0, 0), dog_resized)
        self.dog_photo = ImageTk.PhotoImage(dog_bg)
        self.dog_w = DOG_WIDTH
        self.dog_h = dog_h

        # ---- 加载鸵鸟蛋图片 ----
        egg_path = os.path.join(img_dir, "鸵鸟蛋.webp")
        if not os.path.exists(egg_path):
            tk.messagebox.showerror("错误", f"找不到图片：{egg_path}")
            sys.exit(1)
        egg_original = Image.open(egg_path).convert("RGBA")
        egg_ratio = EGG_WIDTH / egg_original.width
        egg_h = max(1, int(egg_original.height * egg_ratio))
        egg_resized = egg_original.resize((EGG_WIDTH, egg_h), Image.Resampling.LANCZOS)

        # 蛋的静态图
        egg_bg = Image.new("RGB", egg_resized.size, (255, 0, 255))
        egg_bg.paste(egg_resized, (0, 0), egg_resized)
        self.egg_photo = ImageTk.PhotoImage(egg_bg)
        self.egg_w = EGG_WIDTH
        self.egg_h = egg_h

        # 预生成蛋的旋转帧（孵化动画用）
        self.egg_spin_frames = []
        for i in range(SPIN_FRAME_COUNT):
            angle = 360 / SPIN_FRAME_COUNT * i
            rotated = egg_resized.rotate(angle, resample=Image.BICUBIC, expand=False)
            bg = Image.new("RGB", egg_resized.size, (255, 0, 255))
            bg.paste(rotated, (0, 0), rotated)
            self.egg_spin_frames.append(ImageTk.PhotoImage(bg))

        # ---- 列表 ----
        self.dogs = []
        self.eggs = []

        # ---- 右键菜单 ----
        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="新增一颗蛋", command=lambda: self.spawn_egg())
        self.menu.add_separator()
        self.menu.add_command(label="退出", command=self.quit)

        # 初始一只狗
        self.spawn_dog()

        self.animate()
        self.root.mainloop()

    def spawn_dog(self, x=None, y=None, fly_out=False):
        if len(self.dogs) >= MAX_DOGS:
            return
        dog = Dog(self, x, y, fly_out=fly_out)
        self.dogs.append(dog)

    def spawn_egg(self, x=None, y=None):
        if len(self.eggs) >= MAX_EGGS:
            return
        if x is None:
            x = random.randint(0, self.root.winfo_screenwidth() - self.egg_w)
        if y is None:
            y = 0
        egg = Egg(self, x, y)
        self.eggs.append(egg)

    def animate(self):
        for dog in self.dogs:
            dog.update()
        for egg in self.eggs:
            egg.update()
        self.root.after(ANIMATE_INTERVAL, self.animate)

    def show_menu(self, event):
        self.menu.tk_popup(event.x_root, event.y_root)

    def quit(self):
        for dog in self.dogs:
            dog.destroy()
        for egg in self.eggs:
            egg.destroy()
        self.root.destroy()
        sys.exit(0)


if __name__ == "__main__":
    App()
