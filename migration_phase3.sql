-- Phase 3 数据库迁移
-- 新增7张表 + 修改class表

-- 1. class表新增advisor_id字段
ALTER TABLE class ADD COLUMN advisor_id INT NULL COMMENT '辅导员工号' AFTER grade;

-- 2. 通知表
CREATE TABLE IF NOT EXISTS notification (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '通知ID',
    title VARCHAR(200) NOT NULL COMMENT '通知标题',
    content TEXT NOT NULL COMMENT '通知正文',
    event_type VARCHAR(50) NULL COMMENT '触发事件类型',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. 通知用户关联表
CREATE TABLE IF NOT EXISTS notification_user (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    notification_id INT NOT NULL COMMENT '通知ID',
    recipient_role VARCHAR(20) NULL COMMENT '接收角色',
    recipient_id VARCHAR(20) NULL COMMENT '接收人ID',
    is_read TINYINT NOT NULL DEFAULT 0 COMMENT '是否已读',
    INDEX idx_notification (notification_id),
    INDEX idx_recipient (recipient_id, recipient_role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. 请假申请表
CREATE TABLE IF NOT EXISTS leave_application (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '请假ID',
    student_id VARCHAR(20) NOT NULL COMMENT '学号',
    start_date DATE NOT NULL COMMENT '开始日期',
    end_date DATE NOT NULL COMMENT '结束日期',
    total_days INT NOT NULL COMMENT '请假天数',
    reason TEXT NOT NULL COMMENT '请假原因',
    status VARCHAR(20) NOT NULL DEFAULT '提交' COMMENT '状态',
    submit_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. 审批记录表
CREATE TABLE IF NOT EXISTS approval_record (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '审批ID',
    leave_id INT NOT NULL COMMENT '请假申请ID',
    approver_id VARCHAR(20) NOT NULL COMMENT '审批人工号',
    approver_role VARCHAR(20) NOT NULL COMMENT '审批人角色',
    level INT NOT NULL COMMENT '审批级别',
    result VARCHAR(20) NOT NULL COMMENT '审批结果',
    comment TEXT NULL COMMENT '审批意见',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '审批时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. 审批配置表
CREATE TABLE IF NOT EXISTS approval_config (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '配置ID',
    min_days INT NOT NULL COMMENT '最小天数(含)',
    max_days INT NULL COMMENT '最大天数(含)',
    required_levels VARCHAR(50) NOT NULL COMMENT '需要审批级别'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 默认配置：<3天只需辅导员审批，>=3天需要辅导员+学院审批
INSERT INTO approval_config (min_days, max_days, required_levels) VALUES
    (1, 2, '1'),
    (3, NULL, '1,2');

-- 7. 培养方案表
CREATE TABLE IF NOT EXISTS training_plan (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '方案ID',
    major VARCHAR(100) NOT NULL COMMENT '专业名称',
    grade INT NOT NULL COMMENT '入学年级',
    total_credits_required DECIMAL(5,1) NOT NULL COMMENT '总学分要求',
    elective_credits_required DECIMAL(5,1) NOT NULL COMMENT '选修学分要求',
    UNIQUE KEY uk_major_grade (major, grade)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. 培养方案课程明细表
CREATE TABLE IF NOT EXISTS plan_course (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '明细ID',
    plan_id INT NOT NULL COMMENT '方案ID',
    subject_id INT NOT NULL COMMENT '科目ID',
    course_type VARCHAR(20) NOT NULL COMMENT '课程类型',
    limited_group VARCHAR(50) NULL COMMENT '限选组名',
    min_required INT NULL COMMENT '限选组至少选几门',
    credit DECIMAL(4,1) NOT NULL COMMENT '课程学分'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. 毕业审核表
CREATE TABLE IF NOT EXISTS graduation_audit (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '审核ID',
    student_id VARCHAR(20) NOT NULL COMMENT '学号',
    plan_id INT NOT NULL COMMENT '培养方案ID',
    total_credits_earned DECIMAL(5,1) NOT NULL DEFAULT 0 COMMENT '已获总学分',
    elective_credits_earned DECIMAL(5,1) NOT NULL DEFAULT 0 COMMENT '已获选修学分',
    compulsory_passed INT NOT NULL DEFAULT 0 COMMENT '必修通过门数',
    compulsory_total INT NOT NULL DEFAULT 0 COMMENT '必修总门数',
    limited_groups_passed VARCHAR(500) NULL COMMENT '限选组满足情况',
    is_graduatable TINYINT NOT NULL DEFAULT 0 COMMENT '是否可毕业',
    detail VARCHAR(2000) NULL COMMENT '审核详情',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_student_plan (student_id, plan_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
