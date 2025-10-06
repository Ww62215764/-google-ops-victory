# 闹钟1: [恢复] 数据采集触发器 (trigger-draws-collector)
# 这将修复我们当前的P0级故障
resource "google_cloud_scheduler_job" "draws_collector_scheduler" {
  name        = "trigger-draws-collector"
  description = "[IaC] 每5分钟自动触发一次'drawsguard-api-collector'数据采集服务。"
  schedule    = "*/5 * * * *"
  time_zone   = "Asia/Shanghai"

  http_target {
    http_method = "POST"
    uri         = "https://drawsguard-api-collector-rjysxlgksq-uc.a.run.app/collect"
    
    oidc_token {
      service_account_email = "644485179199-compute@developer.gserviceaccount.com"
    }
  }

  retry_config {
    retry_count = 1
  }
}

# 闹钟2: [纳管] 预测触发器 (trigger-betting-recorder-predict)
# 将现有的预测触发器也纳入代码管理，防止其未来也“静默失踪”
resource "google_cloud_scheduler_job" "betting_recorder_scheduler" {
  name        = "trigger-betting-recorder-predict"
  description = "[IaC] 每3分钟自动触发一次'betting-recorder'预测引擎。"
  schedule    = "*/3 * * * *"
  time_zone   = "Asia/Shanghai"

  http_target {
    http_method = "POST"
    uri         = "https://betting-recorder-644485179199.us-central1.run.app/predict"
    
    oidc_token {
      service_account_email = "644485179199-compute@developer.gserviceaccount.com"
      audience            = "https://betting-recorder-644485179199.us-central1.run.app/predict"
    }
  }
}
