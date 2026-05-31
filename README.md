# autodl-cli

一个给 AutoDL Pro 用户用的命令行工具。目标是把网页上常见的 Pro 实例操作搬到终端里：查余额、看实例、开机、关机、释放、保存镜像。

这个项目目前专注 **AutoDL Pro 实例**，不做企业弹性部署 API，也不抓网页、不模拟网页登录。

## 它能做什么

- 查看 AutoDL 账户余额。
- 查看当前账号下的 Pro 实例列表。
- 查看实例状态和实例详情。
- 有卡开机、关机、释放实例。
- 一键 `destroy`：先关机，再释放。
- 保存实例为私有镜像。
- 查看私有镜像列表。
- 支持 `--json`，方便脚本集成。
- 默认隐藏敏感信息，例如 root 密码、Jupyter token、Authorization token。

后续计划：

- 创建 Pro 实例。
- 飞书 Webhook 通知。
- 实例状态监控。
- 稀缺算力等待/重试。
- 定时开关机。

## 适合谁

适合经常使用 AutoDL Pro 跑训练、推理、实验的人，尤其是：

- 不想每次打开网页点开机/关机。
- 想用脚本管理实例。
- 想在服务器、笔记本或 CI 里查询 AutoDL 状态。
- 想更谨慎地管理计费实例，减少忘关机器的风险。

如果你只偶尔用一次 AutoDL，网页控制台可能已经够用。

## 安装

这个项目使用 `uv` 管理 Python 环境。

先安装依赖：

```bash
uv sync
```

检查命令是否可用：

```bash
uv run autodl --help
```

你应该能看到类似这些命令：

```text
auth
account
config
instance
image
```

## 获取 AutoDL Token

这个工具不支持用户名密码登录。AutoDL 官方 API 使用开发者 Token。

你需要到 AutoDL 控制台里找到开发者 Token。一般路径是：

```text
AutoDL 控制台 -> 账号/设置 -> 开发者 Token
```

拿到 token 后再初始化配置。

## 5 分钟上手

### 1. 初始化

推荐优先把 token 存进系统密钥链：

```bash
uv run autodl init --token-store keyring
```

命令会提示你输入 token。输入时不会明文显示。

如果你的机器没有可用的系统密钥链，可以改用本地文件保存：

```bash
uv run autodl init --token-store file
```

本地 token 文件会放在用户数据目录下，并尽量设置为只有当前用户可读写。

### 2. 检查 token 是否可用

```bash
uv run autodl auth check
```

### 3. 查看余额

```bash
uv run autodl account balance
```

如果你想把结果给脚本处理，加 `--json`：

```bash
uv run autodl --json account balance
```

### 4. 查看实例列表

```bash
uv run autodl instance list
```

### 5. 查看某个实例状态

```bash
uv run autodl instance status <instance_uuid>
```

### 6. 查看某个实例详情

```bash
uv run autodl instance inspect <instance_uuid>
```

输出会自动隐藏敏感字段。

## 常用命令

### 账户

```bash
uv run autodl auth check
uv run autodl account balance
```

### 实例

查看实例：

```bash
uv run autodl instance list
uv run autodl instance status <instance_uuid>
uv run autodl instance inspect <instance_uuid>
```

创建实例功能暂时下线，待重新核对 Pro API 参数后再开放。当前建议先在 AutoDL 网页控制台创建实例，再用本工具查询、开机、关机、释放和保存镜像。

开机：

```bash
uv run autodl instance start <instance_uuid>
```

带启动命令开机：

```bash
uv run autodl instance start <instance_uuid> \
  --start-command "bash /root/start.sh"
```

关机：

```bash
uv run autodl instance stop <instance_uuid>
```

释放实例：

```bash
uv run autodl instance release <instance_uuid>
```

这是高危操作，会释放实例资源。请先确认实例内重要数据、镜像和任务状态已经处理完毕。

跳过确认直接释放：

```bash
uv run autodl instance release <instance_uuid> --yes
```

`--yes` 只会跳过交互确认，不代表操作更安全。CLI 仍会在 stderr 打印高危警告。

