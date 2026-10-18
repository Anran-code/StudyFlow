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

    def render(self):
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
        im.save(assets / f'{self.name}.png')
        (assets / f'{self.name}.svg').write_text('\n'.join(svg),encoding='utf-8')

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


def usecases():
    a=Diagram('图A_学生用例','StudyFlow｜系统用例图 A','共同操作；连线表示参与关系；空心三角表示管理者继承学生角色',1480,1160)
    a.node('boundary','panel','',350,160,880,850,'#f8fbfe')
    a.node('system','text','StudyFlow 系统边界 · 学生共同操作',390,174,800,45,'white',23)
    a.node('student','actor','学生\n（当前空间成员）',140,420,62,84)
    a.node('manager','actor','作业管理者\n（负责人 / 个人所有者）',140,790,62,84)
    a.node('provider','actor','外部模型服务\n（支撑系统）',1290,470,62,84)
    cases=[('UC-01','管理账号、空间与小组成员'),('UC-05','维护个人可用时段'),('UC-07','查询任务并请求规划建议'),
           ('UC-10','更新任务、评论、提交成果及验收'),('UC-11','查看计划版本与站内提醒'),('UC-12','检查要求覆盖与交付完整性')]
    for i,(id,t) in enumerate(cases):
        y=240+i*118
        a.node(id,'ellipse',id+'\n'+t,540,y,530,82)
        a.edge([(202,462),(540,y+41)],arrow=False)
    a.edge([(140,832),(74,832),(74,462),(140,462)],'泛化',True,True,(75,660))
    a.edge([(1290,512),(1070,517)],arrow=False)
    a.node('note','note','学生关联不等于获得全部子操作权限：只可维护本人时段及允许的任务字段。\n作业管理者继承共同操作；管理成员、验收及确认权限仍按当前空间判断。',80,1040,1320,88,AMBER,20)

    b=Diagram('图B_管理用例','StudyFlow｜系统用例图 B','管理者额外操作；与图 A 共用角色定义和系统边界',1480,1160)
    b.node('boundary','panel','',350,160,880,850,'#f8fbfe')
    b.node('system','text','StudyFlow 系统边界 · 规划与确认',390,174,800,45,'white',23)
    b.node('manager','actor','作业管理者\n（负责人 / 个人所有者）',140,490,62,84)
    b.node('provider','actor','外部模型服务\n（支撑系统）',1290,560,62,84)
    cases=[('UC-02','管理课程、作业与原始说明'),('UC-03','抽取、修改与确认作业要求'),('UC-04','拆解任务、分配负责人及设置依赖'),
           ('UC-06','生成排程草案并解释冲突'),('UC-08','确认计划并生成正式版本'),('UC-09','时间或工时变化后提出计划调整')]
    for i,(id,t) in enumerate(cases):
        y=240+i*118
        b.node(id,'ellipse',id+'\n'+t,540,y,530,82,TEAL if id=='UC-08' else BLUE)
        b.edge([(202,532),(540,y+41)],arrow=False)
        if id in ['UC-03','UC-06','UC-09']:
            b.edge([(1290,602),(1070,y+41)],arrow=False)
    b.node('note','note','外部模型仅辅助理解与解释；确定性业务服务校验约束并执行排程。\n模型未连接 UC-08：正式计划必须由有权用户确认，代理不能直接使其生效。',80,1040,1320,88,AMBER,20)
    return [a,b]


