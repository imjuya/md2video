"""Convert images to video with timeline support."""
import json
import subprocess
import tempfile
import sys
import logging
from pathlib import Path
from datetime import timedelta, datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
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
        logging.FileHandler(f"logs/{datetime.now().strftime('%Y%m%d_%H%M%S')}_img2video.log")
    ]
)
logger = logging.getLogger(__name__)

def time_str_to_seconds(time_str):
    """将字幕格式的时间字符串 (HH:MM:SS,mmm) 转换为秒数"""
    time_str = time_str.replace(',', '.')
    hours, minutes, seconds = time_str.split(':')
    return float(hours) * 3600 + float(minutes) * 60 + float(seconds)

def find_audio_file(audio_dir):
    """查找目录中唯一的MP3文件"""
    audio_path = Path(audio_dir)
    if not audio_path.exists():
        logger.error(f"音频目录不存在: {audio_dir}")
        return None
    
    mp3_files = list(audio_path.glob("*.mp3"))
    if not mp3_files:
        logger.error(f"在目录 {audio_dir} 中未找到MP3文件")
        return None
    
    logger.info(f"找到音频文件: {mp3_files[0]}")
    return mp3_files[0]

def get_audio_duration(audio_file):
    """获取音频文件的时长（秒）"""
    cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', 
           '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_file)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())

def create_news_video(json_path, images_dir, output_name, output_dir, audio_dir="audio"):
    """创建新闻视频"""
    output_path = output_dir / f"video_{output_name}.mp4"
    temp_output = output_dir / f"temp_{output_name}.mp4"
    
    # 读取JSON文件
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    news_count = len(data['timeline'])
    logger.info(f"开始处理 {news_count} 条新闻")

    # 创建临时文件存储ffmpeg配置
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
        total_duration = 0
        for i in range(news_count):
            news = data['timeline'][i]
            image_path = Path(images_dir) / f"news_{i+1}.png"
            
            start_seconds = time_str_to_seconds(news['start_seconds'])
            end_seconds = time_str_to_seconds(news['end_seconds'])
            duration = end_seconds - start_seconds
            total_duration = max(total_duration, end_seconds)
            
            logger.debug(f"处理图片: {image_path}, 持续时间: {duration:.2f}秒")
            
            if image_path.exists():
                temp_file.write(f"file '{image_path.absolute()}'\n")
                temp_file.write(f"duration {duration}\n")
            else:
                logger.warning(f"找不到图片 {image_path}")
                continue
        
        if news_count > 0:
            last_image = Path(images_dir) / f"news_{news_count}.png"
            temp_file.write(f"file '{last_image.absolute()}'\n")

    # 构建ffmpeg命令 (对临时文件)
    ffmpeg_cmd = [
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', temp_file.name
    ]
    
    # 添加音频
    audio_file = find_audio_file(audio_dir)
    if audio_file:
        ffmpeg_cmd.extend([
            '-i', str(audio_file), '-c:v', 'libx264', '-preset', 'ultrafast',
            '-tune', 'stillimage', '-crf', '28', '-c:a', 'aac', '-b:a', '128k',
            '-shortest', '-vf', 'format=yuv420p,scale=1920:-2'
        ])
    else:
        ffmpeg_cmd.extend([
            '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'stillimage',
            '-crf', '28', '-vf', 'format=yuv420p,scale=1920:-2'
        ])
    
    ffmpeg_cmd.extend(['-threads', '0', str(temp_output)])

    try:
        logger.info("开始生成临时视频...")
        subprocess.run(ffmpeg_cmd, check=True)
        
        # 获取视频时长
        probe_cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1', str(temp_output)]
        result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        
        # 裁剪掉最后8秒
        trim_cmd = [
            'ffmpeg', '-y', '-i', str(temp_output),
            '-t', str(max(0, duration - 8)),  # 确保不会出现负数持续时间
            '-c', 'copy', str(output_path)
        ]
        
        logger.info("开始裁剪视频...")
        subprocess.run(trim_cmd, check=True)
        
        logger.info(f"视频生成成功: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"生成视频失败: {e}")
        return False
    finally:
        # 清理临时文件
        Path(temp_file.name).unlink(missing_ok=True)
        temp_output.unlink(missing_ok=True)

async def main():
    """主函数：将图片转换为视频"""
    # 自动查找最新的output/YYYYMMDD目录
    output_dir = Path("output")  # 直接使用项目根目录下的output文件夹
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"创建输出目录: {output_dir}")
    
    date_dirs = sorted([d for d in output_dir.glob("*") if d.is_dir() and d.name.isdigit()], 
                      reverse=True)
    
    if not date_dirs:
        # 如果没有日期目录，使用当前日期创建一个
        today_dir = output_dir / datetime.now().strftime("%Y%m%d")
        today_dir.mkdir(exist_ok=True)
        logger.info(f"创建新的日期目录: {today_dir}")
        date_dirs = [today_dir]
        
    latest_dir = date_dirs[0]
    logger.info(f"使用最新日期目录: {latest_dir}")
    
    # 查找目录中的JSON文件
    json_files = list(latest_dir.glob("*.json"))
    if not json_files:
        logger.error(f"在目录 {latest_dir} 中未找到JSON文件")
        return False
        
    json_path = json_files[0]
    images_dir = latest_dir / "images"
    
    if not images_dir.exists():
        logger.error(f"图片目录不存在: {images_dir}")
        return False
        
    # 使用日期作为输出文件名
    output_name = latest_dir.name
    
    return create_news_video(json_path, images_dir, output_name, 
                        output_dir=latest_dir,
                        audio_dir=str(latest_dir))

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
