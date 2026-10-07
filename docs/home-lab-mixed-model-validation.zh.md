# Home-Lab：CPA 订阅模型与 NVIDIA 开放模型统一验收

验收日期：2026-10-07（Asia/Shanghai）。角色定义参考 Knowledge 的 `docs/zh/ai-collaboration-guide/full-guide.md`，能力归类是候选分工，不是 hello 测试证明的能力排名。

## 已部署链路

```text
https://ai-internal.onwalk.net
  → Caddy TLS → New API :3000
                  ├→ CPA Codex / Claude / Google 实例
                  └→ LiteLLM :4000 → NVIDIA NIM
```

实际 Caddy 生效配置指向 `127.0.0.1:3000`。LiteLLM 仅监听 loopback。
New API 新增 `litellm-nvidia-open-models` 渠道，使用 LiteLLM 内部 master key；客户端继续使用 New API 用户 Key，NVIDIA Key 不传给客户端。
本轮从 Home-Lab 经 HTTPS 域名测试，不是异地客户端连通性测试。

## 新增模型

| 网关模型 ID | 最小问候结果 | 耗时 |
|---|---|---:|
| openai/gpt-oss-20b | 200，Hello! | 2.02s |
| nvidia/nemotron-3.5-lightning-30b-a3b | 200，Hello! | 13.41s |
| deepseek-ai/deepseek-v4.1-flash | 200，Hello! | 98.33s |
| z-ai/glm-5.3 | 200，有效问候 | 37.48s |
| z-ai/glm-5.3-flash | 200，有效问候 | 64.68s |

以上是本次单次请求耗时，不是稳定延迟统计或 SLA。NVIDIA 托管模型属于开放模型接入来源，许可仍应按每个模型核实。
目录没有目标 DeepSeek V4-Pro、MiniMax M3、Qwen3.8，不能用其他型号替代这些名字。
Kimi K3 上游直连测试 90 秒超时，本轮不加入网关渠道。AMD 无可用额度，保持停用。

## 混合目录与批测

统一目录从 42 增加到 47。所有 47 个目录 ID 都向聊天接口发送了最小问候请求，输出上限 512，单次 HTTP 超时 120 秒，并发 4。

- 31 个得到有效问候：CPA 商业订阅来源 26 个，NVIDIA 来源 5 个。GitOps 只注册这 31 个，统一入口不再暴露其余失败或未验收模型。
- 2 个 HTTP 200 但返回下线提示：claude-opus-4-6-thinking、claude-sonnet-4-6。
- 9 个其他失败：5 个旧 Claude 型号当前 503、2 个 Fable 型号 429、claude-opus-5-5 返回 400、gemini-3.1-flash-image 返回 429。
- 5 个 gpt-image 模型向聊天接口返回 503，图像生成协议尚未验收，不能判断图像能力不可用。

有效问候没有证明 streaming、工具调用、Responses、Messages 或真实工程任务已通过。
NVIDIA 目录的 80 个是上游目录数，不是当前网关的已验收模型数；完整发现快照见
`docs/home-lab/nvidia-model-catalog-20261007.txt`。

## 按协作指南定义角色

| 角色 | 指南职责 | 商业订阅候选 | 开放模型候选 | 后续验收 |
|---|---|---|---|---|
| Chat | 理解、讨论、拆解、协调 | gpt-6.1-sol、claude-sonnet-5-5 | Nemotron Lightning（候选） | 多轮理解、任务拆解 |
| Worker | 确定性任务，速度与成本 | gpt-6-luna、gemini-3.8-flash-high | gpt-oss-20b、DeepSeek V4.1 Flash | JSON、批处理、吞吐 |
| Engineer | 读写代码、调工具、运行测试 | gpt-6.1-sol、claude-sonnet-5-5 | GLM-5.3 | 仓库任务、工具闭环、测试 |
| Architect | 系统设计、选型、终审 | gpt-6-astra、claude-opus-5（候选） | 尚无指南代表模型通过 | 约束、方案权衡、交叉审查 |
| Researcher | 外部事实检索、引用、置信度 | gemini-pro-agent（候选） | Kimi K3 尚未通过 | 搜索工具与引用核验 |
| Specialist | 网安、数学、计算机操作专项 | 尚无指南代表模型通过 | MiniMax M3 / GLM Cyber 未接入 | 专项评测与工具环境 |

不把通用 GLM-5.3 标记成 GLM Cyber；不把 Nemotron Lightning 标记成 Nemotron Ultra。
角色可以交叉，同一模型可承担多个角色。模型、工具、Harness 与验证共同决定任务能力。

## 凭据与持久性

NVIDIA 凭据：`kv/uat/ai-aggregator/litellm/providers/nvidia`，字段 `endpoint` 与 `api_key`。
现有 Vault policy `ai-aggregator-homelab-uat` 仅增加此精确路径的 read 权限。
原有主机加密 Vault 身份已通过独立 systemd 任务验证，可刷新全部运行时配置。

NVIDIA Key 注入 `/run/ai-aggregator/litellm.env`（tmpfs、root、0600）。模型配置仅引用 `os.environ/NVIDIA_API_KEY`。
持久的非敏感模型清单写入 `/etc/ai-aggregator/home-lab.json` 的 `nvidia_models`；现有 `vault-runtime.py` 增加相应渲染支持，原源文件备份为 `.py.pre-nvidia`。
Vault 自动刷新已验证，但未执行整机重启验收。

## 复现脚本

`scripts/homelab-nvidia-stage.py` 从管理终端 Vault 读取 NVIDIA 凭据，在目标 tmpfs 注入，注册或更新指定渠道。
`scripts/homelab-nvidia-persist.py` 补充精确 Vault 权限与主机启动渲染逻辑。
`scripts/homelab-gateway-smoke.py <报告JSON路径>` 验证实际 HTTPS 目录和推理，Key 在主机内读取，不传回控制端。

这些是当前 Home-Lab 的运维脚本，依赖既有 bootstrap、用户、服务和 Vault 身份，不是任意主机的通用安装器。
运行 stage 会重启 LiteLLM；不变更用户钱包、套餐或其他 CPA 渠道配置。

本次报告：`homelab-mixed-gateway-smoke-20261007.json`，位于控制端 `/Users/shenlan/Documents/Codex/`。
本轮非敏感模块清单已同步到 Gateway profile 和 UAT GitOps；生产环境仍需单独写入
Prod Vault、完成 provider smoke test 后再启用。