def planning():
    d=Diagram('图C_主流程_规划','StudyFlow｜主业务活动图 C：规划','P 接执行阶段；R 接重新读取输入并排程；失败路径均不创建正式占用',1480,2320)
    d.lanes(['作业管理者','小组成员 / 本人','系统业务服务','内部 AI / 排程'],2220)
    def box(id,t,lane,y,fill=BLUE,h=66): d.node(id,'box',t,60+lane*330,y,290,h,fill)
    def diamond(id,t,lane,y): d.node(id,'diamond',t,130+lane*330,y,150,92,AMBER,19)
    d.node('start','start','',188,212,34,34)
    box('input','录入作业与原始说明\nUC-02',0,275)
    box('source','保存原文和版本\n标记缺失字段',2,275)
    box('extract','抽取候选要求\n失败时允许手工补全',3,385)
    box('review','核对出处、修订与补全\nUC-03',0,495)
    diamond('reqok','要求已核实？',0,605)
    box('reqconfirm','人工确认要求',0,750,TEAL)
    box('tasks','拆解、分工、设置依赖\nUC-04',0,855)
    box('validate','校验字段、权限、版本\n以及依赖无环',2,855)
    diamond('taskok','任务有效？',2,965)
    box('fix','修正任务或依赖',0,965,AMBER)
    box('avail','维护本人可用时段\nUC-05',1,1100)
    d.node('rin','connector','R',1168,1075,54,54,TEAL,23)
    box('schedule','重新读取输入并排程\nUC-06 / UC-09',3,1190)
    diamond('possible','找到合法\n草案？',3,1300)
    box('adjust','查看冲突并调整\n分工、工时或时间窗口',0,1300,AMBER)
    box('draft','保存带依据版本的草案\n展示影响与差异',2,1440)
    box('preview','预览安排及变更差异\nUC-08',0,1550)
    diamond('apply','选择应用？',0,1660)
    box('park','保留草案，暂不生效',0,1810,AMBER)
    d.node('parkend','end','',188,1920,34,34)
    box('recheck','再检查权限、输入版本\n及所有时间约束',2,1660)
    diamond('fresh','检查通过？',2,1800)
    box('reject','拒绝确认并说明原因\n原计划保留，返回重算',2,1940,AMBER)
    d.node('rout','connector','R',1168,1946,54,54,TEAL,23)
    box('commit','整体生效：版本与时间块\n记录确认人并建立通知',2,2090,TEAL)
    d.node('p','connector','P',838,2180,54,54,TEAL,23)
    d.edge([(205,246),(205,275)])
    d.edge([(350,308),(720,308)])
    d.edge([(865,341),(865,365),(1195,365),(1195,385)])
    d.edge([(1195,451),(1195,475),(205,475),(205,495)])
    d.edge([(205,561),(205,605)])
    d.edge([(130,651),(25,651),(25,528),(60,528)],'否',label_at=(70,651))
    d.edge([(205,697),(205,750)],'是',label_at=(225,721))
    d.edge([(205,816),(205,855)])
    d.edge([(350,888),(720,888)])
    d.edge([(865,921),(865,965)])
    d.edge([(790,1011),(350,1011)],'否',label_at=(540,1011))
    d.edge([(205,965),(205,921)])
    d.edge([(865,1057),(865,1080),(535,1080),(535,1100)],'是',label_at=(700,1080))
    d.edge([(535,1166),(535,1180),(1195,1180),(1195,1190)])
    d.edge([(1195,1129),(1195,1190)])
    d.edge([(1195,1256),(1195,1300)])
    d.edge([(1120,1346),(350,1346)],'否：未找到 / 冲突 / 失败',label_at=(740,1346))
    d.edge([(205,1300),(205,1175),(1010,1175),(1010,1223),(1050,1223)])
    d.edge([(1195,1392),(1195,1425),(865,1425),(865,1440)],'是',label_at=(1050,1425))
    d.edge([(865,1506),(865,1525),(205,1525),(205,1550)])
    d.edge([(205,1616),(205,1660)])
    d.edge([(205,1752),(205,1810)],'否',label_at=(227,1778))
    d.edge([(205,1876),(205,1920)])
    d.edge([(280,1706),(720,1706)],'是',label_at=(500,1706))
    d.edge([(865,1726),(865,1800)])
    d.edge([(940,1846),(1010,1846),(1010,1915),(865,1915),(865,1940)],'否',label_at=(1010,1885))
    d.edge([(1010,1973),(1168,1973)])
    d.edge([(865,1892),(690,1892),(690,2123),(720,2123)],'是',label_at=(690,2005))
    d.edge([(865,2156),(865,2180)])
    d.node('footer','text','草案不占用正式时间。确认检查与占用整体完成；通知失败可重试，不撤销已经生效的计划。',40,2250,1400,38,'white',19)
    return d


