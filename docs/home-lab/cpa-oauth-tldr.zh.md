# CPA 人工 OAuth TLDR：OpenAI / Anthropic / xAI / Google

核对日期：2026-10-01。以下参数已通过 Home-Lab `/opt/ai-aggregator/cliproxyapi --help` 实际核对；本文不执行登录或启用渠道。

本文为 [AI Aggregator Gateway：选型、架构与 Home-Lab 实施](./ai-aggregator-gateway-architecture.zh.md) 的操作附录；架构、选型、凭据归属和验收范围以主文档为入口。

## 先确认实例映射

| 平台 | 实例 | 参数 | 当前状态 |
| --- | --- | --- | --- |
| OpenAI / Codex | `cpa-codex-01`、`cpa-codex-02` | `--codex-device-login` | 已部署两个独立账号实例 |
| Anthropic / Claude | `cpa-claude-01` | `--claude-login` | 已部署 |
| xAI / Grok | `cpa-grok-01` | `--xai-login` | 未部署，命令仅作部署后参考 |
| Google：Antigravity / Gemini CLI | `cpa-antigravity-01` | CPA `--antigravity-login` | Antigravity adapter 已部署；Gemini CLI 自身登录另行完成 |

当前四个运行实例是两个 Codex、一个 Claude、一个 Antigravity，并非四个平台各一个。增加 Grok 需先声明并部署独立实例，不替换或复用现有认证目录。Gemini 模型具体可用性以登录后的模型目录与真实调用为准。

## 共用前置检查

从 Mac 打开交互终端：

```bash
ssh -t root@10.79.0.7
/opt/ai-aggregator/cliproxyapi --help
```

按目标实例检查 Unix 用户、配置、服务、认证挂载：

```bash
cpa_id=cpa-codex-01
id "$cpa_id"
test -r "/run/ai-aggregator/$cpa_id.yaml"
```

服务名为 `ai-aggregator-<instance-id>.service`，例如 `ai-aggregator-cpa-codex-01.service`：

```bash
systemctl is-active "ai-aggregator-$cpa_id.service"
findmnt -T "/var/lib/ai-aggregator/cpa/$cpa_id/auth"
stat -c '%U %G %a' "/var/lib/ai-aggregator/cpa/$cpa_id/auth"
```

确认认证目录属于实例用户、权限 `0700`，底层加密卷/认证挂载已就绪；`findmnt` 本身不能证明加密。命令保留终端交互，不使用 `tee`、录屏或 CI 收集授权链接、设备码和回调内容。

## OpenAI：Codex 设备登录

当前 Home-Lab 的 Codex device flow 需要在 AI Desktop 远程桌面中打开设备登录页面。SSH 终端只负责启动 CPA 和显示设备码，远程桌面浏览器负责完成 Google/ChatGPT 登录。

### Codex-01 完整步骤

在本地终端窗口 1 连接 Home-Lab：

```bash
ssh -t root@10.79.0.7
```

在 Home-Lab root shell 中逐行执行：

```bash
cpa_id=cpa-codex-01
cd "/var/lib/ai-aggregator/$cpa_id" || exit 1
systemctl stop "ai-aggregator-$cpa_id.service"
runuser -u "$cpa_id" -- /opt/ai-aggregator/cliproxyapi \
  --config "/run/ai-aggregator/$cpa_id.yaml" \
  --codex-device-login --no-browser
```

终端会显示类似下面的信息：

```text
Starting Codex device authentication...
Codex device URL: https://auth.openai.com/codex/device
Codex device code: <DEVICE_CODE>
```

设备码只用于本次登录，不要复制到聊天、工单、日志或截图。保持 SSH 窗口运行，不要按 Ctrl-C。

在 Home-Lab 的 `ai_desktop` 远程桌面中：

1. 打开浏览器。
2. 访问终端显示的 `Codex device URL`，不要手工改写域名。
3. 输入终端显示的 `<DEVICE_CODE>`。
4. 登录矩阵指定的账号 `manbuzhe2009@qq.com`。
5. 完成授权后回到 SSH 窗口，等待出现登录成功或认证完成提示。

成功后，在 SSH 窗口按 `Ctrl-C` 结束登录进程，再启动服务：

```bash
systemctl start ai-aggregator-cpa-codex-01.service
systemctl is-active ai-aggregator-cpa-codex-01.service
```

