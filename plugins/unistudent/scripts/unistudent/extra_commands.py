"""Commands added by later tickets (Wiki, inbox, preferences, recordings, checks)."""
from pathlib import Path


def register(add, with_course):
    from . import wiki
    from .cli import resolve_course

    def cmd_wiki(args):
        course = resolve_course(args)
        if args.action == "check":
            return wiki.check(course)
        return wiki.build(course, force=args.force)

    p = with_course(add("wiki", cmd_wiki, "build or check the Wiki"))
    p.add_argument("action", choices=["build", "check"])
    p.add_argument("--force", action="store_true", help="convert every file again")
