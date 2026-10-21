# -*- coding: utf-8 -*-
"""Funding-Fit Memo: build the rule-derived massing in Revit, put it on an annotated sheet,
and export the sheet, from one run folder (massing.json + ledger.json).

Runs three ways, same code:

  A. Inside Revit with pyRevit (pyRevit > Tools > Run, pick this file) or RevitPythonShell:
     builds into the ACTIVE document; a dialog asks for massing.json unless FFM_MASSING_JSON is set.

  B. Headless, from a terminal, with the pyRevit CLI (what Claude Code runs):
       $env:FFM_MASSING_JSON = "C:\\...\\outputs\\998-e-19th-ave\\2026-10-23\\massing.json"
       $env:FFM_SAVE_AS      = "C:\\...\\outputs\\998-e-19th-ave\\2026-10-23\\ffm_massing.rvt"
       pyrevit run revit\\ffm_massing_pyrevit.py --revit=2025 --purge
     With no active document the script creates a new project (FFM_TEMPLATE = an .rte path if
     set, else Revit's default metric template), builds, saves to FFM_SAVE_AS and closes.

  C. Headless against an existing model:
       pyrevit run revit\\ffm_massing_pyrevit.py "C:\\path\\to\\model.rvt" --revit=2025

Stages, each in its own transaction so a later failure never loses an earlier result:

  0 links         headless only: links the template points at that no longer exist are deleted, so
                  the saved file opens without the "Unresolved References" dialog
  1 masses        Mass-category DirectShapes (proposed, outright), floor plates, lot and setback
                  model lines; the version stamp in every element's Comments
  2 views         a 3D axon with a section box, a plan at Level 1 cropped to the lot, a section
                  across the frontage; Mass category made visible in each
  3 annotations   dimensions of the lot and the setback envelope in the plan; text labels in the
                  plan and section; benchmark and outright-height lines in the section
  4 sheet         a sheet (title block if the template has one) with the three views and four
                  text blocks taken from ledger.json: the three answers, the open items, the
                  massing numbers, the stamp
  5 export        the sheet as PDF (Revit 2022+) and PNG, next to massing.json

Outputs next to massing.json: ffm_revit_result.json (what was built, element ids, errors by
stage), ffm_sheet_notes.json (the exact text placed on the sheet, so the memo can quote it),
ffm_sheet.pdf / ffm_sheet.png when export succeeds, and the .rvt when saving.

Units: massing.json is metres with the origin at the front-left lot corner (x along the frontage,
y into the lot, z up); Revit works in feet internally, so every length is converted. The street is
along y = 0. Mass visibility is off by default in Revit views; the script turns it on in the views
it makes. IronPython 2.7 and CPython 3 compatible: no f-strings, no annotations.
"""

import glob
import json
import os
import traceback

import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from System.Collections.Generic import List  # noqa: E402
from Autodesk.Revit.DB import (  # noqa: E402
    BoundingBoxXYZ, BuiltInCategory, BuiltInParameter, CurveLoop, DirectShape, ElementId,
    ElementTypeGroup, ExportRange, ExternalFileUtils, FilteredElementCollector, GeometryCreationUtilities,
    GeometryObject, HorizontalTextAlignment, ImageExportOptions, ImageFileType, ImageResolution, ImageType,
    Level, Line, ModelPathUtils, Plane, ReferenceArray, SaveAsOptions, SketchPlane, TextNote,
    TextNoteOptions, TextNoteType, Transaction, Transform, UnitSystem, VerticalTextAlignment, View3D,
    ViewFamily, ViewFamilyType, ViewOrientation3D, ViewPlan, ViewSection, ViewSheet, Viewport, XYZ,
    ZoomFitType,
)

FT_PER_M = 1.0 / 0.3048
PLATE_THICKNESS_M = 0.15
VIEW_SCALE = 250          # starting scale; the sheet stage picks the largest of 300..1000 that fits the title block
LABEL_ROOM_M = 26.0       # metres kept clear to the right of the section for its height labels
SHEET_NUMBER = "FFM-01"
NL = "\r\n"

uiapp = __revit__  # noqa: F821  (injected by pyRevit / RevitPythonShell)
app = uiapp.Application


# ---------------------------------------------------------------- helpers

def m(x):
    return float(x) * FT_PER_M


def pick_massing_file():
    env = os.environ.get("FFM_MASSING_JSON")
    if env and os.path.exists(env):
        return env
    here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else None
    if here and os.path.exists(os.path.join(here, "massing.json")):
        return os.path.join(here, "massing.json")
    try:
        from pyrevit import forms
        path = forms.pick_file(file_ext="json", title="Pick massing.json from the Funding-Fit Memo run")
        if path:
            return path
    except Exception:
        pass
    return None


def load_json(path):
    with open(path, "r") as fh:
        return json.load(fh)


def set_comment(el, text):
    try:
        p = el.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        if p and not p.IsReadOnly:
            p.Set(text)
    except Exception:
        pass


def id_value(el):
    try:
        v = el.Id.Value  # Revit 2024+: an Int64, which IronPython 2.7 sees as a long
    except Exception:
        v = el.Id.IntegerValue
    return int(v)  # IronPython 2.7's json module cannot serialize a long


def view_family_type(doc, family):
    for vft in FilteredElementCollector(doc).OfClass(ViewFamilyType):
        if vft.ViewFamily == family:
            return vft
    return None


