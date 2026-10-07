# Home-Lab Personal LLM Modules Hub

Home-Lab 的 `ai-aggregato-Gateway` 不把模型目录当成静态“万能列表”，而是把每个
模型当成一个可验证、可启停、可回滚的模块。统一入口仍由 New API 维护用户、套餐、
额度、模型权限和消费记录；LiteLLM 只负责官方/OpenAI-compatible provider 适配、
重试、超时和上游成本统计；CPA 只负责本地订阅账号 OAuth。

## 模块分层

```text
客户端
  → Caddy TLS
  → New API（唯一用户账本）
      ├─ CPA：Codex / Claude / Google 等订阅 OAuth
      └─ LiteLLM：官方 API / NVIDIA / AMD / Ollama
```

模块目录只保存 `id`、provider、上游模型名、协议和状态。API key 只在
`kv/<env>/ai-aggregator/litellm/providers/<provider>`，CPA OAuth 只在实例本地加密
目录，健康与消费数据在数据库。一个模块只有完成 `catalog → stage → minimal hello
→ streaming/tool test → activate` 才能进入公开模型权限。

## Home-Lab 已验证模块

2026-10-07 从 Home-Lab Vault 注入 NVIDIA 凭据后，上游 NVIDIA `/v1/models` 返回
80 个目录项；本轮真实最小聊天请求通过的 5 个是：

```text
openai/gpt-oss-20b
nvidia/nemotron-3.5-lightning-30b-a3b
deepseek-ai/deepseek-v4.1-flash
z-ai/glm-5.3
z-ai/glm-5.3-flash
```

这 5 个已作为非敏感模块声明写入 `profiles/ai-gateway-v1/llm-modules.yaml`。
`moonshotai/kimi-k3` 虽出现在上游目录，但本次请求超时，不能标记为已验证；
DeepSeek V4-Pro、MiniMax M3、Qwen3.8 不在本次 80 项目录中。AMD 当前不启用。

## 80 项上游目录的含义

80 项只是 NVIDIA 账号可发现的上游模型目录，包含文本、代码、视觉、嵌入、翻译、
安全和视频等不同能力，并不表示：

- 已写入 LiteLLM 的 `model_list`；
- 已通过 New API 用户模型权限；
- 适合 `/v1/chat/completions`；
- 在当前额度、区域和账号下可推理；
- 已完成 streaming、工具调用或图像协议验收。

完整快照保存在 `docs/home-lab/nvidia-model-catalog-20261007.txt`，仅供发现和
后续筛选，不作为自动启用清单。
