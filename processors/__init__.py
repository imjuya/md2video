"""
处理器模块包含了将Markdown转换为视频的所有处理步骤。
"""

from .md2html import main as md2html_main
from .html2img import main as html2img_main
from .img2video import main as img2video_main
from .md2audio import process_markdown_file as md2audio_main 
