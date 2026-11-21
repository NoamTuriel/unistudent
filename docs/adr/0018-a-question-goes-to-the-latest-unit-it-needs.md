# A question goes to the latest unit it needs

A question that needed two units used to carry both units' tags "so it reaches both study packs". The student studying the earlier unit then met a question they could not solve yet: half of it is taught later. Now a question belongs to its Question's unit, the latest unit, in teaching order, whose method, notation or assumption it needs, wherever the course put it (even in an earlier unit's own exercise file). A unit is whatever group of topics the course teaches together, numbered in the order it teaches them, so the rule works for chapters, weeks or modules alike.

We kept one exception, chosen by the student: a question whose parts end in different units also appears in each earlier unit where one of its parts ends, with only those parts ("parts a–b only"). So the question bank keeps one tag per unit where a part ends and, with more than one, a `Parts by unit` line saying which parts each gets. A question placed whole in the latest unit only would be simpler, but the student would lose the parts they can already practise.

The merge still joins every writer's tags. A wrong tag is caught by checks instead of by the merge: `us wiki check` flags an entry tagged to two units without a `Parts by unit` line (every entry written under the old rule) or with one that disagrees with its tags, and the verifier flags a Practice question that needs a later unit. We considered a `Needs:` line on every question (the units it uses), checkable by code, and left it out: it costs every writer tokens on every question, and the two checks catch the same mistakes.

The past-exam index keeps one unit per question, the latest any part needs: the before-test plan covers the whole course, so a split there would add nothing.
