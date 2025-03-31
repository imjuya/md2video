import asyncio
import logging
from datetime import datetime
from pathlib import Path

from processors import (
    md2html_main,
    html2img_main,
    img2video_main,
    md2audio_main
)

# 初始化日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"logs/{datetime.now().strftime('%Y%m%d_%H%M%S')}_main.log")
    ]
)
logger = logging.getLogger(__name__)

async def main():
    try:

        # 4. Markdown转音频
        logger.info("开始执行Markdown到音频的转换...")
        md2audio_main("audioText.md")  # 这个函数不是异步的
        logger.info("Markdown到音频转换完成")

        # 1. Markdown转HTML
        logger.info("开始执行Markdown到HTML的转换...")
        await md2html_main()
        logger.info("Markdown到HTML转换完成")

        # 2. HTML转图片
        logger.info("开始执行HTML到图片的转换...")
        await html2img_main()
        logger.info("HTML到图片转换完成")

        # 3. 图片转视频
        logger.info("开始执行图片到视频的转换...")
        await img2video_main()
        logger.info("图片到视频转换完成")

        logger.info("所有处理步骤已完成！")

    except Exception as e:
        logger.error(f"处理过程中出现错误: {e}")
        raise

if __name__ == "__main__":
    # 确保logs目录存在
    Path("logs").mkdir(exist_ok=True)
    
    # 运行主程序
    asyncio.run(main()) 