def first_level(doc):
    levels = list(FilteredElementCollector(doc).OfClass(Level))
    levels.sort(key=lambda lv: lv.Elevation)
    return levels[0] if levels else None


def safe_name(el, name):
    """Set a view or sheet name, adding a counter if the name is taken (a second run in one model)."""
    for i in range(0, 50):
        try:
            el.Name = name if i == 0 else "{0} ({1})".format(name, i)
            return
        except Exception:
            continue


def show_mass(view):
    """Make the Mass category visible in a view the script made. A view template applied by the
    view type (office templates do this) would lock the category off, so it is detached first."""
    try:
        if view.ViewTemplateId != ElementId.InvalidElementId:
            view.ViewTemplateId = ElementId.InvalidElementId
    except Exception:
        pass
    try:
        cat = ElementId(BuiltInCategory.OST_Mass)
        if view.CanCategoryBeHidden(cat):
            view.SetCategoryHidden(cat, False)
    except Exception:
        pass


def new_document():
    """A fresh project for headless runs. Order: FFM_TEMPLATE (an .rte path) if set; Revit's own
    default metric template; any metric .rte under ProgramData. Returns (doc, description).
    Prefer Revit's shipped templates: an office template can carry links to files that are not on
    this machine, and Revit may stop on a dialog about them when it opens headlessly."""
    env = os.environ.get("FFM_TEMPLATE")
    if env and os.path.exists(env):
        return app.NewProjectDocument(env), "template " + os.path.basename(env)   # name only: the memo quotes this line
    try:
        return app.NewProjectDocument(UnitSystem.Metric), "Revit default metric template"
    except Exception:
        pass
    ver = app.VersionNumber
    root = r"C:\ProgramData\Autodesk\RVT {0}\Templates".format(ver)
    cands = glob.glob(os.path.join(root, "*", "*.rte")) + glob.glob(os.path.join(root, "*.rte"))
    cands.sort(key=lambda p: (0 if "metric" in p.lower() else 1, len(p)))
    for c in cands:
        try:
            return app.NewProjectDocument(c), "template " + os.path.basename(c)
        except Exception:
            continue
    raise Exception("Could not create a new project: set FFM_TEMPLATE to an .rte path (no default or metric template found for Revit {0})".format(ver))


class Stage(object):
    """Run fn(doc) inside its own transaction; record success or the traceback."""

    def __init__(self, doc, result):
        self.doc, self.result = doc, result

    def run(self, name, fn):
        t = Transaction(self.doc, "FFM " + name)
        t.Start()
        try:
            out = fn()
            t.Commit()
            self.result["stages"][name] = "ok"
            return out
        except Exception:
            t.RollBack()
            self.result["stages"][name] = "failed"
            self.result["errors"].append({"stage": name, "traceback": traceback.format_exc()})
            return None


# ---------------------------------------------------------------- stage 0: links (new project from a template only)

DROPPABLE_REFERENCE_TYPES = ("CADLink", "DWFMarkup", "RevitLink", "Decal")


def _local_path(path):
    return bool(path) and (path[1:3] == ":\\" or path.startswith("\\\\"))


def stage_links(doc, result):
    """Delete links the template points at that no longer exist (CAD, DWF markup, Revit, decal and
    linked raster images), so the saved model opens without Revit's 'Unresolved References' dialog.
    Keynote and assembly-code tables are left alone. What was dropped is listed in the result."""
    removed = []
    try:
        ids = list(ExternalFileUtils.GetAllExternalFileReferences(doc))
    except Exception:
        ids = []
    for eid in ids:
        try:
            ref = ExternalFileUtils.GetExternalFileReference(doc, eid)
            kind = str(ref.ExternalFileReferenceType)
            path = ModelPathUtils.ConvertModelPathToUserVisiblePath(ref.GetAbsolutePath())
            status = str(ref.GetLinkedFileStatus())
        except Exception:
            continue
        if kind not in DROPPABLE_REFERENCE_TYPES:
            continue
        if not (status == "NotFound" or (_local_path(path) and not os.path.exists(path))):
            continue
        entry = {"type": kind, "path": path, "status": status}
        try:
            doc.Delete(eid)
        except Exception:
            entry["error"] = traceback.format_exc()
        removed.append(entry)
    # Linked raster images are not external file references to the API above, but a missing one
    # still raises the dialog.
    try:
        images = list(FilteredElementCollector(doc).OfClass(ImageType))
    except Exception:
        images = []
    for it in images:
        try:
            if str(it.Source) != "Link":
                continue
            path = it.Path
        except Exception:
            continue
        if not _local_path(path) or os.path.exists(path):
            continue
        entry = {"type": "LinkedImage", "path": path, "status": "NotFound", "element_id": id_value(it)}
        try:
            doc.Delete(it.Id)
        except Exception:
            entry["error"] = traceback.format_exc()
        removed.append(entry)
    if removed:
        result["removed_links"] = removed
    return removed


# ---------------------------------------------------------------- stage 1: masses

def loop_from_polygon(poly, z_m=0.0):
    pts = [XYZ(m(x), m(y), m(z_m)) for x, y in poly]
    loop = CurveLoop()
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        if a.DistanceTo(b) > 1e-6:
            loop.Append(Line.CreateBound(a, b))
    return loop


