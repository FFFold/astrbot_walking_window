from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont
import textwrap
import tempfile
import uuid


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

    def _get_template_config(self, template_name=None):
        """获取指定模板的配置，如果没有指定则返回第一个模板"""
        templates = self.config.get("templates", [])
        if not templates:
            return None
        if template_name:
            for template in templates:
                if template.get("name") == template_name:
                    return template
        return templates[0] if templates else None

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
        
        font_size = self._calculate_font_size(text, font_size_range, draw_area_width, draw_area_height)
        font = self._get_font(font_size)
        
        wrapped_text = self._wrap_text(text, font_size, draw_area_width, font)
        
        # 计算文本总高度以实现垂直居中
        lines = wrapped_text.split('\n')
        line_height = font_size + 4
        total_text_height = len(lines) * line_height
        
        # 垂直居中：计算起始Y坐标
        y_offset = max(0, (draw_area_height - total_text_height) // 2)
        start_y = draw_area[1] + y_offset
        
        draw = ImageDraw.Draw(img)
        # 左对齐，垂直居中
        draw.text(
            (draw_area[0], start_y),
            wrapped_text,
            fill="black",
            font=font
        )
        
        # 使用唯一文件名避免并发冲突
        output_path = Path(tempfile.gettempdir()) / f"walking_window_{uuid.uuid4().hex}.png"
        img.save(output_path, "PNG")
        return output_path

    def _calculate_font_size(self, text, font_size_range, max_width, max_height):
        """根据文本长度和区域高度计算合适的字号"""
        min_size, max_size = font_size_range
        
        for size in range(max_size, min_size - 1, -1):
            font = self._get_font(size)
            # 使用正确的字符宽度估算
            avg_char_width = size * 0.6 if not self._has_cjk(text) else size
            lines = textwrap.wrap(text, width=max_width // avg_char_width)
            total_height = len(lines) * (size + 4)
            if total_height <= max_height:
                return size
        
        return min_size

    def _has_cjk(self, text):
        """检查文本是否包含CJK字符"""
        for char in text:
            if '\u4e00' <= char <= '\u9fff' or '\u3000' <= char <= '\u303f':
                return True
        return False

    def _get_font(self, size):
        """获取指定大小的字体，优先使用支持中文的字体"""
        # 尝试多种字体，优先使用支持中文的
        font_names = ["msyh.ttc", "simhei.ttf", "simsun.ttc", "arial.ttf"]
        for font_name in font_names:
            try:
                return ImageFont.truetype(font_name, size)
            except OSError:
                continue
        return ImageFont.load_default()

    def _wrap_text(self, text, font_size, max_width, font):
        """自动换行文本，支持中文"""
        # 根据是否包含CJK字符选择不同的宽度估算
        if self._has_cjk(text):
            avg_char_width = font_size  # CJK字符约为全角
        else:
            avg_char_width = font_size * 0.6  # 西文字符约为半角
        
        chars_per_line = max(1, int(max_width / avg_char_width))
        return textwrap.fill(text, width=chars_per_line)

    @filter.command("窗")
    async def walking_window(self, event: AstrMessageEvent, text: str = ""):
        """生成行走之窗风格的 meme 图片。用法：/窗 文本内容"""
        text = text.strip()
        
        template_config = self._get_template_config()
        if not template_config:
            yield event.plain_result("错误：没有可用的模板配置")
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
