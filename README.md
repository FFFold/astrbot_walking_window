# astrbot_walking_window

生成"行走之窗"风格的 meme 图片

## 功能

用户发送 `/窗 文本内容` 命令，插件会在模板图的笔记本区域绘制文字并返回给用户。

## 命令格式

```
/窗 这里是一句话
```

- 如果没有文本内容，直接输出模板图
- 如果有文本内容，在模板图的笔记本区域绘制文字（左对齐+上下居中）

## 配置

模板配置文件位于 `templates/config.json`：

```json
{
  "templates": [
    {
      "name": "模板名称",
      "file": "模板图文件名",
      "text_area": {
        "x1": 左边界,
        "y1": 上边界,
        "x2": 右边界,
        "y2": 下边界
      },
      "font_size_range": [最小字号, 最大字号],
      "padding": 内边距
    }
  ]
}
```

## 添加新模板

1. 在 `templates/` 目录放入新模板图
2. 在 `templates/config.json` 的 `templates` 数组中添加新配置项
3. 重启插件即可生效

## 依赖

- Pillow >= 10.0.0
