# Three plugin layers: core, university, subject

The subject layer is superseded by ADR 0011: two layers remain, core and university.

The repo ships a university-agnostic core plugin, one plugin per university (v1: Open University), and subject plugins (v1: economics with the macro course skill). University plugins own site access and unit sorting; subject plugins own study-pack rules and never depend on a university. We chose this over one OpenU plugin so that adding a university or a subject touches one plugin only.
