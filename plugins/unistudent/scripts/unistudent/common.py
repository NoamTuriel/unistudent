"""Shared by the command modules: finding the course, and errors shown to the student."""
from .course import Course, find_course


class UserError(Exception):
    """A problem the student can fix; printed as a message, never as a traceback."""


def problems_summary(problems, line) -> str:
    """"N problems." and one bullet per problem, `line(problem)` being its text."""
    return f"{len(problems)} problems." + "".join(f"\n- {line(p)}" for p in problems)


def resolve_course(args) -> Course:
    course = Course(args.course) if getattr(args, "course", None) else find_course()
    if course is None or not course.exists():
        raise UserError("No course folder found. Run setup first, or pass --course <folder>.")
    return course
