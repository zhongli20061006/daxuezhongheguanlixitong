# docker-init.ps1 — 初始化学生管理系统种子数据
Write-Host "正在初始化数据库种子数据..." -ForegroundColor Cyan
docker compose exec backend python -m app.init_data
if ($LASTEXITCODE -eq 0) {
    Write-Host "初始化完成！" -ForegroundColor Green
    Write-Host ""
    Write-Host "测试账号（密码均为 test123456）："
    Write-Host "  管理员  : admin01"
    Write-Host "  教师    : T10001"
    Write-Host "  学生    : S2024001"
    Write-Host "  后勤    : G10001"
    Write-Host ""
    Write-Host "API 文档: http://localhost:8000/docs"
    Write-Host "前端页面: http://localhost"
} else {
    Write-Host "初始化失败，请检查容器是否正常运行" -ForegroundColor Red
}
