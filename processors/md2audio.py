import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

import re
import logging
import json
from datetime import timedelta, date
from pydub import AudioSegment
from utils.text2audio import generate_audio

# 确保logs目录存在
Path("logs").mkdir(exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/{datetime.now().strftime('%Y%m%d_%H%M%S')}_md2audio.log"),
        logging.StreamHandler()
    ]
)

def format_time(milliseconds):
    """将毫秒转换为SRT格式的时间字符串 (HH:MM:SS,mmm)"""
    td = timedelta(milliseconds=milliseconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds % 1000:03}"

def generate_silence(duration=1000):
    """生成指定时长的无声音频（默认1秒）"""
    return AudioSegment.silent(duration=duration)  # 确保精确指定毫秒

def preprocess_text(text):
    """预处理文本，处理链接和图片等Markdown元素"""
    logging.debug(f"预处理前的文本: {text[:100]}..." if len(text) > 100 else f"预处理前的文本: {text}")
    
    # 处理链接 [文本](链接) -> 文本
    # 匹配 Markdown 链接，包括带空格的格式
    text = re.sub(r'\[(.*?)\][ ]*\(.*?\)', r'\1', text)
    logging.debug(f"处理链接后: {text[:100]}..." if len(text) > 100 else f"处理链接后: {text}")
    
    # 处理 Obsidian 格式图片，完全移除 ![[图片.png]]
    text = re.sub(r'!\[\[.*?\]\]', '', text)
    
    # 处理标准 Markdown 格式图片，完全移除 ![alt](url)
    text = re.sub(r'!\[.*?\][ ]*\(.*?\)', '', text)
    logging.debug(f"处理图片后: {text[:100]}..." if len(text) > 100 else f"处理图片后: {text}")
    
    # 将'-'替换为空格
    text = text.replace('-', ' ')
    
    # 将英文双引号转换为中文双引号
    text = text.replace('"', '“').replace('"', '”')
    
    # 处理英文句点，将其转换为中文句号
    text = re.sub(r'([.])(?=\s|$)', '。', text)
    
    # 移除多余空白字符
    text = re.sub(r'\s+', ' ', text).strip()
    
    logging.debug(f"最终预处理结果: {text[:100]}..." if len(text) > 100 else f"最终预处理结果: {text}")
    
    return text

def sanitize_filename(filename):
    """处理文件名，移除或替换非法字符"""
    # 将引号、空格和其他特殊字符替换为下划线
    filename = re.sub(r'["\'\s\\/:*?"<>|]', '_', filename)
    return filename

