# 行走之窗插件设计文档

## 概述

创建一个 AstrBot 插件，用于生成"行走之窗"风格的 meme 图片。用户发送 `/窗 文本内容` 命令，插件会在模板图的笔记本区域绘制文字并返回给用户。

## 功能需求

### 命令格式

```
/窗 这里是一句话
```

### 功能逻辑

1. 用户发送 `/窗` 命令
2. 解析命令后的文本内容
3. 如果没有文本内容，直接输出模板图
4. 如果有文本内容，在模板图的笔记本区域绘制文字
5. 发送生成的图片给用户

### 文字渲染规则

- **位置**：笔记本区域（由 config.json 配置）
- **对齐**：左对齐
- **颜色**：黑色 (0, 0, 0)
- **字号**：根据文本长度自动调整（在配置的 font_size_range 范围内）
- **换行**：自动换行以适应笔记本区域
- **内边距**：可配置的 padding 值

## 插件结构

```
astrbot_walking_window/
├── main.py                    # 插件入口
├── metadata.yaml              # 插件元数据
├── requirements.txt           # Python 依赖
├── templates/
│   ├── config.json            # 模板配置文件
│   └── template0.jpg          # 模板图
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-07-05-walking-window-design.md
└── README.md
```

## 模板配置

### config.json 结构

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

### 配置字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 模板名称（唯一标识） |
| file | string | 模板图文件名 |
| text_area.x1 | int | 文本区域左上角 X 坐标 |
| text_area.y1 | int | 文本区域左上角 Y 坐标 |
| text_area.x2 | int | 文本区域右下角 X 坐标 |
| text_area.y2 | int | 文本区域右下角 Y 坐标 |
| font_size_range | array[int] | 字号范围 [最小, 最大] |
| padding | int | 文本区域内边距（像素） |

## 技术实现

### 依赖

- `Pillow` (PIL) - Python 图像处理库

### 核心算法

1. **加载模板**：根据配置读取对应的模板图
2. **计算字号**：根据文本长度在 font_size_range 内动态调整
3. **文本换行**：使用 Pillow 的 `textwrap` 功能自动换行
4. **绘制文字**：在文本区域的指定位置绘制文字
5. **保存输出**：保存到临时文件并发送

### 关键代码逻辑

```python
# 伪代码
def generate_image(template_config, text):
    # 1. 加载模板
    img = Image.open(template_config['file'])

    # 2. 计算文本区域
    text_area = template_config['text_area']
    padding = template_config['padding']
    draw_area = (
        text_area['x1'] + padding,
        text_area['y1'] + padding,
        text_area['x2'] - padding,
        text_area['y2'] - padding
    )

    # 3. 计算字号
    font_size = calculate_font_size(text, draw_area)

    # 4. 换行处理
    wrapped_text = wrap_text(text, font_size, draw_area[2] - draw_area[0])

    # 5. 绘制文字
    draw = ImageDraw.Draw(img)
    draw.text((draw_area[0], draw_area[1]), wrapped_text, fill='black', font=font)

    # 6. 保存并返回
    img.save(output_path)
    return output_path
```

## 错误处理

1. **模板不存在**：记录错误日志，返回错误提示
2. **文本为空**：直接输出模板图
3. **图像处理失败**：记录错误日志，返回错误提示

## 扩展性

未来添加新模板只需：

1. 在 `templates/` 目录放入新模板图
2. 在 `config.json` 的 `templates` 数组中添加新配置项
3. 重启插件即可生效

## 测试用例

1. **基础功能**：`/窗 Hello World` → 生成带文字的图片
2. **空文本**：`/窗` → 输出原始模板图
3. **长文本**：`/窗 这是一段很长的测试文本...` → 自动换行并缩小字号
4. **短文本**：`/窗 Hi` → 使用较大字号
