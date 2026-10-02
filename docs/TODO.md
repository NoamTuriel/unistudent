# TODO: known gaps

Remove an item when it ships.

## Revisit the course-specific skills (economics, macro)
In ticket 20 the owner built unit Study packs from the generic rules alone and they were good. Decide whether the course skills earn their place:
- Read what the economics and macro skills add on top of the generic rules.
- Build a partial pack with and without them and compare.
- Keep them (then one field skill per major is needed: math, physics, computer science, and so on) or fold the useful parts into the generic rules and drop them.

## Generic tools for better unit packs (graphs, pictures, flowcharts)
Goals:
- Unit packs teach with visuals as close as possible to the real course material (the lecturer's own diagrams, graphs and figures in style and content).
- Make the plugin more useful on demand: once a student knows it can make great graphs and diagrams, they can ask for one directly, for example "create a complete flowchart and graph to illustrate how raising money in the market affects market Y". The plugin should deliver that well, grounded in the course material.

The plugin already has a graph tool. Think about what other field-agnostic tools would help unit packs across most university degrees, and whether the plugin should ship them or only recommend installing them.
- Candidates to evaluate: diagrams and flowcharts (Mermaid, Graphviz), plots and charts, math and equation rendering, generated or annotated pictures, timelines, concept maps, tables, code or circuit or chemistry drawing.
- Rank candidates by how many degrees they help.
- Decide first, before building anything: pros and cons of bundling tools in the plugin (works out of the box, consistent output, but more to maintain, dependencies, install size, platform issues) versus recommending the student install them (lighter plugin, student choice, but setup friction and unreliable results).
- Then pick per tool: bundle, recommend, or skip.