def make_extrusion(doc, poly, base_z_m, height_m, name, comments):
    loops = List[CurveLoop]()
    loops.Add(loop_from_polygon(poly, base_z_m))
    solid = GeometryCreationUtilities.CreateExtrusionGeometry(loops, XYZ.BasisZ, m(height_m))
    ds = DirectShape.CreateElement(doc, ElementId(BuiltInCategory.OST_Mass))
    ds.ApplicationId = "ffm"
    ds.ApplicationDataId = name
    shapes = List[GeometryObject]()
    shapes.Add(solid)
    ds.SetShape(shapes)
    try:
        ds.Name = name
    except Exception:
        pass
    set_comment(ds, comments)
    return ds


def make_model_lines(doc, poly, z_m, label, closed=True):
    plane = Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ(0, 0, m(z_m)))
    sp = SketchPlane.Create(doc, plane)
    made = []
    pts = [XYZ(m(x), m(y), m(z_m)) for x, y in poly]
    n = len(pts) if closed else len(pts) - 1
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        if a.DistanceTo(b) > 1e-6:
            mc = doc.Create.NewModelCurve(Line.CreateBound(a, b), sp)
            set_comment(mc, label)
            made.append(mc)
    return made


def dash_line(doc, mc):
    """Give a model line a dashed line style if the document has one (names differ by template)."""
    try:
        wanted = ("dash", "hidden", "overhead", "centerline", "centre")
        for sid in mc.GetLineStyleIds():
            gs = doc.GetElement(sid)
            name = (gs.Name or "").lower()
            if any(w in name for w in wanted):
                mc.LineStyle = gs
                return True
    except Exception:
        pass
    return False


def make_horizontal_line_in_section(doc, y_m, z_m, x0_m, x1_m, label, dashed=False):
    """A model line at height z across the frontage, in a vertical plane just behind the section cut."""
    plane = Plane.CreateByNormalAndOrigin(XYZ.BasisY, XYZ(0, m(y_m), 0))
    sp = SketchPlane.Create(doc, plane)
    mc = doc.Create.NewModelCurve(Line.CreateBound(XYZ(m(x0_m), m(y_m), m(z_m)), XYZ(m(x1_m), m(y_m), m(z_m))), sp)
    set_comment(mc, label)
    if dashed:
        dash_line(doc, mc)
    return mc


def stage_masses(doc, data, stamp, result):
    built = {"masses": {}, "lines": {}, "plates": 0}
    lot = data["lot"]["polygon"]
    built["lines"]["lot"] = make_model_lines(doc, lot, 0.0, "FFM lot boundary | " + stamp)
    env = data["envelope"]["polygon"]
    built["lines"]["envelope"] = make_model_lines(doc, env, 0.0, "FFM setback envelope | " + stamp)
    for mass in data.get("masses", []):
        name = "FFM {0}".format(mass.get("name"))
        label = "{0} | plate {1} m2 x {2} = {3} m2, FSR {4}, {5} m | {6}".format(
            mass.get("label"), mass.get("plate_area_m2"), mass.get("storeys"), mass.get("gfa_m2"),
            mass.get("fsr"), mass.get("height_m"), stamp)
        ds = make_extrusion(doc, mass["footprint"], mass.get("base_z", 0.0), mass["height_m"], name, label)
        built["masses"][mass.get("name")] = ds
        result["built"].append({"kind": "mass", "name": name, "element_id": id_value(ds), "height_m": mass["height_m"],
                                "storeys": mass.get("storeys"), "plate_area_m2": mass.get("plate_area_m2"), "fsr": mass.get("fsr")})
        if mass.get("name") == "proposed":
            f2f = float(mass.get("floor_to_floor_m", 3.0))
            for k in range(1, int(mass.get("storeys", 1))):
                make_extrusion(doc, mass["footprint"], k * f2f, PLATE_THICKNESS_M,
                               "FFM proposed level {0}".format(k + 1), "floor plate | " + stamp)
                built["plates"] += 1
    result["built"].append({"kind": "floor plates", "count": built["plates"]})
    result["built"].append({"kind": "model lines", "lot": len(built["lines"]["lot"]), "envelope": len(built["lines"]["envelope"])})
    return built


# ---------------------------------------------------------------- stage 2: views

def lot_bbox(data, margin_m=6.0):
    W, D = data["lot"]["frontage_m"], data["lot"]["depth_m"]
    H = max([x["height_m"] for x in data["masses"]] + [10.0])
    bb = BoundingBoxXYZ()
    bb.Min = XYZ(m(-margin_m), m(-margin_m), m(-1.0))
    bb.Max = XYZ(m(W + margin_m), m(D + margin_m), m(H + margin_m))
    return bb


