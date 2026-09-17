from app.extensions import db
from app.models.base import TimestampMixin

# 课表：周一~周五，每天 12 节课
COURSE_FIELDS = [
    "courseFirst",
    "courseSecond",
    "courseThird",
    "courseFourth",
    "courseFifth",
    "courseSixth",
    "courseSeventh",
    "courseEighth",
    "courseNinth",
    "courseTenth",
    "courseEleventh",
    "courseTwelfth",
]


class Course(db.Model, TimestampMixin):
    """课程表，按用户 + 星期存储。week: 1=周一 ... 5=周五。"""

    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    account = db.Column(db.String(64), nullable=False, index=True)
    week = db.Column(db.SmallInteger, nullable=False)  # 1-5

    course_first = db.Column(db.String(255), default="")
    course_second = db.Column(db.String(255), default="")
    course_third = db.Column(db.String(255), default="")
    course_fourth = db.Column(db.String(255), default="")
    course_fifth = db.Column(db.String(255), default="")
    course_sixth = db.Column(db.String(255), default="")
    course_seventh = db.Column(db.String(255), default="")
    course_eighth = db.Column(db.String(255), default="")
    course_ninth = db.Column(db.String(255), default="")
    course_tenth = db.Column(db.String(255), default="")
    course_eleventh = db.Column(db.String(255), default="")
    course_twelfth = db.Column(db.String(255), default="")

    __table_args__ = (
        db.UniqueConstraint("account", "week", name="uq_course_user_week"),
    )

    def to_dict(self):
        return {
            "account": self.account,
            "week": self.week,
            "courseFirst": self.course_first,
            "courseSecond": self.course_second,
            "courseThird": self.course_third,
            "courseFourth": self.course_fourth,
            "courseFifth": self.course_fifth,
            "courseSixth": self.course_sixth,
            "courseSeventh": self.course_seventh,
            "courseEighth": self.course_eighth,
            "courseNinth": self.course_ninth,
            "courseTenth": self.course_tenth,
            "courseEleventh": self.course_eleventh,
            "courseTwelfth": self.course_twelfth,
        }