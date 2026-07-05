# 行走之窗插件实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建一个 AstrBot 插件，用户发送 `/窗 文本` 命令后，在模板图的笔记本区域绘制文字并返回图片

**Architecture:** 使用 Pillow 库在模板图上绘制文字，通过 JSON 配置文件定义模板参数，支持多模板扩展

**Tech Stack:** Python, Pillow (PIL), AstrBot Plugin API

---

## 文件结构

```
astrbot_walking_window/
├── main.py                    # 插件入口，命令处理
├── metadata.yaml              # 插件元数据
├── requirements.txt           # Python 依赖
├── templates/
│   ├── config.json            # 模板配置
│   └── template0.jpg          # 模板图（已存在）
└── README.md
```

---

### Task 1: 创建插件元数据文件

**Files:**
- Create: `metadata.yaml`

- [ ] **Step 1: 创建 metadata.yaml**

```yaml
name: astrbot_walking_window
author: assistant
desc: 生成"行走之窗"风格的 meme 图片
version: "1.0.0"
display_name: 行走之窗
short_desc: 在模板图上绘制文字生成 meme
```

- [ ] **Step 2: 验证文件格式**

Run: `cat metadata.yaml`
Expected: 显示 YAML 内容

---

### Task 2: 创建依赖文件

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: 创建 requirements.txt**

```
Pillow>=10.0.0
```

- [ ] **Step 2: 验证文件内容**

Run: `cat requirements.txt`
Expected: 显示 `Pillow>=10.0.0`

---

### Task 3: 创建模板配置文件

**Files:**
- Create: `templates/config.json`

- [ ] **Step 1: 创建 config.json**

```json
{
  "templates": [
    {
      "name": "template0",
      "file": "template0.jpg",
      "text_area": {
        "x1": 195,
        "y1": 95,
        "x2": 465,
        "y2": 335
      },
      "font_size_range": [14, 36],
      "padding": 10
    }
  ]
}
```

- [ ] **Step 2: 验证 JSON 格式**

Run: `python -c "import json; json.load(open('templates/config.json'))"`
Expected: 无错误输出

---

### Task 4: 创建插件主文件 - 基础结构

**Files:**
- Create: `main.py`

- [ ] **Step 1: 创建 main.py 基础结构**

```python
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star
from astrbot.api import logger
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont
import textwrap
import tempfile


class WalkingWindowPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.plugin_dir = Path(__file__).parent
        self.templates_dir = self.plugin_dir / "templates"
        self.config = self._load_config()

    def _load_config(self):
        """加载模板配置"""
        config_path = self.templates_dir / "config.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"templates": []}

    def _get_template_config(self, template_name):
        """获取指定模板的配置"""
        for template in self.config.get("templates", []):
            if template.get("name") == template_name:
                return template
        return None

    def _generate_image(self, template_config, text):
        """在模板图上绘制文字并返回输出路径"""
        template_path = self.templates_dir / template_config["file"]
        img = Image.open(template_path)
        
        text_area = template_config["text_area"]
        padding = template_config.get("padding", 10)
        font_size_range = template_config.get("font_size_range", [14, 36])
        
        draw_area = (
            text_area["x1"] + padding,
            text_area["y1"] + padding,
            text_area["x2"] - padding,
            text_area["y2"] - padding
        )
        
        draw_area_width = draw_area[2] - draw_area[0]
        draw_area_height = draw_area[3] - draw_area[1]
        
        font_size = self._calculate_font_size(text, font_size_range, draw_area_width)
        font = self._get_font(font_size)
        
        wrapped_text = self._wrap_text(text, font_size, draw_area_width, font)
        
        draw = ImageDraw.Draw(img)
        draw.text(
            (draw_area[0], draw_area[1]),
            wrapped_text,
            fill="black",
            font=font
        )
        
        output_path = Path(tempfile.gettempdir()) / "walking_window_output.png"
        img.save(output_path, "PNG")
        return output_path

    def _calculate_font_size(self, text, font_size_range, max_width):
        """根据文本长度计算合适的字号"""
        min_size, max_size = font_size_range
        
        for size in range(max_size, min_size - 1, -1):
            font = self._get_font(size)
            lines = textwrap.wrap(text, width=max_width // size)
            if len(lines) * (size + 4) <= 200:
                return size
        
        return min_size

    def _get_font(self, size):
        """获取指定大小的字体"""
        try:
            return ImageFont.truetype("arial.ttf", size)
        except OSError:
            return ImageFont.load_default()

    def _wrap_text(self, text, font_size, max_width, font):
        """自动换行文本"""
        avg_char_width = font_size * 0.6
        chars_per_line = int(max_width / avg_char_width)
        return textwrap.fill(text, width=chars_per_line)

    @filter.command("窗")
    async def walking_window(self, event: AstrMessageEvent):
        """生成行走之窗风格的 meme 图片"""
        message_str = event.message_str
        text = message_str.replace("/窗", "").strip()
        
        template_config = self._get_template_config("template0")
        if not template_config:
            yield event.plain_result("错误：模板配置不存在")
            return
        
        if not text:
            template_path = self.templates_dir / template_config["file"]
            yield event.image_result(str(template_path))
            return
        
        try:
            output_path = self._generate_image(template_config, text)
            yield event.image_result(str(output_path))
        except Exception as e:
            logger.error(f"生成图片失败: {e}")
            yield event.plain_result(f"生成图片失败: {e}")

    async def terminate(self):
        """插件卸载时调用"""
        pass
```

