# 开源归属与实际改造

本项目为个人作品，使用 Codex 辅助开发。新增工作集中在 Harness 集成、文档处理与检索、幂等控制、界面和验收；基础模型、OCR 模型和底层推理库不是本项目原创。

- 句向量模型：[Sentence Transformers multilingual MiniLM](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)，模型卡标注 Apache-2.0。使用其 masked mean pooling 思路。
- ONNX 量化权重：[Xenova 转换版本](https://huggingface.co/Xenova/paraphrase-multilingual-MiniLM-L12-v2)，固定 revision `2c4055b12046f11709e9df2c122e59ffbdc2f900`。下载脚本保存文件哈希和版本，模型存放在用户指定目录，不提交权重到仓库。
- OCR 使用 [RapidOCR](https://github.com/RapidAI/RapidOCR) / rapidocr-onnxruntime；PDF 文本提取使用 pypdf，扫描页渲染使用 Poppler；图像处理使用 Pillow。
- 本地模型服务使用 [Ollama](https://github.com/ollama/ollama) 和用户已安装的 DeepSeek-R1；模型遵循各自分发条款。

依赖通过原分发渠道安装，其许可证随包保留。项目 MIT LICENSE 仅覆盖本项目适用代码，不替换第三方许可证。
