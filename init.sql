-- ============================================
-- 大学生管理系统 完整建库脚本（13张表）
-- 先执行：CREATE DATABASE student_management DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- 再执行：USE student_management;
-- 然后执行本文件
-- ============================================

-- 1. 教师表（无外键）
CREATE TABLE IF NOT EXISTS teacher (
    id INT PRIMARY KEY COMMENT '工号作为主键',
    name VARCHAR(50) NOT NULL,
    job_number VARCHAR(20) UNIQUE NOT NULL,
    department VARCHAR(100),
    title VARCHAR(50)
);

-- 2. 班级表（无外键）
CREATE TABLE IF NOT EXISTS class (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL COMMENT '如：2024级计算机科学1班',
    major VARCHAR(100),
    grade INT COMMENT '入学年份'
);

-- 3. 科目表（无外键）
CREATE TABLE IF NOT EXISTS subject (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    credit DECIMAL(2,1) NOT NULL,
    type ENUM('compulsory', 'limited', 'elective') NOT NULL COMMENT '必修/限选/选修',
    limited_group VARCHAR(20) NULL COMMENT '限选课组ID，如CS_2024_LTD_01',
    INDEX idx_type (type),
    INDEX idx_limited_group (limited_group)
);

-- 4. 教室表（无外键）
CREATE TABLE IF NOT EXISTS classroom (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) UNIQUE NOT NULL COMMENT '如D201',
    capacity INT NOT NULL COMMENT '容纳人数',
    building VARCHAR(50) COMMENT '教学楼',
    has_projector BOOLEAN DEFAULT FALSE
);

-- 5. 课表基础表（外键 → teacher, subject, class, classroom）
CREATE TABLE IF NOT EXISTS schedule (
    id INT PRIMARY KEY AUTO_INCREMENT,
    teacher_id INT NOT NULL,
    subject_id INT NOT NULL,
    class_id INT NOT NULL,
    classroom_id INT NOT NULL,
    weeks VARCHAR(20) NOT NULL COMMENT '如1-18或1-18(单)',
    day_of_week INT NOT NULL COMMENT '1=周一,7=周日',
    period VARCHAR(10) NOT NULL COMMENT '如1-2表示第1-2节',
    semester VARCHAR(20) NOT NULL COMMENT '如2024-2025-1',
    FOREIGN KEY (teacher_id) REFERENCES teacher(id),
    FOREIGN KEY (subject_id) REFERENCES subject(id),
    FOREIGN KEY (class_id) REFERENCES class(id),
    FOREIGN KEY (classroom_id) REFERENCES classroom(id),
    INDEX idx_class_semester (class_id, semester),
    INDEX idx_teacher_semester (teacher_id, semester),
    INDEX idx_classroom_semester (classroom_id, semester)
);

-- 6. 课程容量表（外键 → schedule）
CREATE TABLE IF NOT EXISTS course_capacity (
    schedule_id INT PRIMARY KEY,
    enrolled INT NOT NULL DEFAULT 0,
    capacity INT NOT NULL,
    FOREIGN KEY (schedule_id) REFERENCES schedule(id),
    INDEX idx_schedule_capacity (schedule_id, enrolled, capacity)
);

-- 7. 选课记录表（外键 → schedule）
CREATE TABLE IF NOT EXISTS course_selection (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id VARCHAR(20) NOT NULL COMMENT '学号',
    schedule_id INT NOT NULL,
    select_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TINYINT NOT NULL DEFAULT 1 COMMENT '1=已选,0=已退',
    cancel_time DATETIME NULL,
    FOREIGN KEY (schedule_id) REFERENCES schedule(id),
    UNIQUE KEY uk_student_schedule (student_id, schedule_id, status),
    INDEX idx_student_status (student_id, status),
    INDEX idx_schedule_status (schedule_id, status)
);

-- 8. 用户认证表（无外键）
CREATE TABLE IF NOT EXISTS user_credential (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL COMMENT '学号或工号',
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('student', 'teacher', 'staff', 'admin') NOT NULL,
    role_id VARCHAR(20) NOT NULL COMMENT '对应角色表的ID',
    must_change_password BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_role (role, role_id)
);

-- 9. 学生表（外键 → class）
CREATE TABLE IF NOT EXISTS student (
    id VARCHAR(20) PRIMARY KEY COMMENT '学号作为主键',
    name VARCHAR(50) NOT NULL,
    phone VARCHAR(20),
    id_card VARCHAR(18),
    class_id INT,
    FOREIGN KEY (class_id) REFERENCES class(id)
);

-- 10. 后勤工人表（无外键）
CREATE TABLE IF NOT EXISTS staff (
    id VARCHAR(20) PRIMARY KEY COMMENT '工号作为主键',
    name VARCHAR(50) NOT NULL,
    phone VARCHAR(20),
    department VARCHAR(100),
    job_type VARCHAR(50) COMMENT '维修/清洁/餐饮等'
);

-- 11. 成绩表（外键 → student, schedule）
CREATE TABLE IF NOT EXISTS score (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id VARCHAR(20) NOT NULL,
    schedule_id INT NOT NULL,
    score DECIMAL(4,1) NULL COMMENT '百分制分数，总评记录为NULL',
    gpa DECIMAL(2,1) NOT NULL COMMENT '绩点，5分制',
    score_type ENUM('平时', '期末', '总评') NOT NULL DEFAULT '总评',
    attempt TINYINT NOT NULL DEFAULT 1 COMMENT '1=首次,2=补考',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES student(id),
    FOREIGN KEY (schedule_id) REFERENCES schedule(id),
    UNIQUE KEY uk_student_schedule_type_attempt (student_id, schedule_id, score_type, attempt)
);

-- 12. 报修表（无外键）
CREATE TABLE IF NOT EXISTS repair (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(20) NOT NULL COMMENT '学号或工号',
    role ENUM('student', 'teacher', 'staff') NOT NULL,
    location VARCHAR(200) NOT NULL,
    type ENUM('水电设备', '电子产品', '家具类', '教学用具') NOT NULL,
    description TEXT NOT NULL,
    status ENUM('提交', '已接单', '处理中', '已完成', '已确认', '已取消') NOT NULL DEFAULT '提交',
    assigned_worker_id VARCHAR(20) NULL,
    submit_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    accept_time DATETIME NULL,
    complete_time DATETIME NULL,
    confirm_time DATETIME NULL,
    cancel_time DATETIME NULL,
    INDEX idx_user (user_id),
    INDEX idx_status (status),
    INDEX idx_worker (assigned_worker_id)
);

-- 13. 系统配置表（无外键）
CREATE TABLE IF NOT EXISTS system_config (
    config_key VARCHAR(50) PRIMARY KEY,
    config_value VARCHAR(255) NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