def stage_views(doc, data, stamp, result):
    views = {}
    W, D = data["lot"]["frontage_m"], data["lot"]["depth_m"]
    H = max([x["height_m"] for x in data["masses"]] + [10.0])

    # 3D axon from the street side (south-west), section box around the lot
    vft3d = view_family_type(doc, ViewFamily.ThreeDimensional)
    v3 = View3D.CreateIsometric(doc, vft3d.Id)
    safe_name(v3, "FFM massing axon")
    try:
        fwd = XYZ(1, 1, -1).Normalize()
        up = XYZ(1, 1, 2).Normalize()
        eye = XYZ(m(-40), m(-40), m(H + 40))
        v3.SetOrientation(ViewOrientation3D(eye, up, fwd))
    except Exception:
        pass
    v3.IsSectionBoxActive = True
    v3.SetSectionBox(lot_bbox(data))
    v3.Scale = VIEW_SCALE
    show_mass(v3)
    try:
        crop_3d_to_box(v3, lot_bbox(data))  # without an active crop the viewport box spans the whole model
    except Exception:
        result["errors"].append({"stage": "views/axon crop", "traceback": traceback.format_exc()})
    views["axon"] = v3

    # Plan on the lowest level, cropped to the lot
    vftp = view_family_type(doc, ViewFamily.FloorPlan)
    lvl = first_level(doc)
    vp = ViewPlan.Create(doc, vftp.Id, lvl.Id)
    safe_name(vp, "FFM massing plan")
    crop = BoundingBoxXYZ()
    crop.Min = XYZ(m(-8), m(-8), m(-1))
    crop.Max = XYZ(m(W + 8), m(D + 8), m(1))
    vp.CropBoxActive = True
    vp.CropBox = crop
    vp.CropBoxVisible = False
    vp.Scale = VIEW_SCALE
    show_mass(vp)
    annotation_crop(vp)
    views["plan"] = vp

    # Section across the frontage, cut at mid-depth, viewer on the street
    vfts = view_family_type(doc, ViewFamily.Section)
    t = Transform.Identity
    t.Origin = XYZ(m(W / 2.0), m(D / 2.0), 0)
    t.BasisX = XYZ.BasisX
    t.BasisY = XYZ.BasisZ
    t.BasisZ = XYZ(0, -1, 0)      # points toward the viewer
    sb = BoundingBoxXYZ()
    sb.Transform = t
    sb.Min = XYZ(m(-(W / 2.0 + 6)), m(-2), m(-(D / 2.0 + 6)))
    sb.Max = XYZ(m(W / 2.0 + 6 + LABEL_ROOM_M), m(H + 6), m(1.0))   # room on the right for the height labels
    vs = ViewSection.CreateSection(doc, vfts.Id, sb)
    safe_name(vs, "FFM section across frontage")
    vs.Scale = VIEW_SCALE
    show_mass(vs)
    annotation_crop(vs)
    views["section"] = vs

    for k, v in views.items():
        result["built"].append({"kind": "view", "name": v.Name, "element_id": id_value(v)})
    return views


# ---------------------------------------------------------------- stage 3: annotations

TEXT_TYPE_NAME = "FFM 3 mm"
_text_type_cache = {}


def text_type_id(doc):
    """A 3 mm text type of the script's own (duplicated from the document's default) so the sheet
    text is legible in the export; falls back to the default type if duplicating fails."""
    key = doc.Title
    if key in _text_type_cache:
        return _text_type_cache[key]
    base_id = doc.GetDefaultElementTypeId(ElementTypeGroup.TextNoteType)
    tid = base_id
    try:
        for t in FilteredElementCollector(doc).OfClass(TextNoteType):
            if t.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString() == TEXT_TYPE_NAME:
                tid = t.Id
                break
        else:
            t = doc.GetElement(base_id).Duplicate(TEXT_TYPE_NAME)
            t.get_Parameter(BuiltInParameter.TEXT_SIZE).Set(3.0 / 304.8)
            tid = t.Id
    except Exception:
        tid = base_id
    _text_type_cache[key] = tid
    return tid


def paper_width(width_ft):
    """TextNote widths are paper-space feet in every view (a sheet's scale is 1); clamp to the
    limits Revit enforces."""
    w = float(width_ft)
    try:
        lo, hi = TextNote.GetMinimumWidthLimit(), TextNote.GetMaximumWidthLimit()
        w = max(lo, min(hi, w))
    except Exception:
        pass
    return w


def note(doc, view, x_ft, y_ft, z_ft, text, paper_width_ft=None, valign=None):
    """A left-aligned text note at a model (or sheet) point; the width, if given, is paper feet.
    valign (VerticalTextAlignment.Top / Bottom) says which edge of the note sits on the point."""
    tid = text_type_id(doc)
    opts = TextNoteOptions(tid)
    opts.HorizontalAlignment = HorizontalTextAlignment.Left
    if valign is not None:
        opts.VerticalAlignment = valign
    if paper_width_ft:
        return TextNote.Create(doc, view.Id, XYZ(x_ft, y_ft, z_ft), paper_width(paper_width_ft), text, opts)
    return TextNote.Create(doc, view.Id, XYZ(x_ft, y_ft, z_ft), text, opts)


def annotation_crop(view, on=True):
    """Clip annotations to the crop region so a wide label cannot stretch the viewport on the sheet."""
    try:
        p = view.get_Parameter(BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE)
        if p is not None and not p.IsReadOnly:
            p.Set(1 if on else 0)
    except Exception:
        pass


