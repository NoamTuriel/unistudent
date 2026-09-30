"""Shared by the command modules: finding the course, and errors shown to the student."""
from .course import Course, find_course


class UserError(Exception):
    """A problem the student can fix; printed as a message, never as a traceback."""


def resolve_course(args) -> Course:
    course = Course(args.course) if getattr(args, "course", None) else find_course()
    if course is None or not course.exists():
        raise UserError("No course folder found. Run setup first, or pass --course <folder>.")
    return course
