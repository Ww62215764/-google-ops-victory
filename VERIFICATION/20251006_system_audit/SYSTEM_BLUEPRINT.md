#  PC28 “天网”自动化作战系统 - 系统蓝图 V1
> **文件状态**: 动态更新中  
> **最后更新**: 2025-10-06  
> **审计负责人**: 707 (AI)
---

## 第一部分：系统概述与核心数据流

本系统是一个全自动化的云原生应用，旨在实时采集PC28开奖数据，通过一系列结构化的数据视图进行特征提取与信号生成，最终产出对未来奖期的预测。整个过程无需人工干预，7x24小时在Google Cloud上自动运行。

**核心数据流**可以概括为以下五个步骤：

1.  **数据采集 (Data Ingestion)**: 云服务 `drawsguard-api-collector` 定时从上游API获取最新的开奖结果。
2.  **原始数据层 (Raw Data Layer)**: 采集到的数据被整理、去重后，在视图 `draws_14w_dedup_v` 中形成统一、干净的数据源。
3.  **特征工程层 (Feature Engineering Layer)**: 视图 `features_v1` 基于原始数据，计算出如“大小连胜”、“单双连胜”等基础战术特征。
4.  **信号生成层 (Signal Generation Layer)**: 
    *   视图 `advanced_signals_v1` (战术中枢) 根据特征层的输出，应用核心预测逻辑（如长龙反转、趋势跟随），生成对**下一期**的预测信号。
    *   视图 `candidates_v1` (弹药工厂) 将这些信号“范式化”，转换成统一格式的“候选弹药”。
5.  **预测执行层 (Prediction & Execution Layer)**:
    *   云调度器 `trigger-betting-recorder-predict` 每3分钟触发一次预测流程。
    *   该流程读取“弹药工厂”中的最新弹药，将其加工成最终预测结果，并存入 `score_ledger` (战功记录簿) 以供下游系统使用和未来审计。


## 第二部分：云基础设施组件

### 2.1 数据采集服务: `drawsguard-api-collector` (Cloud Run)

这是我们系统的数据入口，一个无服务器化的云服务，负责系统的“侦察”任务。

-   **服务类型**: Google Cloud Run
-   **触发方式**: 由外部的Cloud Scheduler（或等效的定时任务服务）通过HTTP请求触发，以固定的频率（例如每5分钟）运行。
-   **核心职能**: 调用 `rijb.api.storeapi.net` 接口，获取最新的PC28开奖数据，并将其写入BigQuery的原始数据表中。
-   **镜像地址**: `gcr.io/wprojectl/api-collector-service:latest`
-   **服务账户**: `644485179199-compute@developer.gserviceaccount.com` (拥有访问BigQuery和Secret Manager的权限)
-   **关键配置**:
    -   CPU: 1000m
    -   内存: 512Mi
    -   超时: 300秒

### 2.2 预测触发器: `trigger-betting-recorder-predict` (Cloud Scheduler)

这是我们系统预测流程的“发令枪”，确保我们的预测引擎能被周期性、可靠地唤醒。

-   **服务类型**: Google Cloud Scheduler
-   **核心职能**: 定时向 `betting-recorder` 服务的 `/predict` 端点发送一个HTTP POST请求，从而触发一次完整的预测与下单流程。
-   **执行频率**: `*/3 * * * *` (每3分钟执行一次)，确保了预测的准实时性。
-   **目标服务**: `https://betting-recorder-644485179199.us-central1.run.app/predict`
-   **时区**: `Asia/Shanghai`

## 第三部分：BigQuery数据仓库 - “信号工厂”

这是我们系统的“大脑”，所有的数据处理、特征计算和信号生成都在这里通过一系列级联的SQL视图完成。这种设计的最大好处是：**逻辑即代码、高度透明、自动更新**。当新的原始数据进来时，所有后续的视图都会自动计算出最新结果。

### 3.1 原始数据: `pc28.draws_14w_dedup_v` (视图)

-   **定位**: 万物之源 (The Single Source of Truth)
-   **描述**: 这是整个系统所有分析和计算的唯一、可信的数据源。它整合了从API采集到的原始数据，并进行了必要的清洗和去重。
-   **表结构**:
    ```json
    [
      {"name": "issue", "type": "INTEGER"},
      {"name": "timestamp", "type": "TIMESTAMP"},
      {"name": "sum28", "type": "INTEGER"},
      {"name": "result_digits", "type": "STRING"}
    ]
    ```

### 3.2 特征工程: `pc28.features_v1` (视图)

