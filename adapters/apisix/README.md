# APISIX adapter

默认选用 APISIX Standalone file-driven，以 GitOps 完整文件作为配置事实源，免 etcd。
`ai_proxy_multi` 路由会生成 `ai-proxy-multi` 插件；凭据仅生成运行时环境变量引用。
部署说明见 [Standalone GitOps 选型](../../docs/apisix-standalone-gitops.zh.md)。

生成完整 `apisix.yaml` 配置，不把 APISIX Standalone 描述为 Kong PostgreSQL 动态配置的等价实现。租户变更、全量发布和回滚由部署流水线负责。

APISIX adapter 负责 Host/URI 路由、Key Auth、Consumer 限制、按租户限流、审计请求头和 upstream 节点调度。它通过 Standalone 全量配置发布实现这些能力，不提供 Kong PostgreSQL 的动态控制面语义。
