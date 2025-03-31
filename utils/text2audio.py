from pathlib import Path
from openai import OpenAI
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def generate_audio(input_text, output_path="./生成的语音.mp3", voice="FunAudioLLM/CosyVoice2-0.5B:claire", model="FunAudioLLM/CosyVoice2-0.5B", format="mp3"):
    """
    生成语音文件
    
    参数:
        input_text: 要转换为语音的文本
        output_path: 输出文件路径
        voice: 语音音色
        model: 语音模型
        format: 输出格式
    """
    # 确保输出路径是Path对象
    speech_file_path = Path(output_path)
    
    # 初始化客户端
    client = OpenAI(
        api_key=os.getenv("SILICONFLOW_API_KEY"),
        base_url="https://api.siliconflow.cn/v1"
    )
    
    # 创建语音并保存
    with client.audio.speech.with_streaming_response.create(
        model=model,
        voice=voice,
        input=input_text,
        response_format=format
    ) as response:
        response.stream_to_file(speech_file_path)
    
    return speech_file_path

# 使用示例
if __name__ == "__main__":
    text = "人工智能是计算机科学的一个分支。"
    output_file = generate_audio(text)
    print(f"语音已生成并保存到: {output_file}") 