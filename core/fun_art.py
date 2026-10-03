"""Premium procedural Fun illustrations, no sprites, disk I/O or extra dependencies."""
import math
import time
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor, QPen, QBrush, QPainterPath, QLinearGradient, QRadialGradient


def _pen(color, width=1):
    return QPen(QColor(color), width, Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)


def _gradient(x1,y1,x2,y2,stops):
    g=QLinearGradient(x1,y1,x2,y2)
    for pos,color in stops: g.setColorAt(pos,QColor(color))
    return g


class FunArtwork:
    @staticmethod
    def tile(p):
        p.save()
        p.setBrush(QColor(12,9,34,85));p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(-12,-10,26,26,7,7)
        p.setPen(_pen('#9087E9',1.5))
        p.setBrush(_gradient(-12,-12,12,12,[(0,'#9B8AFF'),(.44,'#5143A5'),(1,'#27204E')]))
        p.drawRoundedRect(-12,-12,24,24,6,6)
        p.setPen(_pen('#DDD6FF',.9));p.setBrush(QColor(224,211,255,95))
        p.drawRoundedRect(-6,-6,12,12,3,3)
        p.setPen(_pen('#F1E9FF',1.15))
        p.drawLine(QPointF(-7,-9),QPointF(4,-9))
        p.restore()
    @staticmethod
    def star(p):
        p.save()
        path=QPainterPath()
        for i in range(10):
            angle=math.radians(-90+i*36); rad=13 if i%2==0 else 5.9
            pt=QPointF(rad*math.cos(angle),13+rad*math.sin(angle))
            if i==0:path.moveTo(pt)
            else:path.lineTo(pt)
        path.closeSubpath()
        p.setPen(_pen('#FFF1C2',1.35))
        p.setBrush(_gradient(0,0,0,26,[(0,'#FFFFFF'),(.3,'#FFE88D'),(.85,'#F5AC36'),(1,'#BD6A20')]))
        p.drawPath(path)
        p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor(255,255,255,170))
        p.drawEllipse(QPointF(-2.4,9),1.55,2.1)
        p.restore()

    @staticmethod
    def comet(p):
        p.save()
        # Tip of the ice-blue comet is the mouse hotspot.
        shape=QPainterPath();shape.moveTo(0,0)
        shape.cubicTo(-4,-8,-15,-10,-24,-12)
        shape.quadTo(-16,-2,-24,8)
        shape.cubicTo(-14,8,-3,5,0,0)
        p.setPen(_pen('#B9FFFF',1.1))
        p.setBrush(_gradient(-16,-10,-7,10,[(0,'#F4FFFF'),(.4,'#59E4F5'),(1,'#686CE9')]))
        p.drawPath(shape)
        p.setPen(_pen('#E7FFFF',1.15));p.drawLine(QPointF(-14,-2),QPointF(-3,0))
        p.restore()

    @staticmethod
    def orbit(p, count=4, clock=None):
        p.save()
        phase=(time.perf_counter() if clock is None else clock)*2.6
        p.setPen(_pen('#6583B8',.85)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(0,0),22,15)
        for i in range(count):
            a=phase+i*2*math.pi/count
            x,y=22*math.cos(a),15*math.sin(a)
            radius=2.9 if i==0 else 2.1
            p.setPen(_pen('#CAEDFF',.9))
            p.setBrush(QColor('#A7F5FF') if i==0 else QColor('#8188FF'))
            p.drawEllipse(QPointF(x,y),radius,radius)
        p.setPen(_pen('#E8FFFF',1.4));p.setBrush(QColor('#1A658C'))
        p.drawEllipse(QPointF(0,0),4.3,4.3)
        p.setPen(Qt.PenStyle.NoPen);p.setBrush(Qt.GlobalColor.white)
        p.drawEllipse(QPointF(-1,-1),1,1)
        p.restore()
    @staticmethod
    def chain(p, points, ox, oy):
        """Batch chain paths: constant draw calls instead of five per link."""
        if len(points)<2:return
        p.save()
        shadow=QPainterPath(); even=QPainterPath(); odd=QPainterPath()
        light=QPainterPath(); joints_a=QPainterPath();joints_b=QPainterPath()
        centres=QPainterPath()
        for i in range(len(points)-1):
            x1,y1=points[i][0]-ox,points[i][1]-oy
            x2,y2=points[i+1][0]-ox,points[i+1][1]-oy
            shadow.moveTo(x1+1,y1+1);shadow.lineTo(x2+1,y2+1)
            segment=odd if i%2 else even
            segment.moveTo(x1,y1);segment.lineTo(x2,y2)
            light.moveTo(x1-.7,y1-.7);light.lineTo(x2-.7,y2-.7)
            (joints_b if i%2 else joints_a).addEllipse(QPointF(x1,y1),2.4,2.4)
            centres.addEllipse(QPointF(x1,y1),.85,.85)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(_pen('#131D32',4));p.drawPath(shadow)
        p.setPen(_pen('#798BAE',2.9));p.drawPath(even)
        p.setPen(_pen('#B7C8E4',2.9));p.drawPath(odd)
        p.setPen(_pen('#ECF4FF',.85));p.drawPath(light)
        p.setPen(_pen('#344E75',.9));p.setBrush(QColor('#C7D6EB'))
        p.drawPath(joints_a)
        p.setBrush(QColor('#E4EDFF'));p.drawPath(joints_b)
        p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor('#344E75'))
        p.drawPath(centres)
        end=points[-1]; x,y=end[0]-ox,end[1]-oy
        p.setPen(_pen('#D4DBF4',1.3))
        p.setBrush(_gradient(x-7,y-7,x+7,y+9,
                            [(0,'#B4BDE7'),(.5,'#645C97'),(1,'#353453')]))
        p.drawEllipse(QPointF(x,y),6.9,6.9)
        p.setBrush(QColor('#EDEEFF'));p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(x-2,y-2),1.6,1.6)
        p.restore()

    @staticmethod
    def particle(p, mode, particle, ox, oy):
        px,py,age,lifetime,radius=particle[:5]
        fade=max(0.0,1-age/lifetime)
        if fade==0:return
        p.save();p.setOpacity(fade)
        col='#89E9FF' if mode=='comet' else '#FFE49C'
        p.setPen(_pen(col,1));p.setBrush(QColor(col))
        x,y=px-ox,py-oy
        p.drawEllipse(QPointF(x,y),radius,radius)
        p.setPen(_pen('#FFFFFF',.65));p.drawLine(QPointF(x-radius*1.6,y),QPointF(x+radius*1.6,y))
        p.drawLine(QPointF(x,y-radius*1.6),QPointF(x,y+radius*1.6))
        p.restore()

    @staticmethod
    def yoyo(p, anchor, ball, ox, oy):
        """A tethered glass ball whose click-triggered motion is simulated."""
        ax,ay=anchor[0]-ox,anchor[1]-oy
        bx,by=ball[0]-ox,ball[1]-oy
        p.save()
        p.setPen(_pen('#222841',3.5))
        p.drawLine(QPointF(ax+1,ay+1),QPointF(bx+1,by+1))
        p.setPen(_pen('#FFCFBA',1.6))
        p.drawLine(QPointF(ax,ay),QPointF(bx,by))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#F3CEAD'))
        p.drawEllipse(QPointF(ax,ay),2.8,2.8)
        glow=QRadialGradient(bx-3,by-4,15)
        glow.setColorAt(0,QColor('#FFF7E5'))
        glow.setColorAt(.35,QColor('#FFAF8D'))
        glow.setColorAt(1,QColor('#AE4469'))
        p.setBrush(glow)
        p.setPen(_pen('#663C5E',1.6))
        p.drawEllipse(QPointF(bx,by),12,12)
        # A yo-yo has two rims and an axle, rather than a plain glass ball.
        p.setBrush(QColor('#D46991'))
        p.setPen(_pen('#FFE4D4',1.0))
        p.drawEllipse(QPointF(bx,by),8.1,8.1)
        p.setBrush(QColor('#763B70'))
        p.setPen(_pen('#FFDDD7',1.1))
        p.drawEllipse(QPointF(bx,by),4.1,4.1)
        p.setBrush(QColor('#FFF2DF'))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(bx-.9,by-.9),1.5,1.5)
        p.setPen(_pen('#FFE0D0',1.2))
        p.drawArc(int(bx-8),int(by-8),16,16,40*16,115*16)
        p.restore()

    @staticmethod
    def ribbon(p, points, ox, oy):
        """A tapered, twisting silk strip (not a chain of particles)."""
        if len(points)<3:return
        p.save()
        left=[];right=[]
        for i,point in enumerate(points):
            before=points[max(0,i-1)]
            after=points[min(len(points)-1,i+1)]
            dx,dy=after[0]-before[0],after[1]-before[1]
            norm=math.hypot(dx,dy)
            if norm<.0001:dx,dy,norm=1,0,1
            width=7*(1-i/(len(points)-1))+.25
            nx,ny=-dy/norm*width,dx/norm*width
            left.append(QPointF(point[0]-ox+nx,point[1]-oy+ny))
            right.append(QPointF(point[0]-ox-nx,point[1]-oy-ny))
        # Midpoint quadratic splines hide the jagged polygon joints.
        shape=QPainterPath();shape.moveTo(left[0])
        for a,b in zip(left,left[1:]):
            shape.quadTo(a,QPointF((a.x()+b.x())*.5,(a.y()+b.y())*.5))
        shape.lineTo(left[-1])
        reverse=list(reversed(right))
        shape.lineTo(reverse[0])
        for a,b in zip(reverse,reverse[1:]):
            shape.quadTo(a,QPointF((a.x()+b.x())*.5,(a.y()+b.y())*.5))
        shape.lineTo(reverse[-1])
        shape.closeSubpath()
        gradient=QLinearGradient(left[0],right[-1])
        gradient.setColorAt(0,QColor('#79D8FF'))
        gradient.setColorAt(.45,QColor('#DDB0FF'))
        gradient.setColorAt(1,QColor('#FA91C6'))
        p.setBrush(gradient);p.setPen(_pen('#D4C8FF',.65))
        p.drawPath(shape)
        p.setPen(_pen('#F7E7FF',.85))
        for first,second in zip(left,left[1:]):p.drawLine(first,second)
        # Visible silk knot even when the pointer has been motionless.
        head=QPointF(points[0][0]-ox,points[0][1]-oy)
        p.setPen(_pen('#EAE2FF',1.15))
        p.setBrush(QColor('#BA83ED'))
        p.drawEllipse(head,4.6,4.6)
        p.restore()

    @staticmethod
    def spinner(p, angle):
        """Three-lobed, vector fidget spinner; the center stays fixed to the pointer."""
        p.save()
        p.rotate(angle)
        p.setPen(_pen('#102B3D',5.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        for direction in (0, 120, 240):
            p.save()
            p.rotate(direction)
            p.drawLine(QPointF(0, 0), QPointF(0, -20))
            p.setPen(_pen('#D9FAFF',1.5))
            p.setBrush(_gradient(-8,-29,8,-13,
                       [(0,'#FFFFFF'),(.35,'#63DDF1'),(1,'#3458A8')]))
            p.drawEllipse(QPointF(0,-20),8.4,8.4)
            p.setPen(_pen('#2C4B76',1.0))
            p.setBrush(QColor('#153044'))
            p.drawEllipse(QPointF(0,-20),4.2,4.2)
            p.setBrush(QColor('#E9FCFF'))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(-1.2,-22.2),1.35,1.35)
            p.restore()
        # Hub and bearing are drawn last so the arms remain underneath.
        p.setPen(_pen('#A4E8F8',1.4))
        p.setBrush(_gradient(-8,-8,8,8,
                   [(0,'#EFFDFF'),(.45,'#74CBE3'),(1,'#31517F')]))
        p.drawEllipse(QPointF(0,0),8.8,8.8)
        p.setPen(_pen('#25405C',1.25))
        p.setBrush(QColor('#162A47'))
        p.drawEllipse(QPointF(0,0),4.7,4.7)
        p.setBrush(QColor('#F7FFFF'))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(-1.4,-1.7),1.5,1.5)
        p.restore()
