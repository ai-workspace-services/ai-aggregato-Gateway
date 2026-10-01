# LiteLLM 免费/试用 OpenAI-compatible Provider 接入示例

本文只描述接入形态，不承诺平台长期免费、固定限额或生产 SLA。NVIDIA
Build 和 AMD Radeon Cloud 的模型、配额、区域和账号资格以平台当前页面为准。
真实 API key 只能进入 Vault，不能写入本文件、GitOps、systemd unit、Terraform
state 或 CI 日志。

## 1. 统一链路

```text
客户端
  → Caddy TLS
  → APISIX 认证/租户/限流
  → LiteLLM :4000
  → Provider OpenAI-compatible /v1
```

LiteLLM 使用统一的 OpenAI-compatible `model_list`，客户端只看到聚合后的模型名。
NVIDIA 和 AMD 不经过 CPA；CPA 仍只承载个人订阅 OAuth 账号。

## 2. Provider 参数

| LiteLLM logical provider | Base URL | 认证 | 模型名 |
| --- | --- | --- | --- |
| `nvidia-build` | `https://integrate.api.nvidia.com/v1` | `Authorization: Bearer` | 以 NVIDIA Build 当前模型页为准，例如 `nvidia/nemotron-3-super-120b-a12b` |
| `amd-radeon` | `https://developer.amd.com.cn/radeon/api/v1` | `Authorization: Bearer` | 以 Radeon Cloud Token Factory 当前模型页为准，例如 `Qwen3.6-35B-A3B` |

NVIDIA Build 页面提供 OpenAI SDK 兼容的 hosted endpoint；AMD Radeon Cloud
公开文档也提供 OpenAI-compatible shared model endpoint。两者都必须先在网页端
登录并取得当前账号的 API key 和可用模型名，再写入对应 Vault secret。

参考：[NVIDIA Build API 示例](https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b)、
[AMD Radeon Cloud Model APIs](https://amd-aim.github.io/radeon-cloud-docs/guides/model-apis/)。

## 3. Vault 结构

沿用现有按 Provider 分离的结构，新增两个可选路径：

```text
kv/<env>/ai-aggregator/litellm/providers/nvidia
  endpoint = https://integrate.api.nvidia.com/v1
  api_key  = <NVIDIA key，仅通过受控 Vault 写入>

kv/<env>/ai-aggregator/litellm/providers/amd
  endpoint = https://developer.amd.com.cn/radeon/api/v1
  api_key  = <AMD key，仅通过受控 Vault 写入>
```

GitOps 只声明 `enabled`、Vault `secret_ref` 和逻辑模型别名；不保存 endpoint
以外的认证材料。若环境仍要求严格的三 Provider 最小集合，则保持这两个路径
为空且不渲染 `model_list` 条目。

## 4. LiteLLM 配置模板

下面是非敏感模板。部署器应从 Vault 读取 key 后，通过受保护的运行时环境或临时
渲染文件注入；不要把 `<NVIDIA_API_KEY>` 或 `<AMD_API_KEY>` 替换后提交。

```yaml
model_list:
  - model_name: nvidia-free-default
    litellm_params:
      model: openai/nvidia/nemotron-3-super-120b-a12b
      api_base: https://integrate.api.nvidia.com/v1
      api_key: os.environ/NVIDIA_API_KEY

  - model_name: amd-free-default
    litellm_params:
      model: openai/Qwen3.6-35B-A3B
      api_base: https://developer.amd.com.cn/radeon/api/v1
      api_key: os.environ/AMD_API_KEY
```

实际模型名不匹配时，LiteLLM 会返回 provider model-not-found；先用 provider
自己的 `/v1/models` 或平台页面确认，再改逻辑别名。不要因为“免费”而自动加入
CPA fallback，也不要跨 Provider 自动发送含敏感代码或数据的请求。

## 5. Home-Lab 验证顺序

1. 在 NVIDIA Build 或 AMD Radeon Cloud 网页端确认账号、API key 和模型名。
2. 将 key 写入对应环境的 Vault，CI 只验证路径存在，不输出值。
3. 部署器重新生成 LiteLLM 运行时配置并重启 LiteLLM；不手工改 `/etc` 配置。
4. 用 APISIX 客户端 token 请求聚合入口的 `/v1/models`，确认只返回已启用别名。
5. 分别执行一次 Chat、streaming、超时/错误处理测试；记录状态码、延迟和模型别名，
   不记录 prompt、response 或 Authorization。
6. 确认 `direct-ai` 不存在时，仍使用当前单入口 `ai-internal.onwalk.net` 的
   LiteLLM 路由约定；生产域名和路径以 GitOps manifest 为准。

## 6. 失败与回滚

- key 无效、配额耗尽或模型下线：只禁用对应 LiteLLM model alias，不影响 CPA。
- Provider 429/5xx：由 LiteLLM retry/timeout 处理；不要无限重试免费端点。
- 配置校验失败：保留上一份有效运行时配置，禁止 reload。
- 回滚时删除运行时 model entry，不删除 Vault secret；待人工确认后再清理。
