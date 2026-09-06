# AI SDD 功能交付记录

## 需求与验收边界

`specs/traceability.json` 是可执行关联表。项目只把能够由代码和测试证明的能力标记为完成；订单数据为模拟数据，本地 hashing 检索不等同于生产级向量模型。

## 设计

- `AgentLoop` 只接收模型决策，所有工具必须经过 `ToolHarness`。
- `MultimodalKnowledgeStore` 负责解析、OCR、分块、索引与删除一致性，`CombinedKnowledgeRetriever` 将上传资料并入客服工具。
- `create_ticket` 以调用方幂等键和请求指纹组合防止未知结果重试造成重复工单。
- `AgentState.to_dict()` 从真实工具观察生成来源列表，网页不自行补造来源。

## 任务与可执行验收

1. 运行 `python -m pytest -q`，覆盖正常、非法参数、失败、超时、循环、OCR、来源和删除。
2. 运行 `python scripts/generate_demo_assets.py`，生成文本、图片和扫描 PDF 三类固定演示素材。
3. 设置 `ESA_PDFTOPPM_PATH` 后分别上传三类素材，检索结果必须返回对应文件；PDF/图片必须显示 `rapidocr` 解析器。
4. 运行工作区 `python delivery/verify_sdd.py`，每个需求必须关联存在的实现文件和测试文件。

## 一次真实需求变更记录（2026-09-06）

- 需求变化：把“非幂等工具不重试”加强为“即使客户端因未知结果重放请求，也不能重复建单”。
- 实现变化：`TicketStore.create` 新增 `idempotency_key`、请求指纹、重复命中返回与冲突拒绝。
- 测试变化：新增同请求去重和同键异请求拒绝用例。
- 验收结果：见工作区 `delivery/acceptance-report.md`，不在此手工填写通过率。