def crop_3d_to_box(view, box):
    """Crop a 3D view to a model-space box. The crop box of a 3D view lives in the view's own
    coordinates, so the box corners are taken through the inverse of that transform."""
    crop = view.CropBox
    inv = crop.Transform.Inverse
    pts = []
    for x in (box.Min.X, box.Max.X):
        for y in (box.Min.Y, box.Max.Y):
            for z in (box.Min.Z, box.Max.Z):
                pts.append(inv.OfPoint(XYZ(x, y, z)))
    xs, ys, zs = [p.X for p in pts], [p.Y for p in pts], [p.Z for p in pts]
    pad = m(3.0)
    new = BoundingBoxXYZ()
    new.Transform = crop.Transform
    new.Min = XYZ(min(xs) - pad, min(ys) - pad, min(zs) - pad)
    new.Max = XYZ(max(xs) + pad, max(ys) + pad, max(zs) + pad)
    view.CropBox = new
    view.CropBoxActive = True
    view.CropBoxVisible = False


def dimension_between_lines(doc, view, line_a, line_b, along_pt, direction):
    """Linear dimension between two model lines, placed on the line through along_pt in `direction`."""
    ra = ReferenceArray()
    ra.Append(line_a.GeometryCurve.Reference)
    ra.Append(line_b.GeometryCurve.Reference)
    dl = Line.CreateBound(along_pt, along_pt + direction)
    return doc.Create.NewDimension(view, dl, ra)


def stage_annotations(doc, data, ledger, views, built, stamp, result):
    W, D = data["lot"]["frontage_m"], data["lot"]["depth_m"]
    sb = data["envelope"]["setbacks_m"]
    plan, sec = views["plan"], views["section"]
    made = {"dimensions": 0, "notes": 0, "lines": 0}

    # Lot and envelope dimensions in the plan. Lot polygon order: front-left, front-right,
    # rear-right, rear-left -> edges 0 front, 1 right side, 2 rear, 3 left side.
    lot, env = built["lines"]["lot"], built["lines"]["envelope"]
    try:
        dimension_between_lines(doc, plan, lot[3], lot[1], XYZ(0, m(-4.0), 0), XYZ.BasisX); made["dimensions"] += 1
        dimension_between_lines(doc, plan, lot[0], lot[2], XYZ(m(W + 4.0), 0, 0), XYZ.BasisY); made["dimensions"] += 1
        dimension_between_lines(doc, plan, lot[3], env[3], XYZ(0, m(D / 2.0), 0), XYZ.BasisX); made["dimensions"] += 1
        dimension_between_lines(doc, plan, env[1], lot[1], XYZ(0, m(D / 2.0), 0), XYZ.BasisX); made["dimensions"] += 1
        dimension_between_lines(doc, plan, lot[0], env[0], XYZ(m(W / 2.0), 0, 0), XYZ.BasisY); made["dimensions"] += 1
        dimension_between_lines(doc, plan, env[2], lot[2], XYZ(m(W / 2.0), 0, 0), XYZ.BasisY); made["dimensions"] += 1
    except Exception:
        result["errors"].append({"stage": "annotations/dimensions", "traceback": traceback.format_exc()})

    # One label in the plan for both masses, inside the proposed footprint (they share the front edge).
    lines = []
    for mass in data["masses"]:
        lines.append("{0}: plate {1:,.0f} m2 x {2} storeys = {3:,.0f} m2".format(
            mass["label"], mass["plate_area_m2"], mass["storeys"], mass["gfa_m2"]))
    if data["masses"]:
        fp = data["masses"][0]["footprint"]
        cx = sum(p[0] for p in fp) / len(fp)
        cy = sum(p[1] for p in fp) / len(fp)
        note(doc, plan, m(cx - 28), m(cy + 4.0), 0, NL.join(lines), 0.38); made["notes"] += 1
    note(doc, plan, m(0), m(-7.0), 0, "STREET (E 19th Ave side)  |  dashed envelope = setbacks front {0} m, rear {1} m, sides {2} m".format(
        sb.get("front"), sb.get("rear"), sb.get("side")), 0.45); made["notes"] += 1

    # Section: benchmark lines and labels. Lines sit 0.2 m behind the cut; labels stand in the room
    # kept clear to the right of the building, benchmarks hanging below their line, mass heights
    # sitting above theirs, so neighbouring labels do not collide.
    yline = D / 2.0 + 0.2
    bench = data.get("policy_benchmark")
    if bench and bench.get("height_m"):
        lo, hi = bench["height_m"]
        for z in (lo, hi):
            make_horizontal_line_in_section(doc, yline, z, -3.0, W + 3.0, "FFM staff benchmark {0} m | {1}".format(z, stamp), dashed=True)
            made["lines"] += 1
        # one label for the pair, hanging below the lower line (the two lines are too close for two)
        note(doc, sec, m(W + 4.0), m(yline), m(lo - 0.15), "staff benchmark {0} to {1} m (dashed)".format(lo, hi), None, VerticalTextAlignment.Top); made["notes"] += 1
    for mass in data["masses"]:
        h_m = mass["height_m"]
        note(doc, sec, m(W + 4.0), m(yline), m(h_m + 0.15), "{0}: {1} m".format(mass["label"], h_m), None, VerticalTextAlignment.Bottom); made["notes"] += 1

    result["built"].append({"kind": "annotations", "dimensions": made["dimensions"], "notes": made["notes"], "section_lines": made["lines"]})
    return made


# ---------------------------------------------------------------- stage 4: sheet