def save_timeline(timeline_data, current_date, output_dir):
    """保存时间轴数据到JSON文件"""
    timeline_path = output_dir / f"timeline_{current_date}.json"
    data = {
        "timeline": timeline_data
    }
    with open(timeline_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logging.info(f"时间轴数据已保存到: {timeline_path}")

def parse_markdown_and_generate_audio(markdown_content):
    """解析Markdown内容，提取标题和文本，生成语音和字幕"""
    logging.info("开始解析Markdown内容")
    
    # 初始化时间轴数据
    timeline_data = []
    
    # 获取第一个标题作为主文件名
    first_title_match = re.search(r'##\s+(.*?)(?=\n)', markdown_content)
    if not first_title_match:
        main_title = "未命名文档"
    else:
        main_title = first_title_match.group(1).strip()
    
    logging.info(f"主标题: {main_title}")
    
    # 获取当前日期并创建输出目录
    current_date = date.today().strftime("%Y%m%d")
    output_dir = Path("output") / current_date
    output_dir.mkdir(parents=True, exist_ok=True)
    logging.info(f"输出目录: {output_dir}")
    
    # 使用正则表达式找出所有## 开头的标题及其内容
    sections = re.findall(r'##\s+(.*?)(?=\n##|\Z)', markdown_content, re.DOTALL)
    logging.info(f"找到 {len(sections)} 个章节")
    
    # 生成SRT文件内容
    srt_content = []
    current_time = 0
    sentence_index = 1
    
    # 创建一个合并的音频文件
    combined_audio = AudioSegment.empty()
    
    # 处理所有章节
    for section_idx, section in enumerate(sections):
        logging.info(f"处理章节 {section_idx+1}/{len(sections)}")
        
        # 分离标题和内容
        lines = section.strip().split('\n')
        title = lines[0].strip()
        logging.info(f"章节标题: {title}")
        
        # 排除标题行，只保留内容
        content = '\n'.join(lines[1:]).strip()
        
        if not content:
            logging.warning(f"章节 '{title}' 没有内容，跳过")
            continue  # 跳过没有实际内容的小节
        
        # 首先预处理整个内容，移除链接格式和图片
        preprocessed_content = preprocess_text(content)
        logging.info(f"章节预处理后内容: {preprocessed_content[:100]}..." if len(preprocessed_content) > 100 else f"章节预处理后内容: {preprocessed_content}")
        
        # 按句号分割内容 - 修改分割逻辑
        sentences = re.split(r'([。?!，])', preprocessed_content)  # 同时处理中英文标点
        
        # 重新组合句子和标点
        complete_sentences = []
        i = 0
        while i < len(sentences):
            if i + 1 < len(sentences) and sentences[i+1] in '。?!，':
                complete_sentences.append(sentences[i] + sentences[i+1])
                i += 2
            else:
                if sentences[i].strip():  # 只添加非空句子
                    complete_sentences.append(sentences[i] + '。')  # 为没有标点的句子添加句号
                i += 1
        
        logging.debug(f"组合后句子数量: {len(complete_sentences)}")
        
        # 过滤空句子
        complete_sentences = [s.strip() for s in complete_sentences if s.strip()]
        logging.info(f"过滤后句子数量: {len(complete_sentences)}")
        
        # 记录章节开始时间
        section_start_time = format_time(current_time)
        
        # 处理每个句子
        for i, sentence in enumerate(complete_sentences, 1):
            logging.info(f"处理句子 {i}/{len(complete_sentences)}")
            logging.debug(f"处理后的句子: {sentence}")
            
            try:
                # 如果句子为空，跳过
                if not sentence.strip():
                    logging.warning(f"句子为空，跳过")
                    continue
                
                # 生成安全的文件名
                safe_title = sanitize_filename(title)
                audio_path = output_dir / f"temp-{safe_title}-{i}.mp3"
                
                logging.info(f"生成音频: {audio_path}")
                logging.debug(f"音频文本: {sentence}")
                
                try:
                    generate_audio(sentence, str(audio_path))
                    logging.info("音频生成成功")
                except Exception as e:
                    logging.error(f"生成音频时出错: {e}")
                    continue
                
                # 获取音频时长
                try:
                    audio = AudioSegment.from_file(audio_path)
                    duration = len(audio)  # 毫秒
                    logging.info(f"音频时长: {duration}毫秒")
                except Exception as e:
                    logging.error(f"读取音频文件时出错: {e}")
                    if os.path.exists(audio_path):
                        os.remove(audio_path)
                    continue
                
                # 添加到合并音频
                combined_audio += audio
                
                # 添加到SRT内容
                start_time = current_time
                end_time = current_time + duration
                
                srt_content.append(f"{sentence_index}\n{format_time(start_time)} --> {format_time(end_time)}\n{sentence}\n")
                logging.debug(f"添加字幕: {sentence_index}, {format_time(start_time)} --> {format_time(end_time)}")
                
                current_time = end_time
                sentence_index += 1
                
                # 删除临时音频文件
                os.remove(audio_path)
                logging.debug("删除临时音频文件")
                
                # 如果不是本章节的最后一个句子，则在句子之间添加0.3秒的停顿
                if i < len(complete_sentences):
                    # 添加0.3秒的无声
                    short_silence = generate_silence(300)  # 300毫秒 = 0.3秒
                    combined_audio += short_silence
                    
                    # 更新时间，但不添加字幕
                    current_time += 300
                    logging.debug("添加短暂停顿: 300毫秒")
            except Exception as e:
                logging.error(f"处理句子时出错: {e}")
                continue
            
        # 如果不是最后一个章节，添加1秒钟的无声音频
        if section_idx < len(sections) - 1:
            silence = generate_silence()
            combined_audio += silence
            current_time += 1000
            logging.debug("章节之间添加停顿: 1000毫秒")
            
        # 添加到时间轴 - 使用不同的结束时间逻辑
        if section_idx == len(sections) - 1:
            # 最后一个章节使用当前时间作为结束时间
            section_end_time = format_time(current_time)
        else:
            # 非最后章节使用下一章节开始时间作为结束时间
            section_end_time = format_time(current_time)  # 包含了过渡的1秒
            
        timeline_data.append({
            "title": title,
            "start_seconds": section_start_time,
            "end_seconds": section_end_time
        })
    
    # 保存合并的音频文件
    try:
        combined_audio_path = output_dir / f"audio_{current_date}.mp3"
        logging.info(f"保存合并音频文件: {combined_audio_path}")
        combined_audio.export(str(combined_audio_path), format="mp3")
        logging.info("音频文件保存成功")
    except Exception as e:
        logging.error(f"保存合并音频文件时出错: {e}")
    
    # 写入单个SRT文件
    try:
        srt_path = output_dir / f"subtitle_{current_date}.srt"
        logging.info(f"保存字幕文件: {srt_path}")
        with open(srt_path, "w", encoding="utf-8") as srt_file:
            srt_file.write("\n".join(srt_content))
        logging.info("字幕文件保存成功")
    except Exception as e:
        logging.error(f"保存字幕文件时出错: {e}")
    
    # 保存时间轴数据
    save_timeline(timeline_data, current_date, output_dir)
    
    logging.info(f"已生成合并音频文件: {combined_audio_path}")
    logging.info(f"已生成字幕文件: {srt_path}")
    logging.info(f"已生成时间轴文件: {output_dir / f'timeline_{current_date}.json'}")
    
    print(f"已生成合并音频文件: {combined_audio_path}")
    print(f"已生成字幕文件: {srt_path}")
    print(f"已生成时间轴文件: {output_dir / f'timeline_{current_date}.json'}")
    print(f"共处理了 {sentence_index-1} 个句子")

def process_markdown_file(file_path):
    """处理Markdown文件"""
    logging.info(f"开始处理Markdown文件: {file_path}")
    
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            markdown_content = file.read()
        logging.info(f"成功读取文件，内容长度: {len(markdown_content)} 字符")
    except Exception as e:
        logging.error(f"读取文件时出错: {e}")
        return
    
    parse_markdown_and_generate_audio(markdown_content)

if __name__ == "__main__":
    # 示例使用
    markdown_file = "./audioText.md"
    
    # 如果文件不存在，创建一个示例Markdown文件
    if not os.path.exists(markdown_file):
        example_content = """## 人工智能简介
        
人工智能是计算机科学的一个分支。它企图了解智能的实质。
人工智能是对人的意识、思维的信息过程的模拟。
人工智能不是人的智能，但能像人那样思考、也可能超过人的智能。

## 机器学习基础
        
机器学习是人工智能的一个分支。
机器学习使用算法解析数据、从中学习、然后对真实世界中的事件做出决策和预测。
传统上，计算机程序只能根据开发人员的设计执行特定指令。
        """
        
        with open(markdown_file, "w", encoding="utf-8") as file:
            file.write(example_content)
        
        print(f"已创建示例Markdown文件: {markdown_file}")
    
    process_markdown_file(markdown_file)
