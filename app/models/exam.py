"""
考试系统模型
"""
from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import String, Integer, Date, DateTime, Text, Index, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Exam(Base):
    __tablename__ = "exam"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="考试ID")
    semester: Mapped[str] = mapped_column(String(20), nullable=False, comment="学期，如2024-2025-1")
    subject_id: Mapped[int] = mapped_column(ForeignKey("subject.id"), nullable=False, comment="科目ID")
    schedule_id: Mapped[int] = mapped_column(ForeignKey("schedule.id"), nullable=False, comment="课表ID")
    exam_type: Mapped[str] = mapped_column(String(10), nullable=False, default="统一考试", comment="统一考试/随堂考试")
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=120, comment="考试时长(分钟)")
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="待排考", comment="待排考/已排考/已发布/已结束")
    student_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="参考学生数")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class ExamArrangement(Base):
    __tablename__ = "exam_arrangement"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="安排ID")
    exam_id: Mapped[int] = mapped_column(ForeignKey("exam.id"), nullable=False, comment="考试ID")
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classroom.id"), nullable=False, comment="教室ID")
    date: Mapped[date] = mapped_column(Date, nullable=False, comment="考试日期")
    start_time: Mapped[str] = mapped_column(String(20), nullable=False, comment="开始时间，如08:00")
    end_time: Mapped[str] = mapped_column(String(20), nullable=False, comment="结束时间")
    invigilator_id: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="监考人工号")

    __table_args__ = (Index("uk_classroom_time", "classroom_id", "date", "start_time", unique=True),)


class ExamStudent(Base):
    __tablename__ = "exam_student"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exam.id"), nullable=False, comment="考试ID")
    student_id: Mapped[str] = mapped_column(ForeignKey("student.id"), nullable=False, comment="学号")
    seat_no: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="座位号")

    __table_args__ = (Index("uk_exam_student", "exam_id", "student_id", unique=True),)


class ExamConflict(Base):
    __tablename__ = "exam_conflict"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id_1: Mapped[int] = mapped_column(Integer, nullable=False)
    exam_id_2: Mapped[int] = mapped_column(Integer, nullable=False)
    conflict_type: Mapped[str] = mapped_column(String(50), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
