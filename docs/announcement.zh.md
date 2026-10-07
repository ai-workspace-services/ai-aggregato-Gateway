# 少切账号，多用模型：搭建自己的 LLM Hub

GPT、Claude、Gemini，开源 DeepSeek、GLM、GPT-OSS、Nemotron——能不能放到同一个入口，在 OpenCode 里直接切换？

我们把这套配置、脚本和验证记录整理成了 **AI Aggregator Gateway**。

面向个人工作站与团队，Caddy 提供 HTTPS，New API 管理用户、额度和模型权限，CPA 隔离订阅账号，LiteLLM 接入官方 API、NVIDIA NIM 与 Ollama Cloud。需要入口 ACL、限流与审计时，还可以选择 APISIX 或 Kong。

参考环境已有 **36 个模型的最小聊天成功记录**。商业订阅与开源模型在同一个 Provider 下使用，OpenCode App、CLI 和其他支持兼容接口的客户端可按端点接入。模型目录、账号权限和真实推理结果都有对应记录。

少花钱，先把已有订阅、开发者额度与开源能力用起来。目录可见不代表可推理；开发者额度和模型可用性以平台及账号实际状态为准。

仓库包含架构、模型表、OAuth 操作、Vault 凭据管理、部署引导与请求验证说明。Home-Lab 是参考环境，部署其他主机时需设置目标并准备服务、数据库与凭据。

欢迎试用、提 Issue，也欢迎补充你实际验证过的模型与部署经验。

https://github.com/ai-workspace-services/ai-aggregato-Gateway
