"""Convert markdown to HTML with timeline support."""
import asyncio
import json
import re
import sys
import argparse
import yaml
import os
import logging
from pathlib import Path
from openai import AsyncOpenAI
from dotenv import load_dotenv
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 加载 .env 文件
load_dotenv()

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
        logging.FileHandler(f"logs/{datetime.now().strftime('%Y%m%d_%H%M%S')}_md2html.log")
    ]
)
logger = logging.getLogger(__name__)

# 添加父目录到Python路径
sys.path.append(str(Path(__file__).parent))

async def read_file_content(file_path: Path) -> str:
    """读取文件内容"""
    try:
        return file_path.read_text(encoding='utf-8')
    except Exception as e:
        logger.error(f"无法读取文件 {file_path}: {e}")
        raise

def parse_markdown_content(content: str) -> list:
    """解析Markdown内容为新闻条目列表"""
    # 移除分隔符
    content = re.sub(r'---+', '', content)
    
    if not content.strip().startswith('##'):
        if '##' in content:
            content = f"## AI 行业早报\n{content.split('##')[0]}\n##" + '##'.join(content.split('##')[1:])
        else:
            content = f"## AI 行业早报\n{content}"
    
    sections = re.split(r'(?m)^##\s+', content)
    return [section.strip() for section in sections if section.strip()]

async def save_html_page(html_content: str, file_path: Path):
    """保存HTML页面"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(html_content, encoding='utf-8')
    logger.info(f"已保存HTML页面到 {file_path}")

async def create_index_page(titles: list, file_paths: list, output_dir: Path):
    """创建索引页面"""
    index_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI新闻页面索引</title>
    <style>
        body { font-family: 'Microsoft YaHei', Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f5f5f5; }
        h1 { color: #333; text-align: center; border-bottom: 2px solid #ddd; padding-bottom: 10px; }
        ul { list-style-type: none; padding: 0; }
        li { margin: 10px 0; padding: 15px; background-color: #fff; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        a { color: #0066cc; text-decoration: none; font-size: 18px; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>AI新闻页面索引</h1>
    <ul>
"""
    for i, (title, file_path) in enumerate(zip(titles, file_paths)):
        rel_path = file_path.relative_to(output_dir)
        clean_title = title.replace('##', '').strip() or f"新闻 {i+1}"
        index_content += f'        <li><a href="{rel_path}" target="_blank">{clean_title}</a></li>\n'
    
    index_content += """    </ul>
</body>
</html>"""
    
    index_path = output_dir / "index.html"
    index_path.write_text(index_content, encoding='utf-8')
    logger.info(f"已保存索引页面到 {index_path}")

async def generate_html_for_news(news_content: str, client: AsyncOpenAI, system_prompt: str, index: int) -> str:
    """为新闻生成HTML页面"""
    logger.info(f"正在为新闻 {index+1} 生成HTML页面...")
    
    try:
        # 准备请求参数
        completion_params = {
            "model": client.model,
            "temperature": 0.7,  # 直接在API调用时设置temperature
            "max_tokens": 4000,  # 设置最大token数
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"以下为新闻文章的内容：\n{news_content}"}
            ]
        }
        
        response = await client.chat.completions.create(**completion_params)
        clean_response = response.choices[0].message.content.strip()
        
        if clean_response.startswith("```html"):
            clean_response = clean_response[7:]
        elif clean_response.startswith("```"):
            clean_response = clean_response[3:]
        
        if clean_response.endswith("```"):
            clean_response = clean_response[:-3]
        
        if not clean_response.startswith(("<!DOCTYPE", "<html")):
            logger.warning("返回的内容不是有效的HTML，使用默认模板")
            return generate_default_html(news_content, index)
        
        return clean_response.strip()
    except Exception as e:
        logger.error(f"生成HTML时发生错误: {e}")
        return generate_default_html(news_content, index)

def generate_default_html(news_content: str, index: int) -> str:
    """生成默认HTML模板"""
    lines = news_content.strip().split('\n')
    title = lines[0].replace('##', '').strip() if lines else f"新闻 {index+1}"
    content = '\n'.join(lines[1:]) if len(lines) > 1 else ""
    
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        p {{ margin-bottom: 15px; }}
        @media (max-width: 768px) {{ body {{ padding: 15px; }} }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div>{content.replace('\n', '<br>')}</div>
</body>
</html>"""

async def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="生成HTML静态页面")
    parser.add_argument("--output", "-o", default="html_pages", help="HTML页面输出目录")
    parser.add_argument("--content", "-c", default="newsText.md", help="内容文件路径")
    args = parser.parse_args()

    try:
        # 获取标准输出目录
        output_dir = get_output_dir("html")
        
        # 读取内容文件
        md_content = await read_file_content(Path(args.content))
        
        # 读取配置文件
        with open('llmConfig.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            md2html_config = config['md2html']
        
        # 从环境变量获取 API key
        api_key = os.getenv('LLM_API_KEY')
        if not api_key:
            raise ValueError("未找到环境变量 LLM_API_KEY，请在 .env 文件中设置")
        
        # 创建OpenAI客户端
        client = AsyncOpenAI(
            base_url=md2html_config['base_url'],
            api_key=api_key,
            timeout=60.0,  # 设置超时时间
            max_retries=3  # 设置最大重试次数
        )
        # 设置模型名称
        client.model = md2html_config['name']
        
        # 解析内容
        news_items = parse_markdown_content(md_content)
        logger.info(f"共解析出 {len(news_items)} 条新闻")
        
        # 处理每条新闻
        file_paths = []
        titles = []
        for i, news_item in enumerate(news_items):
            title_match = re.search(r'^## (.+?)(\n|$)', news_item)
            title = f"## {title_match.group(1).strip()}" if title_match else f"## 新闻 {i+1}"
            titles.append(title)
            
            # 生成并保存HTML
            html_content = await generate_html_for_news(news_item, client, md2html_config['system_prompt'], i)
            file_path = output_dir / f"news_{i+1}.html"
            await save_html_page(html_content, file_path)
            file_paths.append(file_path)
        
        # 创建索引
        await create_index_page(titles, file_paths, output_dir)
               
        logger.info("处理完成！")
    except Exception as e:
        logger.error(f"处理失败: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