- [ ] **Step 2: 验证 Python 语法**

Run: `python -m py_compile main.py`
Expected: 无错误输出

---

### Task 5: 移动模板文件到子目录

**Files:**
- Modify: Move `template0.jpg` to `templates/template0.jpg`

- [ ] **Step 1: 移动模板文件**

Run: `mv template0.jpg templates/`
Expected: 文件移动成功

- [ ] **Step 2: 验证文件位置**

Run: `ls templates/`
Expected: 显示 `config.json` 和 `template0.jpg`

---

### Task 6: 功能测试 - 基础命令

**Files:**
- Test: `main.py` (通过 AstrBot 加载测试)

- [ ] **Step 1: 安装依赖**

Run: `pip install -r requirements.txt`
Expected: 安装成功

- [ ] **Step 2: 测试插件加载**

在 AstrBot 中重新加载插件，验证无错误

- [ ] **Step 3: 测试空文本命令**

发送: `/窗`
预期: 返回原始模板图

- [ ] **Step 4: 测试带文本命令**

发送: `/窗 Hello World`
预期: 返回带有文字的图片

---

### Task 7: 完善 README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 更新 README.md**

```markdown
# astrbot_walking_window

生成"行走之窗"风格的 meme 图片

## 功能

用户发送 `/窗 文本内容` 命令，插件会在模板图的笔记本区域绘制文字并返回给用户。

## 命令格式

```
/窗 这里是一句话
```

- 如果没有文本内容，直接输出模板图
- 如果有文本内容，在模板图的笔记本区域绘制文字

## 配置

模板配置文件位于 `templates/config.json`，支持以下配置：

- `templates`: 模板数组
  - `name`: 模板名称
  - `file`: 模板图文件名
  - `text_area`: 文本区域坐标
  - `font_size_range`: 字号范围
  - `padding`: 内边距

## 添加新模板

1. 在 `templates/` 目录放入新模板图
2. 在 `templates/config.json` 的 `templates` 数组中添加新配置项
3. 重启插件即可生效

## 依赖

- Pillow >= 10.0.0
```

- [ ] **Step 2: 验证 README 内容**

Run: `cat README.md`
Expected: 显示更新后的 README

---

## 自检清单

- [ ] 所有任务都有完整代码
- [ ] 无占位符或 TODO
- [ ] 文件路径一致
- [ ] 测试步骤完整
- [ ] 命令和预期输出明确