-   **定位**: 战场情报分析室
-   **描述**: 该视图在原始数据的基础上，进行第一层加工。它通过窗口函数（`LAG`, `ROW_NUMBER`）计算出截至每一期的“大小”和“单双”的连续出现次数（即“长龙”长度）。
-   **表结构**:
    ```json
    [
      {"name": "period", "type": "INTEGER"},
      {"name": "timestamp", "type": "TIMESTAMP"},
      {"name": "sum_value", "type": "INTEGER"},
      {"name": "big_small", "type": "STRING"},
      {"name": "odd_even", "type": "STRING"},
      {"name": "bs_streak", "type": "INTEGER"},
      {"name": "oe_streak", "type": "INTEGER"}
    ]
    ```

### 3.3 信号生成: `pc28.advanced_signals_v1` (视图)

-   **定位**: 战术中枢 (The Tactical Hub)
-   **描述**: 这是我们预测逻辑的核心。它读取`features_v1`的输出，并应用我们当前的核心战术，为**下一期**生成具体的做多/做空信号。
-   **核心逻辑 (SQL解读)**:
    1.  **计算目标**: 基于当前期的期号 (`period`)，直接计算出预测的目标期号 (`next_period = period + 1`)。
    2.  **应用“长龙反转”战术**: 当检测到“大小”或“单双”的连胜 (`streak`) 大于等于4时，生成一个与当前趋势相反的预测信号 (e.g., 如果当前是'BIG'，则预测'SMALL')。此信号的预设胜率为`0.65`。
    3.  **应用“趋势跟随”战术**: 无论是否存在长龙，都始终生成一个与当前趋势相同的预测信号 (e.g., 如果当前是'BIG'，则预测'BIG')。此信号的预设胜率为`0.55`。
    4.  **输出**: 将所有生成的信号，连同其目标期号 (`next_period`) 和预设胜率一起输出。
-   **表结构**:
    ```json
    [
      {"name": "period", "type": "STRING"},
      {"name": "timestamp", "type": "TIMESTAMP"},
      {"name": "s_reversal_bs", "type": "STRING"},
      {"name": "s_reversal_oe", "type": "STRING"},
      {"name": "s_follow_bs", "type": "STRING"},
      {"name": "s_follow_oe", "type": "STRING"},
      {"name": "p_reversal", "type": "FLOAT"},
      {"name": "p_follow", "type": "FLOAT"}
    ]
    ```

### 3.4 候选信号格式化: `pc28.candidates_v1` (视图)

-   **定位**: 弹药工厂 (The Ammunition Factory)
-   **描述**: `advanced_signals_v1` 输出的信号是“宽表”格式，不便于程序处理。此视图的核心任务是“逆透视”（Unpivot），将来自不同战术（反转、跟随）和不同市场（大小、单双）的信号，全部统一成“一期、一市场、一选择”的标准化格式。
-   **核心逻辑 (SQL解读)**:
    -   使用`UNION ALL`将`advanced_signals_v1`中的`s_reversal_bs`, `s_reversal_oe`, `s_follow_bs`, `s_follow_oe`等多个信号字段，合并成一个统一的“弹药”清单。每一行都包含期号、市场、预测选项和预设胜率。
-   **表结构**:
    ```json
    [
      {"name": "period", "type": "INTEGER"},
      {"name": "timestamp", "type": "TIMESTAMP"},
      {"name": "market", "type": "STRING"},
      {"name": "pick", "type": "STRING"},
      {"name": "p_win", "type": "FLOAT"}
    ]
    ```

### 3.5 最终预测记录: `pc28_lab.score_ledger` (表)

-   **定位**: 战功记录簿 (The Ledger of Scores)
-   **描述**: 这是我们预测流程的最终输出。当`trigger-betting-recorder-predict`触发预测服务后，服务会读取`candidates_v1`中的最新“弹药”，经过可能的模型计算或逻辑整合后，将最终决定下注的预测结果写入此表。
-   **表结构**:
    ```json
    [
      {"name": "day_id_cst", "type": "DATE"},
      {"name": "period", "type": "STRING"},
      {"name": "market", "type": "STRING"},
      {"name": "prediction", "type": "STRING"},
      {"name": "probability", "type": "FLOAT"},
      {"name": "stake_u", "type": "INTEGER"},
      {"name": "ev", "type": "FLOAT"},
      {"name": "outcome", "type": "STRING"},
      {"name": "pnl_u", "type": "INTEGER"},
      {"name": "timestamp", "type": "TIMESTAMP"},
      {"name": "tag", "type": "STRING"},
      {"name": "created_at", "type": "TIMESTAMP"},
      {"name": "note", "type": "STRING"}
    ]
    ```
