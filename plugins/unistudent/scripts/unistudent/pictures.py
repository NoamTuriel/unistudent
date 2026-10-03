"""Drawers for the curated picture kinds (ADR 0010): a small JSON spec in, a PNG beside it.

Each library is imported inside its drawer; the dispatcher (draw.py) makes sure it is installed first.
"""
import json
from pathlib import Path

from .common import UserError


def _load(spec_path):
    try:
        return json.loads(Path(spec_path).read_text("utf-8"))
    except (OSError, ValueError) as error:
        raise UserError(f"I can't read the spec {spec_path}: it must be valid JSON ({error}).")


def _fresh(spec_path, force):
    png = Path(spec_path).with_suffix(".png")
    return png, (not force and png.exists() and png.stat().st_mtime >= Path(spec_path).stat().st_mtime)


def circuit(spec_path, force=False):
    """Spec: a list of {"el": "Resistor", "dir": "right", "label": "R1"} drawn one after the other."""
    png, fresh = _fresh(spec_path, force)
    spec = _load(spec_path)
    if fresh:
        return {"png": str(png), "drawn": False}
    import schemdraw
    import schemdraw.elements as elm
    if not isinstance(spec, list) or not spec:
        raise UserError('A circuit spec is a list such as [{"el": "SourceV", "dir": "up", "label": "V"}, ...].')
    with schemdraw.Drawing(show=False) as drawing:
        for part in spec:
            element = getattr(elm, str(part.get("el", "")), None)
            if element is None:
                raise UserError(f'There is no circuit element "{part.get("el")}" (try Resistor, Capacitor, Inductor, SourceV, Line).')
            item = element()
            if part.get("dir"):
                item = getattr(item, part["dir"])()
            if part.get("label"):
                item = item.label(part["label"])
            drawing += item
        drawing.save(str(png), dpi=200)
    return {"png": str(png), "drawn": True}


def molecule(spec_path, force=False):
    """Spec: {"smiles": "CCO"} for a structure, or {"reaction": "CC(=O)O.N>>CC(=O)N"} for a reaction scheme."""
    png, fresh = _fresh(spec_path, force)
    spec = _load(spec_path)
    if fresh:
        return {"png": str(png), "drawn": False}
    from rdkit import Chem
    from rdkit.Chem import AllChem, Draw
    if spec.get("reaction"):
        reaction = AllChem.ReactionFromSmarts(spec["reaction"], useSmiles=True)
        Draw.ReactionToImage(reaction, subImgSize=(300, 250)).save(str(png))
    elif spec.get("smiles"):
        mol = Chem.MolFromSmiles(spec["smiles"])
        if mol is None:
            raise UserError(f'"{spec["smiles"]}" is not a structure I can read; check the SMILES written from the course notation.')
        Draw.MolToFile(mol, str(png), size=(400, 300))
    else:
        raise UserError('A molecule spec has "smiles" (one structure) or "reaction" (reactants>>products).')
    return {"png": str(png), "drawn": True}


def tree(spec_path, force=False):
    """Spec: {"newick": "((A:1,B:1):1,(C:1,D:1):2);"} drawn as a phylogenetic tree."""
    png, fresh = _fresh(spec_path, force)
    spec = _load(spec_path)
    if fresh:
        return {"png": str(png), "drawn": False}
    from io import StringIO
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from Bio import Phylo
    if not spec.get("newick"):
        raise UserError('A tree spec has "newick", for example "((A,B),(C,D));".')
    try:
        phylo = Phylo.read(StringIO(spec["newick"]), "newick")
    except Exception as error:
        raise UserError(f"I can't read that Newick tree ({error}).")
    fig = plt.figure(figsize=(5.2, 4), dpi=150)
    Phylo.draw(phylo, axes=fig.add_subplot(1, 1, 1), do_show=False)
    fig.savefig(png, bbox_inches="tight")
    plt.close(fig)
    return {"png": str(png), "drawn": True}
