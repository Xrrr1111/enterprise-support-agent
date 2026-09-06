# 企业知识与客服 Agent：启动与演示

在仓库根目录使用 Python 3.11+：

```powershell
python -m pip install -r requirements.txt
python -m enterprise_support_agent.web --port 8011
```

打开 http://127.0.0.1:8011 。默认使用确定性 Mock，订单是模拟数据。输入“检查订单 ORD-1002，并解释配送政策”，可查看订单工具、知识检索、工具观察、结果和轨迹。

真实模型需先启动已有的 Ollama 服务，然后设置环境变量再启动网页：

```powershell
$env:ESA_LLM_PROVIDER='ollama'
$env:ESA_LLM_MODEL='deepseek-r1:8b'
python -m enterprise_support_agent.web --port 8011
```

## 多模态与语义检索

上传 `demo_assets/member-delivery.md`、`fragile-policy.png`、`invoice-policy-scan.pdf`，分别询问“星云会员礼盒几天发出”“易碎品损坏举证时限”“发票申请和抬头修改”。可观察来源及可获取的页码；删除后重新询问，确认对应文档已从索引清理。

图片使用 RapidOCR；扫描 PDF 还需要 Poppler 的 pdftoppm 在 PATH 内，或通过 `ESA_PDFTOPPM_PATH` 指定其路径。依赖缺失会明确报告解析失败。

预训练语义检索需下载外部模型并设置路径；未配置时仅使用明确标识的 Hashing 基线，不等同于预训练语义理解：

```powershell
python scripts/download_embeddings.py --directory D:/models/multilingual-minilm
$env:ESA_EMBEDDING_MODEL_DIR='D:/models/multilingual-minilm'
python -m enterprise_support_agent.web --port 8011
```

模型来源、固定版本和归属见 [ATTRIBUTION.md](ATTRIBUTION.md)。项目不训练基础模型。上述路径是示例，请按本机修改。配置文件 `.env.example` 供参考，程序读取环境变量而不自动加载 `.env`。

## 验收与边界

```powershell
python -m pytest -q
python specs/verify.py --test
```

58 项自动化测试通过；3 份文件在真实 OCR 和预训练向量推理下完成解析、检索、来源显示、删除复查，Agent 控制采用脚本决策。另有一次真实模型订单查询通过；这不是泛化准确率评估。工单按幂等键防重，写操作不盲目自动重试；锁仅覆盖单进程。网页仅适用于本机演示，没有身份认证、订单归属验证和生产隔离。线程超时不能强行终止正在运行的代码。
