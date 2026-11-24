"""Построение графиков отчёта. Дополнительная зависимость: reportlab."""
from reportlab.graphics import renderSVG
from reportlab.graphics.shapes import Drawing, Line, PolyLine, Rect, String
from reportlab.lib.colors import HexColor, white

from experiments import configurations
from sugeno import HERE, TERMS, membership


COLORS = ["#006b7d", "#bd5415", "#523f9d"]


def panel(drawing, x, y, title, axis, curves):
    width, height = 244, 130
    limit = 100 if axis == "Impact (%)" else 10
    drawing.add(String(x, y + height + 23, title, fontName="Helvetica-Bold", fontSize=13))
    for i in range(5):
        v = i / 4
        yy = y + v * height
        drawing.add(Line(x, yy, x + width, yy, strokeColor=HexColor("#d2d8dd")))
        drawing.add(String(x - 6, yy - 3, f"{v:g}", textAnchor="end", fontSize=9))
    for i in range(6):
        xx = x + width * i / 5
        drawing.add(String(xx, y - 13, f"{limit*i/5:g}", textAnchor="middle", fontSize=9))
    drawing.add(String(x + width / 2, y - 29, axis, textAnchor="middle", fontSize=10))
    for j, (label, spec) in enumerate(curves):
        color = HexColor(COLORS[j])
        points = []
        for k in range(301):
            points.extend((x + k * width / 300, y + height * membership(k * limit / 300, spec)))
        drawing.add(PolyLine(points, strokeColor=color, strokeWidth=2, fillColor=None))
        lx = x + j * 78
        drawing.add(Line(lx, y - 45, lx + 17, y - 45, strokeColor=color, strokeWidth=2))
        drawing.add(String(lx + 21, y - 48, label, fontSize=9))


def main():
    configs = configurations()
    base = configs["base"]["memberships"]
    tuned = configs["tuned"]["memberships"]
    bell = configs["bell"]["memberships"]
    out = HERE.parent / "reports" / "lab3"
    out.mkdir(parents=True, exist_ok=True)
    charts = [
        ("Base membership functions", [
            ("Impact", "Impact (%)", [(t, base["impact"][t]) for t in TERMS]),
            ("Urgency", "Urgency", [(t, base["urgency"][t]) for t in TERMS])]),
        ("Membership function changes", [
            ("Impact.Medium | shape", "Impact (%)", [("Gauss", base["impact"]["Medium"]), ("Bell", bell["impact"]["Medium"])]),
            ("Impact.Low | center", "Impact (%)", [("Base", base["impact"]["Low"]), ("Tuned", tuned["impact"]["Low"])]),
            ("Impact.Medium | width", "Impact (%)", [("Base", base["impact"]["Medium"]), ("Tuned", tuned["impact"]["Medium"])]),
            ("Urgency.High | center", "Urgency", [("Base", base["urgency"]["High"]), ("Tuned", tuned["urgency"]["High"])])]),
    ]
    for filename, (heading, panels) in zip(("base.svg", "changes.svg"), charts):
        height = 60 + 240 * (len(panels) // 2)
        drawing = Drawing(660, height)
        drawing.add(Rect(0, 0, 660, height, fillColor=white, strokeColor=None))
        drawing.add(String(46, height - 30, heading, fontSize=19, fontName="Helvetica-Bold"))
        for i, (title, axis, curves) in enumerate(panels):
            panel(drawing, 50 + 320 * (i % 2), height - 218 - 240 * (i // 2), title, axis, curves)
        renderSVG.drawToFile(drawing, str(out / filename))


if __name__ == "__main__":
    main()