def sheet_text_blocks(data, ledger, stamp):
    """The words that go on the sheet, built from the ledger. Returned as a dict so the memo can quote them."""
    site = ledger["inputs"]["site"]
    opt = ledger["inputs"]["option"]
    ans = ledger["summary"]["answers"]
    res = ledger["results"]

    title = ["FUNDING-FIT MEMO  |  " + site.get("address", site.get("id", "")),
             "Option: " + opt.get("name", opt.get("id", "")),
             "Rules as of {0}  |  stamp {1}  |  engine {2}".format(ledger["run"]["as_of"], ledger["run"]["stamp"]["stamp"], ledger["run"]["engine_version"])]

    allowed = ["1. IS IT ALLOWED?",
               "Outright under {0}: {1}.".format(site.get("zoning_district", "the district"), ans["allowed"]["outright"]["verdict"])]
    for r in res:
        if r.get("check", "").startswith("district_outright") and r["status"] != "not_applicable":
            allowed.append("  - " + r["finding"])
    if ans["allowed"].get("rezoning_path"):
        allowed.append("By rezoning ({0}): {1}.".format(ans["allowed"]["rezoning_path"], ans["allowed"]["by_rezoning"]["verdict"]))
        for r in res:
            if r["layer"] in ("A", "B", "C") and r["status"] in ("fail", "conditional", "uncertain") and not r.get("check", "").startswith("district_outright"):
                allowed.append("  - [{0}] {1}: {2}".format(r["status"].upper(), r["title"], r["finding"]))

    funders = ["2. DOES IT FIT THE FUNDERS?  {0}.".format(ans["funded"]["verdict"].capitalize())]
    targets = opt.get("target_programs") or []
    for r in res:
        if r["layer"] == "E" and (not targets or r["rule_id"] in targets):
            funders.append("  - [{0}] {1}".format(r["status"].upper(), r["finding"]))

    unsure = ["3. STILL UNSURE, AND WHO RESOLVES IT"]
    for u in ans["unsure"][:8]:
        unsure.append("  - [{0}] {1} -> {2}".format(u["status"].upper(), u["title"], u.get("action") or "-"))
    if not ans["unsure"]:
        unsure.append("  Nothing outstanding.")

    massing = ["MASSING, DERIVED FROM THE RULES"]
    for x in data["masses"]:
        massing.append("  - {0}: plate {1:,.0f} m2 x {2} = {3:,.0f} m2 (FSR {4:.2f}), {5} m high; envelope {6} x {7} m".format(
            x["label"], x["plate_area_m2"], x["storeys"], x["gfa_m2"], x["fsr"], x["height_m"],
            data["envelope"]["width_m"], data["envelope"]["depth_m"]))
    b = data.get("policy_benchmark")
    if b and b.get("height_m"):
        massing.append("  - Staff benchmark ({0}): {1} to {2} m, about FSR {3}".format(b["rule_id"], b["height_m"][0], b["height_m"][1], b["fsr"]))
    if data.get("trees"):
        t = data["trees"]
        massing.append("  - Trees: Schedule C requires {0}, plan leaves {1}, shortfall {2}".format(t["required"], t["after"], t["shortfall"]))
    for w in data.get("warnings", []):
        massing.append("  - Note: " + w)

    footer = ["Generated by ffm from the cited rule stack; a feasibility screen, not a survey or advice. Every figure links to its source in the memo.",
              "Placeholders in the inputs are listed in the memo's Inputs section. " + stamp]
    return {"title": title, "allowed": allowed, "funders": funders, "unsure": unsure, "massing": massing, "footer": footer}


def sheet_frame(doc, sheet):
    """The title block's outline on the sheet in sheet feet (x0, y0, x1, y1); A1 landscape if none."""
    try:
        for tb in FilteredElementCollector(doc, sheet.Id).OfCategory(BuiltInCategory.OST_TitleBlocks):
            bb = tb.get_BoundingBox(sheet)
            if bb is not None:
                return bb.Min.X, bb.Min.Y, bb.Max.X, bb.Max.Y
    except Exception:
        pass
    return 0.0, 0.0, 2.76, 1.95


def set_project_info(doc, data, ledger):
    """Fill the title block from the ledger instead of whatever the template last carried."""
    site, opt = ledger["inputs"]["site"], ledger["inputs"]["option"]
    pi = doc.ProjectInformation
    values = (
        (BuiltInParameter.PROJECT_NAME, "Funding-fit memo: " + str(site.get("address", site.get("id", "")))),
        (BuiltInParameter.PROJECT_ADDRESS, str(site.get("address", ""))),
        (BuiltInParameter.PROJECT_NUMBER, "ffm " + str(data.get("stamp"))),
        (BuiltInParameter.CLIENT_NAME, str(opt.get("proponent", ""))),
        (BuiltInParameter.PROJECT_STATUS, "Feasibility screen, rules as of " + str(data.get("as_of"))),
        (BuiltInParameter.PROJECT_BUILDING_NAME, str(opt.get("name", ""))),
        (BuiltInParameter.PROJECT_ISSUE_DATE, str(data.get("as_of"))),
    )
    for bip, val in values:
        try:
            p = pi.get_Parameter(bip)
            if p is not None and not p.IsReadOnly:
                p.Set(val)
        except Exception:
            pass


def _box_size(vpt):
    o = vpt.GetBoxOutline()
    return (o.MaximumPoint.X - o.MinimumPoint.X, o.MaximumPoint.Y - o.MinimumPoint.Y)