def execution():
    d=Diagram('图D_主流程_执行','StudyFlow｜主业务活动图 D：执行与交付','与图 C 连接；阻塞与待重排分别记录，不替代任务执行状态',1480,2220)
    d.lanes(['作业管理者','小组成员 / 本人','系统业务服务','变更处理（系统）'],2130)
    def box(id,t,lane,y,fill=BLUE,h=66): d.node(id,'box',t,60+lane*330,y,290,h,fill)
    def diamond(id,t,lane,y): d.node(id,'diamond',t,130+lane*330,y,150,92,AMBER,19)
    d.node('p','connector','P',838,220,54,54,TEAL,23)
    box('view','查看本人待执行任务\nUC-10',1,310)
    box('check','检查前置任务实际完成\n情况和阻塞原因',2,420)
    diamond('ready','允许开始？',2,530)
    box('blocked','显示阻塞，记录原因',1,530,AMBER)
    box('wait','等待前置完成 / 解除阻塞',1,650,AMBER)
    box('starttask','开始任务：进行中',1,780)
    box('submit','提交成果链接\n进入待验收',1,890)
    box('review','验收成果\n个人场景由本人检查',0,1000)
    diamond('accept','验收通过？',0,1110)
    box('fix','退回进行中，修改成果',1,1110,AMBER)
    box('done','记录已完成及操作人\n解除已满足的依赖阻塞',2,1250,TEAL)
    diamond('remaining','还有未完成\n任务？',2,1370)
    box('coverage','核对要求—任务—证据\nUC-12',0,1510)
    diamond('covered','要求均有\n有效证据？',0,1620)
    box('evidence','定位缺项，补充证据\n必要时新增 / 重开任务',1,1620,AMBER)
    diamond('rework','需新增 /\n重开任务？',1,1750)
    d.node('rwork','connector','R',838,1769,54,54,TEAL,23)
    box('external','学生在学校指定渠道\n完成实际提交',0,1970,TEAL)
    d.node('end','end','',188,2070,34,34)
    d.node('event','start','',1178,220,34,34)
    box('changed','执行期间时间、工时\n或截止日期变化',3,310)
    box('impact','标记受影响安排待重排\n保留旧版本，不静默移动',3,450,AMBER)
    d.node('r','connector','R',1168,585,54,54,TEAL,23)
    d.node('note','note','R 返回图 C 重新规划。\n\n新增 / 重开任务先按\nUC-04处理，再进入排程。\n\n其他未受影响任务可继续。\n旧草案不能直接应用。',1050,730,290,240,AMBER,20)
    d.edge([(865,274),(865,290),(535,290),(535,310)])
    d.edge([(535,376),(535,395),(865,395),(865,420)])
    d.edge([(865,486),(865,530)])
    d.edge([(790,576),(680,576)],'否',label_at=(732,576))
    d.edge([(535,596),(535,650)])
    d.edge([(680,683),(698,683),(698,453),(720,453)])
    d.edge([(865,622),(865,755),(535,755),(535,780)],'是',label_at=(865,704))
    d.edge([(535,846),(535,890)])
    d.edge([(535,956),(535,980),(205,980),(205,1000)])
    d.edge([(205,1066),(205,1110)])
    d.edge([(280,1156),(390,1156)],'否',label_at=(335,1156))
    d.edge([(680,1143),(695,1143),(695,923),(680,923)])
    d.edge([(205,1202),(205,1230),(865,1230),(865,1250)],'是',label_at=(550,1230))
    d.edge([(865,1316),(865,1370)])
    d.edge([(940,1416),(1415,1416),(1415,290),(535,290)],'是：继续任务',label_at=(1415,1280))
    d.edge([(865,1462),(865,1485),(205,1485),(205,1510)],'否',label_at=(565,1485))
    d.edge([(205,1576),(205,1620)])
    d.edge([(280,1666),(390,1666)],'否',label_at=(336,1666))
    d.edge([(535,1686),(535,1750)])
    d.edge([(610,1796),(838,1796)],'是',label_at=(730,1796))
    d.edge([(535,1842),(535,1880),(25,1880),(25,1543),(60,1543)],'否：仅补证据',label_at=(280,1880))
    d.edge([(205,1712),(205,1970)],'是',label_at=(225,1930))
    d.edge([(205,2036),(205,2070)])
    d.edge([(1195,254),(1195,310)])
    d.edge([(1195,376),(1195,450)])
    d.edge([(1195,516),(1195,585)])
    d.node('footer','text','“已覆盖”只表示存在交付证据，不等于内容质量达标或学校平台已经收到提交。',40,2160,1400,38,'white',19)
    return d


def main():
    diagrams = usecases()+[planning(),execution()]
    root=ET.Element('mxfile',{'host':'app.diagrams.net','version':'24.7.17','type':'device'})
    for d in diagrams:
        d.render()
        d.drawio(root)
    ET.indent(root,space='  ')
    (ROOT/'models').mkdir(exist_ok=True)
    ET.ElementTree(root).write(ROOT/'models'/'StudyFlow_用例与主业务流程.drawio',encoding='utf-8',xml_declaration=True)
    print('Generated',len(diagrams),'editable pages, SVGs and PNGs.')


if __name__ == '__main__':
    main()
