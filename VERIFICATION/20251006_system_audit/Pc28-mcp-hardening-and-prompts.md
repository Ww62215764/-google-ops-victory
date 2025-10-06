# PC28 MCP: 生产级加固与标准化作业指令库 (V1)

> **方案提出**: 项目总指挥 (15年BigQuery/生产级工程专家)  
> **方案整理**: 707 (AI)  
> **日期**: 2025-10-06
> **状态**: **提案通过，待执行**

---

## 1. 核心理念：从“手工作坊”到“现代工厂”

本方案旨在将我们当前的云端运维模式，从依赖个人经验和手动操作的“手工作坊”，全面升级为基于代码化、自动化和持续验证的“现代工厂”。我们的核心原则是：

-   **一切皆代码 (Everything as Code)**: 所有云资源 (IaC)、所有运维操作 (OaC)、所有监控告警规则 (MaC)，都必须以代码的形式进行版本化管理。
-   **不可变基础设施 (Immutable Infrastructure)**: 我们不“修复”服务器或服务，我们只“替换”它们。任何变更都通过部署一个全新的、经过验证的版本来实现。
-   **持续验证与主动防御 (Continuous Verification & Proactive Defense)**: 在问题演变成故障之前，通过自动化的测试和监控，主动地发现并拦截它们。

---

## 2. “磐石”加固计划 (Project "Bedrock" - Hardening Plan)

**目标**: 根除“组件静默失踪”问题，确保所有云端基础设施的健壮性与可追溯性。

### 2.1 [P0] 基础设施全面代码化 (IaC with Terraform)

-   **行动**: 引入`Terraform`作为我们唯一的云资源管理工具。
-   **范围**:
    -   `Cloud Run`服务: `drawsguard-api-collector`, `betting-recorder`
    -   `Cloud Scheduler`任务: `trigger-draws-collector`, `trigger-betting-recorder-predict`
    -   `BigQuery`数据集与核心表结构: `pc28`, `pc28_lab`
    -   `IAM`服务账户与权限绑定
-   **交付产物**:
    -   一个全新的`terraform/`目录。
    -   所有现有云资源的`.tf`定义文件。
-   **预期效果**: 彻底禁止任何通过GCP控制台进行的、手动的资源变更。所有变更必须通过代码提交、审查和`terraform apply`来完成。

### 2.2 [P1] 基础设施级监控

-   **行动**: 扩充我们的“哨兵协议V2”，增加对基础设施组件本身状态的监控。
-   **监控项**:
    -   **调度器状态监控**: 创建一个新的监控视图 `monitor_v4_scheduler_health`，该视图应每10分钟执行一次 `gcloud scheduler jobs describe <job_name>` 命令，并检查返回结果中的`state`字段。如果`state`不为`ENABLED`，则立刻生成**P1级告警**。
-   **预期效果**: 在我们现有的“数据质量”监控之上，增加一层“系统组件”监控，形成双重保险。

---

## 3. “法典”标准化指令库 (Project "Codex" - Prompts Library)

**目标**: 根除“命令随手敲”的问题，将所有运维操作标准化、脚本化。

### 3.1 [P1] 建立`scripts/`目录

-   **行动**: 在项目根目录下，创建一个全新的`scripts/`目录，用于存放所有标准化的运维脚本。
-   **结构**:
    ```
    scripts/
    ├── deploy/
    │   ├── deploy_collector.sh
    │   └── deploy_predictor.sh
    ├── data/
    │   ├── backfill.sh
    │   └── reprocess_features.sh
    └── system/
        └── check_status.sh
    ```

### 3.2 [P2] 编写核心运维脚本

-   **行动**: 将我们最高频、最核心的操作，优先封装成脚本。
-   **首批脚本清单**:
    -   `scripts/system/check_status.sh`: 一键执行，调用所有`monitor_v*`视图和`alerts_v2`表，生成一份浓缩版的实时战情报告。
    -   `scripts/deploy/deploy_collector.sh`: 封装了`gcloud builds submit`和`gcloud run deploy`等一系列命令，实现数据采集服务的一键安全部署。
-   **预期效果**: 将复杂的、多步骤的云端操作，简化为单一、可靠的本地命令，极大降低人为失误的概率。

---

## 4. “金丝雀”部署验证脚本 (Project "Canary" - Test Scripts)

**目标**: 根除“部署即祈祷”的问题，为我们的核心服务建立一套自动化的、部署后的快速健康检查机制。

### 4.1 [P1] 为`drawsguard-api-collector`开发金丝雀脚本

-   **行动**: 创建`scripts/deploy/canary_test_collector.sh`。
-   **执行时机**: 在`deploy_collector.sh`脚本成功执行`gcloud run deploy`之后，自动调用。
-   **核心流程**:
    1.  **记录当前**: 获取BigQuery中最新的`issue`号，记为`last_issue_before_test`。
    2.  **强制触发**: 手动调用一次刚刚部署的新版`drawsguard-api-collector`服务。
    3.  **轮询验证**: 在接下来的90秒内，每10秒查询一次BigQuery，检查是否存在一个`issue`号大于`last_issue_before_test`的新记录。
    4.  **裁决**:
        -   **如果成功**: 打印“✅ Canary test passed!”并正常退出。
        -   **如果失败**: 打印“🔴 Canary test FAILED!”，立刻自动触发回滚到上一个稳定版本，并向`alerts_v2`表中插入一条**P1级部署失败告警**。
-   **预期效果**: 确保任何有问题的代码版本，在被部署到生产环境的90秒内，就会被自动发现、自动隔离，从而将故障对系统的影响降至最低。