def place_views(doc, sheet, views, frame, result):
    """Axon top-left, plan under it, section to their right; the text column takes the right fifth
    of the sheet and the title strip the rest. The views' scale is the largest of a short list at
    which everything fits inside the frame."""
    x0, y0, x1, y1 = frame
    W, H = x1 - x0, y1 - y0
    margin, gap = 0.03 * W, 0.02 * W
    draw_w = 0.62 * W
    vps = {}
    for key in ("axon", "plan", "section"):
        v = views.get(key)
        if v is None:
            continue
        try:
            if Viewport.CanAddViewToSheet(doc, sheet.Id, v.Id):
                vps[key] = Viewport.Create(doc, sheet.Id, v.Id, XYZ(x0 + W / 2.0, y0 + H / 2.0, 0))
                result["built"].append({"kind": "viewport", "view": v.Name, "element_id": id_value(vps[key])})
        except Exception:
            result["errors"].append({"stage": "sheet/viewport " + key, "traceback": traceback.format_exc()})
    sizes, scale = {}, VIEW_SCALE
    for scale in (300, 400, 500, 750, 1000):
        for v in views.values():
            try:
                v.Scale = scale
            except Exception:
                pass
        doc.Regenerate()
        sizes = dict((k, _box_size(vp)) for k, vp in vps.items())
        aw, ah = sizes.get("axon", (0, 0))
        pw, ph = sizes.get("plan", (0, 0))
        sw, sh = sizes.get("section", (0, 0))
        left_w = max(aw, pw)
        if margin + left_w + gap + sw + gap <= draw_w and ah + gap + ph <= H - 2 * margin and sh <= H - 2 * margin:
            break
    aw, ah = sizes.get("axon", (0, 0))
    pw, ph = sizes.get("plan", (0, 0))
    sw, sh = sizes.get("section", (0, 0))
    left_w = max(aw, pw)
    top = y1 - margin
    if "axon" in vps:
        vps["axon"].SetBoxCenter(XYZ(x0 + margin + aw / 2.0, top - ah / 2.0, 0))
    if "plan" in vps:
        vps["plan"].SetBoxCenter(XYZ(x0 + margin + pw / 2.0, top - ah - gap - ph / 2.0, 0))
    if "section" in vps:
        vps["section"].SetBoxCenter(XYZ(x0 + margin + left_w + gap + sw / 2.0, top - sh / 2.0, 0))
    result["built"].append({"kind": "sheet layout", "scale": scale, "frame_ft": [round(W, 2), round(H, 2)],
                            "sizes_ft": dict((k, [round(a, 2), round(b, 2)]) for k, (a, b) in sizes.items())})
    caption_at = (x0 + margin + left_w + gap, top - sh - 0.01 * H, sw) if "section" in vps else None
    return vps, scale, caption_at


