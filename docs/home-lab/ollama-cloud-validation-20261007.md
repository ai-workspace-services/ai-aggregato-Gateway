# Ollama Cloud 聚合验证（2026-10-07）

## 已部署链路

`https://ai-internal.onwalk.net/v1 → Caddy → New API → LiteLLM → Ollama Cloud`

CPA 与 NVIDIA 继续由同一个 New API 入口提供服务，客户端仍使用 New API 用户 Key。
Ollama endpoint 为 `https://ollama.com/v1`，endpoint / api_key 来自
`kv/uat/ai-aggregator/litellm/providers/ollama`；密钥不写入 GitOps、README 或客户端配置。

上游目录返回 18 项；逐项发送最小 `Say hello` 请求后，仅注册成功的 5 项。

| 模型 ID | 上游最小聊天 | 统一 HTTPS 最小聊天 | HTTPS 耗时 |
|---|---|---|---|
| `gpt-oss:120b` | 成功 | HTTP 200，非空文本 | 7.18 s |
| `gpt-oss:20b` | 成功 | HTTP 200，非空文本 | 4.59 s |
| `gemma4:31b` | 成功 | HTTP 200，非空文本 | 4.73 s |
| `nemotron-3-super` | 成功 | HTTP 200，非空文本 | 6.64 s |
| `nemotron-3-ultra` | 成功 | HTTP 200，非空文本 | 4.23 s |

这不是长期可用性或性能基准；本轮只验收 OpenAI-compatible 非流式聊天。

| 未启用结果 | 模型 |
|---|---|
| HTTP 402 | `deepseek-v4.1-flash`、`deepseek-v4-pro:0813`、`minimax-m2.7`、`minimax-m3`、`mistral-large-3:675b`、`glm-5.2`、`glm-5.3`、`kimi-k2.6`、`kimi-k2.7-code`、`kimi-k3` |
| 超时 | `glm-5.3-flash`、`nemotron-3-nano:30b`、`mistral-large-4` |

HTTP 402 仅作为观测结果，需向上游核对账号权限/额度，不自动归因于网关。

## 配置与持久化

- LiteLLM 模型映射：`openai/<model-id>`，endpoint/key 使用运行时环境引用。
- New API channel：`litellm-ollama-cloud`，上游 `http://127.0.0.1:4000`。
- 非敏感模型声明保存至 `/etc/ai-aggregator/home-lab.json` 的 `ollama_cloud_models`。
- Vault runtime renderer 按主机声明重新读取凭据，注入 tmpfs；不持久化 Provider Key。
- 已执行 Vault runtime 服务刷新：生成的 10 项 LiteLLM 配置保留全部 5 个 Ollama 模型；节点重启未测试。
- UAT GitOps 同步模型、Provider Vault 引用与 channel；不修改 Prod。

执行过渡脚本需在 Vault 管理终端具备对应权限并能 SSH 到该参考主机：

```bash
python3 scripts/homelab-ollama-stage.py --models \
  gpt-oss:120b gpt-oss:20b gemma4:31b nemotron-3-super nemotron-3-ultra
```

该脚本是 Home-Lab 迁移工具，不是通用一键安装器；会更新最小 Vault 读取 policy、
LiteLLM 配置、New API channel 和主机 renderer，并重启 LiteLLM。执行会有短暂请求窗口。
更新已有 New API channel 时不传 `status`，避免新版本返回 `Invalid parameters`。

## 目录与后续验收

统一入口本轮返回 52 个目录项；累计最小聊天成功记录为 36 个（CPA 26、NVIDIA 5、Ollama 5）。
旧渠道目录尚未全部收敛到已验证清单，因此 52 不代表 52 个都可推理。
后续需完成 SSE、工具调用、客户端接入与重启恢复验证，再扩大能力声明。