检查本地认证结果，只输出文件名：

```bash
find /var/lib/ai-aggregator/cpa/cpa-codex-01/auth \
  -maxdepth 2 -type f -printf '%P\n'
```

如果浏览器提示设备码过期、无效或账号错误，关闭当前登录进程，重新执行完整步骤生成新设备码；不要重复使用旧 code。

```bash
cd /var/lib/ai-aggregator/cpa-codex-01
runuser -u cpa-codex-01 -- /opt/ai-aggregator/cliproxyapi \
  --config /run/ai-aggregator/cpa-codex-01.yaml \
  --codex-device-login --no-browser
```

第二个账号使用完全独立的实例和登录流程。确认账号为 `manbuzhe2008@gmail.com`：

```bash
cd /var/lib/ai-aggregator/cpa-codex-02
runuser -u cpa-codex-02 -- /opt/ai-aggregator/cliproxyapi \
  --config /run/ai-aggregator/cpa-codex-02.yaml \
  --codex-device-login --no-browser
```

这里也要在 AI Desktop 远程桌面打开终端显示的设备 URL，输入新生成的设备码；不能复用 Codex-01 的 code 或浏览器账号状态。

## Anthropic：Claude OAuth

### Claude 完整步骤

```bash
cpa_id=cpa-claude-01
cd "/var/lib/ai-aggregator/$cpa_id" || exit 1
systemctl stop "ai-aggregator-$cpa_id.service"
runuser -u cpa-claude-01 -- /opt/ai-aggregator/cliproxyapi \
  --config /run/ai-aggregator/cpa-claude-01.yaml \
  --claude-login --no-browser
```

在 AI Desktop 远程桌面浏览器中打开终端显示的授权 URL，确认账号为
`haitaopanhq@gmail.com`，完成授权后回到 SSH 窗口等待成功提示。若 CPA 明确提示 localhost 回调，按本文后面的 SSH 隧道步骤处理。

完成后按 `Ctrl-C`，恢复服务并检查：

```bash
systemctl start ai-aggregator-cpa-claude-01.service
systemctl is-active ai-aggregator-cpa-claude-01.service
find /var/lib/ai-aggregator/cpa/cpa-claude-01/auth \
  -maxdepth 2 -type f -printf '%P\n'
```

失败或账号错误时结束当前进程，从停服务步骤重新开始；每次使用新的授权流程。

## xAI：Grok OAuth（实例部署后）

前置条件：GitOps 已声明 `cpa-grok-01`，Unix 用户、配置文件、加密 auth 目录及 systemd 服务均已部署。当前 Home-Lab 尚不满足该条件。

```bash
cpa_id=cpa-grok-01
cd "/var/lib/ai-aggregator/$cpa_id" || exit 1
systemctl stop "ai-aggregator-$cpa_id.service"
runuser -u cpa-grok-01 -- /opt/ai-aggregator/cliproxyapi \
  --config /run/ai-aggregator/cpa-grok-01.yaml \
  --xai-login --no-browser
```

按终端实际提示，在 AI Desktop 远程桌面浏览器中打开授权页面（如果输出 URL），使用部署时批准的 xAI 账号完成授权。不要将官方 xAI API Key 当作 OAuth bundle。

授权成功后按 `Ctrl-C`，再执行：

```bash
systemctl start ai-aggregator-cpa-grok-01.service
systemctl is-active ai-aggregator-cpa-grok-01.service
find /var/lib/ai-aggregator/cpa/cpa-grok-01/auth \
  -maxdepth 2 -type f -printf '%P\n'
```

当前 Home-Lab 尚未部署此实例；GitOps、Unix 用户、配置文件、auth 目录和 systemd 服务就绪前不要执行。

## Google：Antigravity OAuth 与 Gemini CLI

当前 CPA Google 入口使用 Antigravity：

```bash
cpa_id=cpa-antigravity-01
cd "/var/lib/ai-aggregator/$cpa_id" || exit 1
systemctl stop "ai-aggregator-$cpa_id.service"
runuser -u cpa-antigravity-01 -- /opt/ai-aggregator/cliproxyapi \
  --config /run/ai-aggregator/cpa-antigravity-01.yaml \
  --antigravity-login --no-browser
```

在 AI Desktop 远程桌面浏览器中打开终端显示的授权 URL，确认 `haitaopanhq@gmail.com`，等待终端完成。随后按 `Ctrl-C`，恢复并检查：

