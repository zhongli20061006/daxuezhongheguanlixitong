#!/bin/bash
# docker-init.sh — 初始化学生管理系统种子数据
set -e

echo "正在初始化数据库种子数据..."
docker compose exec backend python -m app.init_data

echo ""
echo "初始化完成！"
echo ""
echo "测试账号（密码均为 test123456）："
echo "  管理员  : admin01"
echo "  教师    : T10001"
echo "  学生    : S2024001"
echo "  后勤    : G10001"
echo ""
echo "API 文档: http://localhost:8000/docs"
echo "前端页面: http://localhost"