def stage_sheet(doc, data, ledger, views, stamp, result):
    tb_id = ElementId.InvalidElementId
    try:
        tbs = list(FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_TitleBlocks).WhereElementIsElementType())
        tbs.sort(key=lambda e: (0 if "A1" in (e.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString() or "") else 1))
        if tbs:
            tb_id = tbs[0].Id
    except Exception:
        pass
    sheet = ViewSheet.Create(doc, tb_id)
    for i in range(0, 50):
        try:
            sheet.SheetNumber = SHEET_NUMBER if i == 0 else "{0}-{1}".format(SHEET_NUMBER, i)
            break
        except Exception:
            continue
    sheet_title = "Funding-fit massing: " + str(data.get("site_id"))
    safe_name(sheet, sheet_title)
    # Office title blocks often read a shared "sheet title" parameter rather than Sheet Name.
    try:
        for p in sheet.Parameters:
            try:
                nm = p.Definition.Name.lower()
                if (("title" in nm or "name" in nm) and p.StorageType.ToString() == "String"
                        and not p.IsReadOnly and p.Definition.Name != "Sheet Name"):
                    p.Set(sheet_title)
            except Exception:
                continue
    except Exception:
        pass
    set_project_info(doc, data, ledger)
    doc.Regenerate()
    frame = sheet_frame(doc, sheet)
    result["built"].append({"kind": "sheet", "number": SHEET_NUMBER, "element_id": id_value(sheet),
                            "title_block": tb_id != ElementId.InvalidElementId, "frame_ft": [round(v, 3) for v in frame]})

    vps, scale, caption_at = place_views(doc, sheet, views, frame, result)

    # Text column: the right fifth of the frame, left of the title strip, stacked by measured height.
    x0, y0, x1, y1 = frame
    W, H = x1 - x0, y1 - y0
    tx, tw = x0 + 0.655 * W, 0.20 * W
    ty = y1 - 0.03 * W
    blocks = sheet_text_blocks(data, ledger, stamp)
    for key in ("title", "allowed", "funders", "unsure", "massing", "footer"):
        text = NL.join(blocks[key])
        try:
            tn = note(doc, sheet, tx, ty, 0, text, tw)
            doc.Regenerate()
            try:
                hgt = tn.Height
            except Exception:
                hgt = 0.012 * sum(max(1, len(s) // 90 + 1) for s in blocks[key])
            ty -= hgt + 0.012 * H
        except Exception:
            result["errors"].append({"stage": "sheet/text " + key, "traceback": traceback.format_exc()})
    if caption_at:
        try:
            cx, cy, cw = caption_at
            note(doc, sheet, cx, cy, 0, NL.join(["FIG 01 axon  |  FIG 02 plan 1:{0}  |  FIG 03 section 1:{0}".format(scale),
                                                 "blue: proposed  |  grey: outright  |  dashed: staff benchmark lines"]), cw)
        except Exception:
            pass
    result["sheet_notes"] = blocks
    return sheet


# ---------------------------------------------------------------- stage 5: export

def stage_export(doc, sheet, folder, result):
    ids = List[ElementId]()
    ids.Add(sheet.Id)
    # PDF (Revit 2022+)
    try:
        from Autodesk.Revit.DB import PDFExportOptions
        po = PDFExportOptions()
        po.FileName = "ffm_sheet"
        po.Combine = True
        if doc.Export(folder, ids, po):
            result["exports"] = result.get("exports", []) + [os.path.join(folder, "ffm_sheet.pdf")]
    except Exception:
        result["errors"].append({"stage": "export/pdf", "traceback": traceback.format_exc()})
    # PNG
    try:
        io = ImageExportOptions()
        io.ExportRange = ExportRange.SetOfViews
        io.SetViewsAndSheets(ids)
        io.FilePath = os.path.join(folder, "ffm_sheet")
        io.ZoomType = ZoomFitType.FitToPage
        io.PixelSize = 4000
        io.HLRandWFViewsFileType = ImageFileType.PNG
        io.ShadowViewsFileType = ImageFileType.PNG
        io.ImageResolution = ImageResolution.DPI_150
        doc.ExportImage(io)
        pngs = [p for p in glob.glob(os.path.join(folder, "ffm_sheet*.png"))]
        if pngs:
            pngs.sort(key=os.path.getmtime)
            target = os.path.join(folder, "ffm_sheet.png")
            if pngs[-1] != target:
                if os.path.exists(target):
                    os.remove(target)
                os.rename(pngs[-1], target)
            result["exports"] = result.get("exports", []) + [target]
    except Exception:
        result["errors"].append({"stage": "export/png", "traceback": traceback.format_exc()})


# ---------------------------------------------------------------- main

def main():
    result = {"ok": False, "mode": None, "stages": {}, "built": [], "errors": []}
    path = pick_massing_file()
    if not path:
        result["errors"].append({"stage": "input", "traceback": "No massing.json found: set FFM_MASSING_JSON or pick the file."})
        print(json.dumps(result, indent=2))
        return result
    folder = os.path.dirname(os.path.abspath(path))
    data = load_json(path)
    ledger_path = os.path.join(folder, "ledger.json")
    ledger = load_json(ledger_path) if os.path.exists(ledger_path) else None
    result["massing_json"] = path
    result["ledger_json"] = ledger_path if ledger else None
    stamp = "ffm stamp {0} | rules as of {1} | {2} / {3}".format(data.get("stamp"), data.get("as_of"), data.get("site_id"), data.get("option_id"))
    result["stamp"] = data.get("stamp")

    uidoc = uiapp.ActiveUIDocument
    created = False
    if uidoc is not None and uidoc.Document is not None:
        doc = uidoc.Document
        result["mode"] = "active document: " + (doc.Title or "untitled")
    else:
        doc, how = new_document()
        created = True
        result["mode"] = "new project (headless), " + how

    st = Stage(doc, result)
    if created:  # tidy only a project this script made, never the user's open model
        st.run("links", lambda: stage_links(doc, result))
    built = st.run("masses", lambda: stage_masses(doc, data, stamp, result))
    views = st.run("views", lambda: stage_views(doc, data, stamp, result)) if built else None
    if built and views:
        st.run("annotations", lambda: stage_annotations(doc, data, ledger, views, built, stamp, result))
    sheet = None
    if views and ledger:
        sheet = st.run("sheet", lambda: stage_sheet(doc, data, ledger, views, stamp, result))
    elif views and not ledger:
        result["errors"].append({"stage": "sheet", "traceback": "ledger.json not found next to massing.json; sheet text skipped."})
    if sheet is not None:
        try:
            doc.Regenerate()
        except Exception:
            pass
        stage_export(doc, sheet, folder, result)

    result["ok"] = bool(built) and result["stages"].get("masses") == "ok"

    save_as = os.environ.get("FFM_SAVE_AS")
    if result["ok"] and (save_as or created):
        if not save_as:
            save_as = os.path.join(folder, "ffm_massing.rvt")
        try:
            so = SaveAsOptions()
            so.OverwriteExistingFile = True
            doc.SaveAs(save_as, so)
            result["saved_as"] = save_as
        except Exception:
            result["errors"].append({"stage": "save", "traceback": traceback.format_exc()})
    if created:
        try:
            doc.Close(False)
        except Exception:
            pass

    if result.get("sheet_notes"):
        try:
            with open(os.path.join(folder, "ffm_sheet_notes.json"), "w") as fh:
                json.dump(result["sheet_notes"], fh, indent=2)
        except Exception:
            pass
    try:
        with open(os.path.join(folder, "ffm_revit_result.json"), "w") as fh:
            json.dump(result, fh, indent=2)
    except Exception:
        result["errors"].append({"stage": "result", "traceback": traceback.format_exc()})
    print(json.dumps({k: v for k, v in result.items() if k != "sheet_notes"}, indent=2))
    return result


main()
