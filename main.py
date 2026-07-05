from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont
import tempfile
import uuid


class WalkingWindowPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.plugin_dir = Path(__file__).parent
        self.templates_dir = self.plugin_dir / "templates"
        self.config = self._load_config()
        self._cached_font_path = None

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

        lines = self._wrap_text(text, draw_area_width, font)
        line_height = self._get_line_height(font)
        total_text_height = len(lines) * (line_height + 4)

        y_offset = max(0, (draw_area_height - total_text_height) // 2)
        start_y = draw_area[1] + y_offset

        draw = ImageDraw.Draw(img)
        y = start_y
        for line in lines:
            draw.text((draw_area[0], y), line, fill="black", font=font)
            y += line_height + 4

        output_path = Path(tempfile.gettempdir()) / f"walking_window_{uuid.uuid4().hex}.png"
        img.save(output_path, "PNG")
        return output_path

    def _calculate_font_size(self, text, font_size_range, max_width, max_height):
        """根据实际像素测量计算合适的字号"""
        min_size, max_size = font_size_range

        for size in range(max_size, min_size - 1, -1):
            font = self._get_font(size)
            lines = self._wrap_text(text, max_width, font)
            line_height = self._get_line_height(font)
            total_height = len(lines) * (line_height + 4)
            if total_height <= max_height:
                return size

        return min_size

    def _get_line_height(self, font):
        """获取字体实际行高"""
        bbox = font.getbbox("Ay")
        return bbox[3] - bbox[1]

    def _get_font(self, size):
        """获取指定大小的字体，优先使用支持中文的字体"""
        if self._cached_font_path:
            try:
                return ImageFont.truetype(self._cached_font_path, size)
            except (OSError, IOError):
                self._cached_font_path = None

        font_paths = [
            # Windows fonts
            "msyh.ttc", "simhei.ttf", "simsun.ttc", "msyhbd.ttc", "msyhl.ttc",
            # Debian/Ubuntu: wqy-microhei → .ttc
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            # Other distros: .ttf
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttf",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttf",
            # Noto CJK (opentype & truetype)
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansSC-Regular.otf",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansSC-Regular.ttf",
            # DroidSansFallback
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
            # AR PL UMing/UKai
            "/usr/share/fonts/truetype/arphic/uming.ttc",
            "/usr/share/fonts/truetype/arphic/ukai.ttc",
            # macOS
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/Arial.ttf",
            "arial.ttf",
        ]
        for font_path in font_paths:
            try:
                font = ImageFont.truetype(font_path, size)
                self._cached_font_path = font_path
                logger.info(f"已加载字体: {font_path}")
                return font
            except (OSError, IOError):
                continue

        font = self._find_font_fallback(size)
        if font:
            return font

        logger.warning("未找到中文字体！中文可能显示为方框。请安装中文字体包：apt-get install fonts-wqy-microhei")
        return ImageFont.load_default()

    def _find_font_fallback(self, size):
        """遍历常见字体目录寻找可用的 TrueType 字体"""
        scan_dirs = ["/usr/share/fonts/truetype", "/usr/share/fonts/opentype"]
        for scan_dir in scan_dirs:
            scan_path = Path(scan_dir)
            if not scan_path.exists():
                continue
            for ext in ("*.ttf", "*.ttc", "*.otf"):
                for font_file in sorted(scan_path.rglob(ext)):
                    try:
                        font = ImageFont.truetype(str(font_file), size)
                        self._cached_font_path = str(font_file)
                        logger.info(f"已自动发现并加载字体: {font_file}")
                        return font
                    except (OSError, IOError):
                        continue
        return None

    def _wrap_text(self, text, max_width, font):
        """按单词+像素宽度换行（英文保持单词完整，超宽单词逐字拆分）"""
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            if font.getbbox(test_line)[2] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                    current_line = ""
                if font.getbbox(word)[2] <= max_width:
                    current_line = word
                else:
                    for char in word:
                        char_test = current_line + char
                        if font.getbbox(char_test)[2] > max_width and current_line:
                            lines.append(current_line)
                            current_line = char
                        else:
                            current_line = char_test
        if current_line:
            lines.append(current_line)
        return lines

    @filter.command("窗")
    async def walking_window(self, event: AstrMessageEvent):
        """生成行走之窗风格的 meme 图片。用法：/窗 文本内容"""
        raw = event.get_message_text().strip() if hasattr(event, 'get_message_text') else event.message_str.strip()
        # 去掉第一个词（即命令及前缀，兼容任意唤醒符如 / ! # 等）
        first_space = raw.find(' ')
        text = raw[first_space:].strip() if first_space != -1 else ""
        
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
