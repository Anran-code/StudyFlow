# Reused and adapted from 雍致鸣_SRS交付/support/build_models.py at 97deeb6.
# Shared drawing style; AI activity content is defined separately in build_models.py.
"""Generate editable draw.io diagrams and matching SVG/PNG exports.

Requires Python and Pillow. No remote renderer or image generation is used.
"""
from pathlib import Path
from dataclasses import dataclass
import html
import math
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONT = Path('C:/Windows/Fonts/msyh.ttc')
BOLD = Path('C:/Windows/Fonts/msyhbd.ttc')
NAVY, INK, BLUE, TEAL = '#17324d', '#243b53', '#eaf2fb', '#e7f5f1'
AMBER, STROKE, GRAY = '#fff4dd', '#45617b', '#60758a'


@dataclass
class Node:
    id: str
    shape: str
    text: str
    x: int
    y: int
    w: int
    h: int
    fill: str = BLUE
    size: int = 21


class Diagram:
    def __init__(self, name, title, subtitle, w, h):
        self.name, self.w, self.h = name, w, h
        self.nodes, self.edges = [], []
        self.node('title', 'text', title, 40, 27, w - 80, 48, '#ffffff', 32)
        self.node('subtitle', 'text', subtitle, 40, 84, w - 80, 35, '#ffffff', 18)

    def node(self, id, shape, text, x, y, w, h, fill=BLUE, size=21):
        self.nodes.append(Node(id, shape, text, x, y, w, h, fill, size))
        return id

    def edge(self, points, label='', arrow=True, hollow=False, label_at=None):
        self.edges.append((points, label, arrow, hollow, label_at))

    def lanes(self, labels, bottom):
        for i, label in enumerate(labels):
            x = 40 + i * 330
            self.node(f'lane{i}', 'panel', '', x, 145, 330, bottom - 145,
                      '#f7fafc' if i % 2 == 0 else '#ffffff')
            self.node(f'lh{i}', 'header', label, x, 145, 330, 52, NAVY, 23)

    def render(self, *, save_png=True):
        svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">',
               '<rect width="100%" height="100%" fill="white"/>',
               '<g font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif">']
        im = Image.new('RGB', (self.w, self.h), 'white')
        draw = ImageDraw.Draw(im)

        def line(points, color=STROKE, width=2):
            draw.line(points, fill=color, width=width)
            svg.append('<polyline points="' + ' '.join(f'{x},{y}' for x, y in points) + f'" fill="none" stroke="{color}" stroke-width="{width}"/>')

        def text(t, x, y, w, h, size, color=INK, bold=False, centered=True):
            font = ImageFont.truetype(str(BOLD if bold else FONT), size)
            rows = t.split('\n')
            lh = int(size * 1.5)
            yy = y + (h - len(rows) * lh) / 2
            for row in rows:
                box = draw.textbbox((0, 0), row, font=font)
                tw = draw.textlength(row, font=font)
                if tw > w - 8:
                    raise ValueError(f'Text exceeds box width: {row!r} ({tw} > {w})')
                xx = x + (w - tw) / 2 if centered else x
                draw.text((xx, yy - box[1] + (lh - (box[3] - box[1])) / 2), row, font=font, fill=color)
                sx = x + w / 2 if centered else x
                svg.append(f'<text x="{sx}" y="{yy + lh/2}" text-anchor="{"middle" if centered else "start"}" dominant-baseline="central" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}">{html.escape(row)}</text>')
                yy += lh

        def shape(n):
            x, y, w, h = n.x, n.y, n.w, n.h
            fill = n.fill
            if n.shape == 'text':
                text(n.text, x, y, w, h, n.size, NAVY if n.id == 'title' else GRAY,
                     n.id == 'title', False)
                return
            if n.shape == 'actor':
                cx = x + w/2
                draw.ellipse((cx-13, y, cx+13, y+26), outline=STROKE, width=3)
                svg.append(f'<circle cx="{cx}" cy="{y+13}" r="13" fill="white" stroke="{STROKE}" stroke-width="3"/>')
                for points in [[(cx, y+26), (cx, y+63)], [(x+6, y+38), (x+w-6, y+38)],
                               [(cx, y+63), (x+8, y+h)], [(cx, y+63), (x+w-8, y+h)]]:
                    line(points, width=3)
                text(n.text, x-80, y+h+9, w+160, 70, n.size)
                return
            if n.shape in ('start', 'end', 'connector'):
                draw.ellipse((x,y,x+w,y+h), fill=NAVY if n.shape != 'connector' else TEAL, outline=STROKE, width=2)
                svg.append(f'<ellipse cx="{x+w/2}" cy="{y+h/2}" rx="{w/2}" ry="{h/2}" fill="{NAVY if n.shape != "connector" else TEAL}" stroke="{STROKE}" stroke-width="2"/>')
                if n.shape == 'end':
                    draw.ellipse((x+5,y+5,x+w-5,y+h-5), outline='white', width=2)
                    svg.append(f'<ellipse cx="{x+w/2}" cy="{y+h/2}" rx="{w/2-5}" ry="{h/2-5}" fill="none" stroke="white" stroke-width="2"/>')
                if n.shape == 'connector': text(n.text,x,y,w,h,n.size)
                return
            if n.shape == 'diamond':
                pts = [(x+w/2,y),(x+w,y+h/2),(x+w/2,y+h),(x,y+h/2)]
                draw.polygon(pts, fill=fill)
                draw.line(pts + [pts[0]], fill=STROKE, width=2)
                svg.append('<polygon points="'+' '.join(f'{a},{b}' for a,b in pts)+f'" fill="{fill}" stroke="{STROKE}" stroke-width="2"/>')
            elif n.shape == 'ellipse':
                draw.ellipse((x,y,x+w,y+h), fill=fill, outline=STROKE, width=2)
                svg.append(f'<ellipse cx="{x+w/2}" cy="{y+h/2}" rx="{w/2}" ry="{h/2}" fill="{fill}" stroke="{STROKE}" stroke-width="2"/>')
            else:
                radius = 12 if n.shape in ('box','note') else 0
                draw.rounded_rectangle((x,y,x+w,y+h), radius=radius, fill=fill, outline=STROKE, width=1 if n.shape in ('panel','header') else 2)
                svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{STROKE}" stroke-width="{1 if n.shape in ("panel","header") else 2}"/>')
            if n.text:
                text(n.text,x,y,w,h,n.size, 'white' if n.shape == 'header' else INK, n.shape == 'header')

        backgrounds = [n for n in self.nodes if n.shape in ('panel','header')]
        foregrounds = [n for n in self.nodes if n.shape not in ('panel','header')]
        for n in backgrounds: shape(n)
        for points, label, arrow, hollow, label_at in self.edges:
            line(points)
            if arrow:
                (x0,y0),(x1,y1) = points[-2:]
                ang = math.atan2(y1-y0,x1-x0)
                a = (x1-14*math.cos(ang)+6*math.sin(ang), y1-14*math.sin(ang)-6*math.cos(ang))
                b = (x1-14*math.cos(ang)-6*math.sin(ang), y1-14*math.sin(ang)+6*math.cos(ang))
                pts = [(x1,y1),a,b]
                draw.polygon(pts,fill='white' if hollow else STROKE)
                draw.line(pts+[pts[0]],fill=STROKE,width=2)
                svg.append('<polygon points="'+' '.join(f'{a},{b}' for a,b in pts)+f'" fill="{"white" if hollow else STROKE}" stroke="{STROKE}" stroke-width="2"/>')
            if label:
                lx,ly = label_at or points[len(points)//2]
                font = ImageFont.truetype(str(FONT),18)
                lw = draw.textlength(label,font=font)+12
                draw.rectangle((lx-lw/2,ly-15,lx+lw/2,ly+15),fill='white')
                svg.append(f'<rect x="{lx-lw/2}" y="{ly-15}" width="{lw}" height="30" fill="white"/>')
                text(label,lx-lw/2,ly-15,lw,30,18)
        for n in foregrounds: shape(n)
        svg.append('</g></svg>')
        assets = ROOT / 'assets'
        assets.mkdir(exist_ok=True)
        if save_png:
            im.save(assets / f'{self.name}.png')
        (assets / f'{self.name}.svg').write_text('\n'.join(svg),encoding='utf-8')
        return im

    def drawio(self, root):
        diagram = ET.SubElement(root,'diagram',{'id':self.name,'name':self.name})
        model = ET.SubElement(diagram,'mxGraphModel',{'dx':'1400','dy':'1000','grid':'1','gridSize':'10','page':'1','pageScale':'1','pageWidth':str(self.w),'pageHeight':str(self.h),'math':'0','shadow':'0'})
        cells = ET.SubElement(model,'root')
        ET.SubElement(cells,'mxCell',{'id':'0'})
        ET.SubElement(cells,'mxCell',{'id':'1','parent':'0'})
        ordered = [n for n in self.nodes if n.shape in ('panel','header')]
        ordered += [n for n in self.nodes if n.shape not in ('panel','header')]
        for n in ordered:
            shape = {'actor':'shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;',
                     'ellipse':'ellipse;', 'diamond':'rhombus;', 'text':'text;strokeColor=none;fillColor=none;align=left;',
                     'start':'ellipse;fillColor=#17324d;', 'end':'ellipse;double=1;fillColor=#17324d;',
                     'connector':'ellipse;', 'panel':'rounded=0;', 'header':'rounded=0;fontColor=#ffffff;fontStyle=1;'}.get(n.shape,'rounded=1;arcSize=14;')
            style = f'whiteSpace=wrap;html=1;fontFamily=Microsoft YaHei;fontSize={n.size};fontColor={INK};strokeColor={STROKE};fillColor={n.fill};'
            style += shape
            if n.id == 'title': style += 'fontStyle=1;fontColor=#17324d;'
            cell = ET.SubElement(cells,'mxCell',{'id':n.id,'value':html.escape(n.text).replace('\n','<br>'),'style':style,'vertex':'1','parent':'1'})
            ET.SubElement(cell,'mxGeometry',{'x':str(n.x),'y':str(n.y),'width':str(n.w),'height':str(n.h),'as':'geometry'})
        for i,(points,label,arrow,hollow,label_at) in enumerate(self.edges):
            end = 'block' if hollow else ('classic' if arrow else 'none')
            style = f'edgeStyle=none;rounded=0;html=1;fontFamily=Microsoft YaHei;fontSize=18;strokeColor={STROKE};endArrow={end};endFill={0 if hollow else 1};labelBackgroundColor=#ffffff;'
            cell=ET.SubElement(cells,'mxCell',{'id':f'e{i}','value':html.escape(label),'style':style,'edge':'1','parent':'1'})
            geo=ET.SubElement(cell,'mxGeometry',{'relative':'1','as':'geometry'})
            for (x,y),kind in [(points[0],'sourcePoint'),(points[-1],'targetPoint')]:
                ET.SubElement(geo,'mxPoint',{'x':str(x),'y':str(y),'as':kind})
            arr=ET.SubElement(geo,'Array',{'as':'points'})
            for x,y in points[1:-1]: ET.SubElement(arr,'mxPoint',{'x':str(x),'y':str(y)})
            if label_at:
                # draw.io locates a relative x=0 label halfway along path length.
                lengths=[math.dist(a,b) for a,b in zip(points,points[1:])]
                remaining=sum(lengths)/2
                mid=points[-1]
                for a,b,length in zip(points,points[1:],lengths):
                    if remaining <= length and length:
                        ratio=remaining/length
                        mid=(a[0]+ratio*(b[0]-a[0]), a[1]+ratio*(b[1]-a[1]))
                        break
                    remaining-=length
                ET.SubElement(geo,'mxPoint',{'x':str(label_at[0]-mid[0]),'y':str(label_at[1]-mid[1]),'as':'offset'})
