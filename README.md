# MD2Video

MD2Video 是一个强大的工具，可以将 Markdown 文档转换为视频内容。它支持将文本转换为语音，生成图片，并最终合成为视频。
## 缺点
- 只能处理一个音频文本和对应的文本
- 只能处理仅存在 ## 标记的 Markdown 文本，且文档开头需要是 ## 标记。


## 功能特点

- Markdown 转音频：将文档内容转换为自然的语音narration
- Markdown 转 HTML：保持文档的格式和样式
- HTML 转图片：生成高质量的内容截图
- 图片合成视频：将所有元素组合成完整视频

## 安装要求

- Python 3.8+
- Chrome浏览器（用于HTML渲染）
- FFmpeg（用于视频处理）

## 安装步骤

1. 克隆仓库：
```bash
git clone [repository-url]
cd md2video
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置环境变量：
   - 复制 `.env.example` 到 `.env`
   - 填入必要的API密钥

## 使用方法

1. 准备Markdown文件
2. 运行转换：
```bash
python main.py
```

## 项目结构

```
md2video/
├── main.py              # 主程序入口
├── processors/          # 处理器模块
├── utils/              # 工具函数
├── output/             # 输出目录
└── llmConfig.yaml      # LLM配置文件
```

## 注意事项

- 确保已正确配置所有API密钥
- 确保系统已安装FFmpeg
- 处理大文件时可能需要较长时间

## License

MIT 