先关机再释放：

```bash
uv run autodl instance destroy <instance_uuid>
```

这是高危操作，会先关机再释放实例资源。请先确认实例内重要数据、镜像和任务状态已经处理完毕。

跳过确认直接关机并释放：

```bash
uv run autodl instance destroy <instance_uuid> --yes
```

### 镜像

查看私有镜像：

```bash
uv run autodl image list
```

保存实例为私有镜像：

```bash
uv run autodl image save <instance_uuid> --name <image_name>
```

## 全局参数

这些参数可以放在 `autodl` 后面、子命令前面。

指定配置 profile：

```bash
uv run autodl --profile default account balance
```

临时传入 token，不写入配置：

```bash
uv run autodl --token "$AUTODL_TOKEN" account balance
```

输出 JSON：

```bash
uv run autodl --json instance list
uv run autodl instance list --json
```

面向脚本或 AI agent 时，请优先使用 `--json`。默认表格输出是给人看的，不保证适合机器解析。

`instance list --json` 会返回稳定的 key-value 结构，列表项会包含规范化字段：

```json
{
  "list": [
    {
      "uuid": "pro-xxx",
      "name": "train-job",
      "status": "running",
      "gpu_spec_uuid": "4090",
      "gpu_amount": 1
    }
  ],
  "page_index": 1,
  "page_size": 20,
  "total_count": 1,
  "total_page": 1
}
```

指定配置文件：

```bash
uv run autodl --config ./config.toml account balance
```

查看版本：

```bash
uv run autodl --version
```

## 关于开机、释放和计费

请特别注意：

- `instance start` 会有卡开机，也是可能产生费用的操作。
- `instance release` 是高危操作，会释放实例资源。
- `instance destroy` 是高危操作，会先关机再释放实例资源。
- 使用 `--yes` 会跳过交互确认，适合脚本，但请只在你非常确定目标实例时使用。

建议新用户先只运行这些只读命令：

```bash
uv run autodl auth check
uv run autodl account balance
uv run autodl instance list
uv run autodl image list
```

确认 token 和输出都正常后，再使用开机、释放命令。

## Pro API 能不能获取机器列表？

当前实现使用的是 AutoDL Pro 官方公开 API。

Pro API 支持获取“当前账号下的 Pro 实例列表”：

```text
POST /api/v1/dev/instance/pro/list
```

这不是平台物理机器列表，也不是全站 GPU 库存列表。

也就是说：

- 可以列出你自己账号下已有的 Pro 实例。
- 不会去抓取 AutoDL 的网页。
- 不会获取其他用户或平台机器池。
- 不会绕过 AutoDL 的调度逻辑。

因为 AutoDL Pro 是算力和数据分离，通常不需要“抢某一台机器”。后续如果做等待/重试，也只会基于官方 Pro API 做温和重试，不会模拟网页登录或高频刷接口。

## 常见问题

### 没有 token 怎么办？

去 AutoDL 控制台获取开发者 Token，然后运行：

```bash
uv run autodl init
```

### 不想保存 token 怎么办？

可以每次临时传入：

```bash
uv run autodl --token "$AUTODL_TOKEN" account balance
```

### 输出里为什么看不到 root 密码和 Jupyter token？

为了避免误泄漏，CLI 默认会隐藏敏感字段。

### 为什么没有 Webhook？

Webhook 会做，但不是第一批核心功能。当前先完成账户、实例、镜像这些基础能力。

### 为什么没有创建实例命令？

创建实例接口参数和实际 Pro 行为还需要继续核对。为了避免命令直接报错，或者误触发计费操作，`instance create` 暂时下线，标记为待实现。

### 为什么没有企业弹性部署 API？

这个项目第一阶段只做 AutoDL Pro 实例。企业弹性部署 API 权限和使用场景不同，暂时不混在一起。

## 开发

运行测试：

```bash
uv run pytest
```

运行 lint：

```bash
uv run ruff check .
```

查看 CLI 帮助：

```bash
uv run autodl --help
```

设计文档在：

```text
docs/autodl-pro-cli-design.md
```
