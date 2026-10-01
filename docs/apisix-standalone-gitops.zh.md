# APISIX Standalone GitOps 选型

默认网关选择 APISIX Standalone file-driven，关闭 etcd、Admin API 和 Control API。
Caddy 自动 TLS → APISIX（认证、租户、限流、路由）→ New API → CPA。
官方 API 使用 APISIX `ai-proxy-multi` 直接聚合，LiteLLM 保留为迁移回滚上游。

## 配置交付

GitOps 是配置事实源，不是 APISIX 原生数据库插件。公共 CLI 将经过校验的 YAML
渲染为 `config.yaml` 和以 `#END` 结尾的完整 `apisix.yaml`。
APISIX 监听 `127.0.0.1:9080`；Caddy 只转发 HTTPS。

```bash
python -m gatewayctl validate contracts/ai-internal-apisix.yaml
python -m gatewayctl render contracts/ai-internal-apisix.yaml --adapter apisix --output-dir build/apisix
python -m gatewayctl render contracts/ai-internal-apisix.yaml --adapter caddy --output-dir build/caddy
```

单入口 `ai-internal.onwalk.net`：`/v1/*` 交给 New API，
`/official/v1/chat/completions` 由 AI 插件处理。官方 API 客户端 base URL 为
`https://ai-internal.onwalk.net/official/v1`。插件实例的 `override.endpoint`
必须是完整上游接口 URL，不能直接使用只有主机的 Provider base URL。
该示例只实现官方 Chat 接口；Responses、Messages、streaming、tool calling
仍需逐协议验证后扩展。

## 凭据与激活

Git 中只保存环境变量名称。Vault 的
`kv/<env>/ai-aggregator/litellm/providers/{openai,anthropic,xai}`
继续提供 endpoint/API key；部署控制器转换为对应 `*_CHAT_ENDPOINT` 和 `*_API_KEY`。
运行时环境文件放在 `/run/ai-aggregator/apisix/`，root-only，禁止日志或 artifact 输出。
租户默认禁用，渲染 route `status: 0`；激活前必须由部署控制器注入 consumer
认证配置，校验无凭据、错误凭据、跨租户请求都被拒绝，然后打开租户。
CPA OAuth 继续留在各实例本地加密目录。

## 部署交接与验证

Playbooks 当前 `apisix_service` role 使用 Docker，不能直接当作 systemd 实现。
后续 systemd 部署需固定 APISIX/OpenResty 版本，验证插件 schema，再 stage 完整配置；
保留上一次非敏感配置，采用同文件系统临时文件校验与原子 rename 发布。
路由文件会热加载；进程环境变量改变需重启 APISIX，单纯路由热加载不足以轮换环境凭据。
先验证本地 APISIX，再验证 Caddy TLS 和入口；验证成功后切流。
回滚恢复上一版完整文件及对应运行时环境。跨 OpenAI/Anthropic/xAI fallback
必须由租户显式接受数据发送目的地和模型差异。

本轮公共 renderer 测试不能代替 APISIX schema 加载、systemd、节点及端到端验证。

官方参考：
- https://apisix.apache.org/docs/apisix/plugins/ai-proxy-multi/
- https://apisix.apache.org/docs/apisix/deployment-modes/
