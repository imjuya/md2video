import asyncio
import argparse
import sys
import os
import logging
from pathlib import Path
from PIL import Image, ImageChops
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 检查必要的库是否安装
try:
    import selenium
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    print("错误: 请先安装 selenium 库 (pip install selenium)")
    sys.exit(1)

# 导入公共模块
from utils.paths import get_output_dir

# 确保logs目录存在
Path("logs").mkdir(exist_ok=True)

# 初始化日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"logs/{datetime.now().strftime('%Y%m%d_%H%M%S')}_html2img.log")
    ]
)
logger = logging.getLogger(__name__)

async def read_file_content(file_path):
    """读取文件内容"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        raise IOError(f"无法读取文件 {file_path}: {e}")

async def html_to_image(html_file, output_name, width=1920, height=1080):
    """将HTML文件转换为图片"""
    output_dir = get_output_dir("images")
    output_image = output_dir / f"{output_name}.png"

    
    # 设置Chrome选项
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 无头模式
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(f"--window-size={width},{height}")
    chrome_options.add_argument("--hide-scrollbars")
    
    # 创建Chrome浏览器实例
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # 获取HTML文件的绝对路径
        html_path = os.path.abspath(html_file)
        file_url = f"file:///{html_path}"
        
        # 加载HTML文件
        driver.get(file_url)
        
        # 等待页面加载完成
        import time
        time.sleep(1)  # 简单等待，确保页面完全渲染
        
        # 截图
        driver.save_screenshot(str(output_image))
        logger.info(f"已保存截图到 {output_image}")
        
        return True
    except Exception as e:
        print(f"截图过程中出错: {e}")
        return False
    finally:
        # 关闭浏览器
        driver.quit()

async def process_html_directory(html_dir, width=1920, height=1080):
    """处理HTML目录下的所有文件"""
    html_path = Path(html_dir)
    if not html_path.exists():
        raise FileNotFoundError(f"HTML目录不存在: {html_dir}")
    
    # 获取所有HTML文件（除了index.html）
    html_files = [f for f in html_path.glob("*.html") if f.name != "index.html"]
    html_files.sort(key=lambda x: int(x.stem.split('_')[1]) if x.stem.startswith('news_') else float('inf'))
    
    success_count = 0
    for html_file in html_files:
        output_name = html_file.stem
        try:
            success = await html_to_image(html_file, output_name, width, height)
            if success:
                success_count += 1
                logger.info(f"成功处理 {html_file.name}")
            else:
                logger.error(f"处理失败 {html_file.name}")
        except Exception as e:
            logger.error(f"处理 {html_file.name} 时出错: {e}")
    
    return success_count

async def main():
    parser = argparse.ArgumentParser(
        description="将HTML页面转换为截图",
        formatter_class=argparse.RawTextHelpFormatter)
    
    # 添加两种模式的参数组，但设置auto为默认值
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--manual", action="store_true",
                         help="手动模式，需要指定HTML文件和输出路径")
    mode_group.add_argument("--auto", action="store_true", default=True,
                         help="自动处理最新的输出目录中的HTML文件（默认模式）")
    
    parser.add_argument("--html", help="手动模式：要截图的HTML文件路径")
    parser.add_argument("--output", "-o", help="手动模式：截图保存路径")
    parser.add_argument("--width", "-w", type=int, default=1920,
                      help="截图宽度，默认1920像素")
    parser.add_argument("--height", "-ht", type=int, default=1080,
                      help="截图高度，默认1080像素")
    
    args = parser.parse_args()
    
    try:
        if args.manual:
            if not (args.html and args.output):
                parser.error("手动模式需要同时指定 --html 和 --output 参数")
            # 单文件处理模式
            success = await html_to_image(args.html, args.output, args.width, args.height)
            if not success:
                sys.exit(1)
        else:
            # 默认使用auto模式
            output_dir = Path("output")
            if not output_dir.exists():
                output_dir.mkdir(parents=True, exist_ok=True)
            
            date_dirs = sorted([d for d in output_dir.glob("*") 
                              if d.is_dir() and d.name.isdigit()], reverse=True)
            
            if not date_dirs:
                today_dir = output_dir / datetime.now().strftime("%Y%m%d")
                today_dir.mkdir(exist_ok=True)
                date_dirs = [today_dir]
            
            latest_dir = date_dirs[0]
            html_dir = latest_dir / "html"
            images_dir = latest_dir / "images"
            images_dir.mkdir(exist_ok=True)
            
            if not html_dir.exists():
                raise FileNotFoundError(f"HTML目录不存在: {html_dir}")
            
            logger.info(f"处理目录: {html_dir}")
            success_count = await process_html_directory(html_dir, args.width, args.height)
            logger.info(f"成功处理 {success_count} 个HTML文件")
            
    except Exception as e:
        logger.error(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