```bash
systemctl start ai-aggregator-cpa-antigravity-01.service
systemctl is-active ai-aggregator-cpa-antigravity-01.service
find /var/lib/ai-aggregator/cpa/cpa-antigravity-01/auth \
  -maxdepth 2 -type f -printf '%P\n'
```

这仅登录 CPA Antigravity adapter；不代表独立 Gemini CLI 已登录，也不保证所有 Gemini 模型可调用。

当前 CPA `--help` 没有独立 Gemini 登录参数。若目标是 Gemini CLI：

1. 进入 AI Desktop 远程桌面，打开该 CodeAgent 用户的终端。
2. 启动已安装的 `gemini` CLI，按当前版本交互提示选择 Google 登录。
3. 在远程桌面浏览器中完成 Google 登录，确认 `haitaopanhq@gmail.com`。
4. 回到 Gemini CLI，等待登录完成后再做最小模型列表或请求检查。

不要凭空使用未在当前版本帮助中确认的 `gemini login` 参数，也不要将 `.gemini/config/config.json` 或整个 `.gemini/` 复制到 CPA、Vault、Git 或聊天。

## localhost 回调：Mac SSH 隧道

仅当 CPA 提示 localhost 回调时，在 Mac 的另一个终端转发它实际显示的端口。下例的 `<port>` 必须替换为数字：

```bash
ssh -N -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:<port>:127.0.0.1:<port> root@10.79.0.7
```

隧道保持运行至登录完成，再 Ctrl-C 关闭。回调端口不经过 Caddy/APISIX，不公开到网络；在服务器确认实际监听范围。若端口冲突，可先通过 `--oauth-callback-port` 指定端口，并同步调整隧道，以实际 CLI 提示为准。

## 登录完成：恢复服务 → 验证 → 启用

登录进程必须从实例用户可访问的工作目录启动。否则从 root 的 `/root` 目录直接 `runuser` 时，Go 程序执行 `stat .` 会得到 `permission denied`。若 CLI 报端口或文件冲突，可只停该实例并在退出后恢复。可使用下面的 shell 包装，确保普通失败或中断后重新启动该实例：

```bash
(
  cpa_id=cpa-claude-01
  login_flag=--claude-login
  trap 'systemctl start "ai-aggregator-$cpa_id.service"' EXIT
  systemctl stop "ai-aggregator-$cpa_id.service" || exit 1
  cd "/var/lib/ai-aggregator/$cpa_id" || exit 1
  runuser -u "$cpa_id" -- /opt/ai-aggregator/cliproxyapi \
    --config "/run/ai-aggregator/$cpa_id.yaml" "$login_flag" --no-browser
)
```

检查状态、权限和认证文件数量，不打印文件内容：

```bash
cpa_id=cpa-claude-01
systemctl is-active "ai-aggregator-$cpa_id.service"
stat -c '%U %G %a' "/var/lib/ai-aggregator/cpa/$cpa_id/auth"
find "/var/lib/ai-aggregator/cpa/$cpa_id/auth" -maxdepth 2 -type f -name '*.json' -printf '.\n' | wc -l
```

OAuth bundle 仅保存在本实例本地加密 auth 目录，不上传 Vault、数据库、Git 或聊天。CLI 登录成功后，继续使用受控验证程序读取凭据，依次验证模型目录、一次真实推理、streaming、工具调用和相应协议；不要把 key 写入命令行或 shell 历史。

现有节点提供以下单渠道激活脚本，执行前核对其 `--help`、账号和模型；此操作会产生真实推理请求并修改 Channel 状态：

```bash
python3 /opt/ai-aggregator/bootstrap/activate-cpa.py --help
python3 /opt/ai-aggregator/bootstrap/activate-cpa.py cpa-codex-01 \
  --model '<实际模型 ID>' \
  --confirm-account-email 'manbuzhe2009@qq.com' --approve-inference
```

完整验收路径为 `stage → 人工 OAuth → validate / smoke test → activate`。OAuth 登录使用 CPA，客户端随后使用 APISIX 网关凭据和约定的上游授权，不把 OAuth token 发给客户端。

参考：[架构与选型](./ai-aggregator-gateway-architecture.zh.md)、[CPA 项目](https://github.com/ai-workspace-lab/CLIProxyAPI)。登录参数以已部署二进制为准。
