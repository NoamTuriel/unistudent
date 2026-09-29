# Working on this repo

- Use the vocabulary in `CONTEXT.md` in code, tests, skills and docs. Respect the decisions in `docs/adr/`.
- Tests: `python3 -m unittest discover -s tests`. Write tests only at the three seams (sync, Wiki build, grounding), through the `us.py` command line.
- Scripts: Python standard library only; optional libraries behind `try/except ImportError`. OS-specific behaviour lives in `links.py` and `recordings.py` only.
- Skills and agents follow `writing-for-agents`: steps with "Done when" criteria, one source of truth per rule. The grounding rule's single source is `plugins/unistudent/templates/CLAUDE.md`; study-pack generic rules live in `plugins/unistudent/reference/study-pack.md`.
- Subject plugins never depend on a university plugin; university plugins never hold study-pack rules.
- Never commit course material.
