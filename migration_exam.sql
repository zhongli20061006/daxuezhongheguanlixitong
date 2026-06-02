ALTER TABLE classroom ADD COLUMN type VARCHAR(20) DEFAULT '普通教室' COMMENT '教室类型：普通教室/机房/实验室/阶梯教室';

CREATE TABLE IF NOT EXISTS exam (
    id INT AUTO_INCREMENT PRIMARY KEY,
    semester VARCHAR(20) NOT NULL,
    subject_id INT NOT NULL,
    schedule_id INT NOT NULL,
    exam_type VARCHAR(10) NOT NULL DEFAULT '统一考试',
    duration_minutes INT NOT NULL DEFAULT 120,
    status VARCHAR(10) NOT NULL DEFAULT '待排考',
    student_count INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS exam_arrangement (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exam_id INT NOT NULL,
    classroom_id INT NOT NULL,
    date DATE NOT NULL,
    start_time VARCHAR(20) NOT NULL,
    end_time VARCHAR(20) NOT NULL,
    invigilator_id VARCHAR(20) NULL,
    UNIQUE KEY uk_exam_room_time (classroom_id, date, start_time)
);

CREATE TABLE IF NOT EXISTS exam_student (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exam_id INT NOT NULL,
    student_id VARCHAR(20) NOT NULL,
    seat_no INT NULL,
    UNIQUE KEY uk_exam_student (exam_id, student_id)
);

CREATE TABLE IF NOT EXISTS exam_conflict (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exam_id_1 INT NOT NULL,
    exam_id_2 INT NOT NULL,
    conflict_type VARCHAR(50) NOT NULL,
    detail TEXT NULL
);
