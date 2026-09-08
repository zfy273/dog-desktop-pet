# 插件开发指南

本文档介绍如何为小狗桌宠编写插件。

## 目录

- [插件是什么](#插件是什么)
- [插件的放置与加载](#插件的放置与加载)
- [插件基本结构](#插件基本结构)
- [钩子方法大全](#钩子方法大全)
- [可用 API 参考](#可用-api-参考)
- [完整示例](#完整示例)
- [注意事项](#注意事项)

## 插件是什么

插件是放在 `plugins/` 目录下的 Python 文件，可以在不修改主程序代码的情况下扩展桌宠的功能。插件通过钩子（hook）机制监听程序中的各种事件，并在事件发生时执行自定义逻辑。

你可以用插件实现：
- 统计狗和蛋的数量
- 给狗添加特殊行为
- 记录运行日志
- 播放音效
- 与其他程序交互
- 等等

## 插件的放置与加载

1. 将插件文件（`.py`）放入项目根目录下的 `plugins/` 文件夹
2. 文件名以 `.py` 结尾，且不以 `_` 开头
3. 程序启动时自动扫描并加载所有符合条件的插件
4. 插件按文件名排序依次加载

禁用插件的方法：
- 删除插件文件
- 或将文件改名为下划线开头（如 `_myplugin.py`）

在 `config.json` 中设置 `"enable_plugins": false` 可全局禁用所有插件。

## 插件基本结构

每个插件文件必须定义一个名为 `Plugin` 的类，类的 `__init__` 方法接收一个 `app` 参数（主程序实例）。

```python
# plugins/my_plugin.py

class Plugin:
    def __init__(self, app):
        self.app = app
        # 在这里做初始化工作

    def on_dog_spawn(self, dog):
        # 重写你需要的钩子方法
        pass
```

你不需要继承任何基类，只需要定义 `Plugin` 类并实现你需要的钩子方法即可。未实现的方法会被自动跳过。

## 钩子方法大全

以下是所有可用的钩子方法，按调用时机排列：

### on_dog_spawn(self, dog)

一只小狗被创建时调用。

参数：
- `dog`：新创建的 `Dog` 实例

可访问的属性：
- `dog.x`, `dog.y`：位置（浮点数）
- `dog.dx`, `dog.dy`：移动速度
- `dog.w`, `dog.h`：尺寸
- `dog.window`：tkinter Toplevel 窗口
- `dog.label`：显示图片的 Label 控件

### on_egg_spawn(self, egg)

一颗鸵鸟蛋被创建时调用。

参数：
- `egg`：新创建的 `Egg` 实例

可访问的属性：
- `egg.x`, `egg.y`：位置
- `egg.w`, `egg.h`：尺寸
- `egg.hatch_delay`：孵化倒计时（毫秒）
- `egg.landed`：是否已落地
- `egg.window`：tkinter Toplevel 窗口

### on_hatch(self, egg, dog)

蛋完成孵化、小狗破壳而出时调用。

参数：
- `egg`：孵化的蛋（即将被销毁）
- `dog`：刚孵化出的小狗实例

### on_dog_click(self, dog, event)

小狗被鼠标左键点击时调用（在蛋生成之后调用）。

参数：
- `dog`：被点击的狗
- `event`：tkinter 鼠标事件对象（包含 `x`, `y`, `x_root`, `y_root` 等）

### on_update(self, app)

每一帧动画更新时调用（默认约 33 帧/秒，由 `config.json` 中的 `animate_interval` 控制）。

参数：
- `app`：主程序实例

注意：此方法调用频率很高，避免做耗时操作，否则会影响动画流畅度。

### on_quit(self, app)

程序退出时调用（在所有窗口销毁之前）。

参数：
- `app`：主程序实例

## 可用 API 参考

插件通过 `self.app` 可以访问主程序的所有公开属性和方法。

### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `app.config` | dict | 当前配置（来自 config.json，合并了默认值） |
| `app.dogs` | list | 当前所有狗的列表 |
| `app.eggs` | list | 当前所有蛋的列表 |
| `app.plugins` | list | 当前所有已加载插件的列表 |
| `app.root` | tk.Tk | 主窗口（隐藏状态） |
| `app.dog_w`, `app.dog_h` | int | 狗的尺寸 |
| `app.egg_w`, `app.egg_h` | int | 蛋的尺寸 |
| `app.dog_photo` | PhotoImage | 狗的图片 |
| `app.egg_photo` | PhotoImage | 蛋的静态图片 |
| `app.egg_spin_frames` | list | 蛋的旋转帧图片列表 |
| `app.base_dir` | str | 程序所在目录的绝对路径 |

### 方法

| 方法 | 说明 |
|------|------|
| `app.spawn_dog(x=None, y=None, fly_out=False)` | 生成一只新狗，返回 Dog 实例或 None（达到上限时） |
| `app.spawn_egg(x=None, y=None)` | 生成一颗新蛋 |
| `app.show_menu(event)` | 在指定位置弹出右键菜单 |
| `app.quit()` | 退出程序 |

### 配置项

通过 `app.config` 可以读取所有配置项，完整列表见 `config.json` 或主 README。

## 完整示例

### 示例一：活动监视器（已内置）

见 `plugins/example_monitor.py`，演示了所有钩子方法的用法，在控制台打印事件信息。

### 示例二：自动繁殖插件

每隔一段时间自动生成一颗蛋，让狗的数量自动增长。

```python
# plugins/auto_breed.py

import random


class Plugin:
    def __init__(self, app):
        self.app = app
        self.frame = 0
        self.breed_interval = 600  # 约每20秒自动生一颗蛋

    def on_update(self, app):
        self.frame += 1
        if self.frame % self.breed_interval == 0:
            if len(app.eggs) < app.config["max_eggs"]:
                # 在屏幕随机位置生成一颗蛋
                x = random.randint(0, app.root.winfo_screenwidth() - app.egg_w)
                app.spawn_egg(x, 0)
                print("[自动繁殖] 生成了一颗新蛋")
```

### 示例三：限速插件

当狗的数量超过阈值时，限制新狗的生成速度。

```python
# plugins/population_control.py

class Plugin:
    def __init__(self, app):
        self.app = app
        self.max_dogs_before_slow = 20

    def on_dog_spawn(self, dog):
        if len(self.app.dogs) > self.max_dogs_before_slow:
            # 狗太多了，让新狗移动慢一些
            dog.dx *= 0.5
            dog.dy *= 0.5
```

### 示例四：点击计数插件

统计总共点击了多少次狗。

```python
# plugins/click_counter.py

class Plugin:
    def __init__(self, app):
        self.app = app
        self.click_count = 0

    def on_dog_click(self, dog, event):
        self.click_count += 1
        print(f"[点击统计] 总点击次数：{self.click_count}")
```

## 注意事项

1. **异常隔离**：单个插件的钩子方法抛出异常不会导致程序崩溃，错误会打印到控制台。但请尽量在插件内部处理好异常。

2. **性能**：`on_update` 每帧都会调用，不要在里面做文件读写、网络请求等耗时操作。如果需要，可以用计数器降低执行频率。

3. **线程安全**：所有钩子方法都在主线程（tkinter 事件循环）中调用，不要在插件中创建新线程操作 tkinter 控件。

4. **窗口操作**：插件可以直接操作 `dog.window` 或 `egg.window`（tkinter Toplevel），但请小心，不当操作可能导致显示异常。

5. **插件顺序**：插件按文件名字典序加载，`on_update` 等钩子也按此顺序调用。

6. **配置读取**：插件应通过 `app.config` 读取配置，不要自己解析 `config.json`。

7. **资源路径**：如果插件需要读取外部文件，使用 `app.base_dir` 构建绝对路径，不要依赖相对路径。

8. **Python 版本**：插件代码需兼容 Python 3.7 及以上版本。
