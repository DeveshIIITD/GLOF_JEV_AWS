from PIL import Image,ImageDraw
from pathlib import Path
import math
out=Path(__file__).resolve().parents[1]/'assets'/'schematic'
out.mkdir(parents=True,exist_ok=True)
INK='#233e48'; TEAL='#4daf9e'; BLUE='#91bcf0'; GOLD='#efc86b'; WHITE='#ffffff'
def draw_icon(name,t):
 im=Image.new('RGBA',(128,128),(255,255,255,0)); d=ImageDraw.Draw(im)
 def line(points,fill=INK,w=3): d.line(points,fill=fill,width=w,joint='curve')
 def rect(box,fill=WHITE,r=6): d.rounded_rectangle(box,radius=r,fill=fill,outline=INK,width=3)
 def ellipse(box,fill=WHITE): d.ellipse(box,fill=fill,outline=INK,width=3)
 pulse=(math.sin(t*2*math.pi)+1)/2
 if name=='satellite':
  d.ellipse((34,74,94,120),fill='#daf0e8',outline=INK,width=2)
  d.arc((40,76,87,110),0,160,fill=TEAL,width=3)
  rect((43,22,82,58),GOLD,5);rect((8,25,36,55),BLUE,2);rect((89,25,117,55),BLUE,2)
  for x in [17,26,98,107]: line([(x,27),(x,53)],'#496f9d',1)
  line([(9,40),(34,40)],'#496f9d',1);line([(91,40),(115,40)],'#496f9d',1)
  line([(36,40),(43,40)]);line([(82,40),(89,40)]);line([(62,22),(62,11)])
  ellipse((59,7,65,13),TEAL)
  for i in range(3):
   y=61+(i*10+t*24)%27; d.arc((50,y,76,y+13),0,180,fill=TEAL,width=2)
 elif name=='sensor':
  rect((12,82,115,108),'#e5f2ec');ellipse((20,90,28,98),TEAL);ellipse((101,90,109,98),GOLD)
  line([(64,81),(64,68)])
  for i in range(3):d.arc((39-i*10,34-i*10,89+i*10,82+i*10),205,335,fill=TEAL if (int(t*6)+i)%3==0 else INK,width=3)
  pts=[(12+i,55+math.sin((i/6)+t*math.pi*2)*math.exp(-((i-50)/25)**2)*17) for i in range(102)]
  line(pts,'#507aa4',2)
 elif name=='weather':
  ellipse((75,12,105,42),GOLD)
  for i in range(8):
   a=i*math.pi/4+t*.3;line([(90+20*math.cos(a),27+20*math.sin(a)),(90+25*math.cos(a),27+25*math.sin(a))],GOLD,3)
  ellipse((20,42,65,84),'#d1e5fa');ellipse((44,30,89,84),'#d1e5fa');ellipse((73,50,112,84),'#d1e5fa')
  d.rounded_rectangle((21,65,109,88),12,fill='#d1e5fa');line([(27,88),(102,88)])
  for x in [36,58,80,102]:
   y=91+(x/7+t*22)%16;line([(x,y),(x-4,y+8)],'#4e93b5',3)
 elif name=='aggregate':
  rect((41,39,90,91),'#d5eee7');line([(53,52),(76,52)],TEAL);line([(53,63),(76,63)],TEAL);line([(53,74),(68,74)],TEAL)
  for sx,sy,ex,ey in [(12,22,41,44),(116,22,90,44),(12,106,41,84),(116,106,90,84)]:
   line([(sx,sy),(ex,ey)],'#8bb7ac',2)
   q=t;xx=sx+(ex-sx)*q;yy=sy+(ey-sy)*q;ellipse((xx-4,yy-4,xx+4,yy+4),GOLD)
  for x,y in [(6,16),(110,16),(6,100),(110,100)]:rect((x,y,x+12,y+12),BLUE,2)
 elif name=='segment':
  rect((8,15,119,113),'#eaf1f8')
  d.polygon([(12,76),(39,37),(62,67),(87,30),(114,76)],fill='#a9bac7',outline=INK)
  d.polygon([(39,37),(32,49),(41,46),(46,50)],fill=WHITE)
  d.polygon([(87,30),(79,42),(87,39),(95,44)],fill=WHITE)
  d.ellipse((24,74,107,102),fill='#a2e4df',outline=TEAL,width=3)
  x=17+t*91;line([(x,24),(x,105)],TEAL,2);ellipse((x-3,105,x+3,111),TEAL)
  for a,b,c,e in [(17,24,32,24),(17,24,17,39),(111,24,96,24),(111,24,111,39)]:line([(a,b),(c,e)],'#628cc1',2)
 elif name=='judge':
  rect((29,17,99,111),'#f3ebfb');rect((48,9,80,28),GOLD,4)
  for i in range(3):
   y=40+i*22;rect((40,y,53,y+13),WHITE,2);line([(63,y+5),(88,y+5)],'#8b739d',2)
   if t>i/4:line([(42,y+6),(46,y+10),(52,y+2)],TEAL,3)
 elif name=='routing':
  rect((13,46,48,83),'#d5eee7');line([(48,65),(70,65),(70,26),(95,26)]);line([(70,65),(95,65)]);line([(70,65),(70,105),(95,105)])
  for y,c in [(26,TEAL),(65,GOLD),(105,'#db8a83')]:ellipse((94,y-9,113,y+10),c)
  active=int(t*3)%3
  for i,y in enumerate([26,65,105]):
   if i==active:d.ellipse((98,y-5,109,y+6),fill=WHITE)
  line([(23,65),(38,65)],TEAL,3)
 elif name=='monitor':
  ellipse((18,18,110,110),'#d9f0e6');ellipse((34,34,94,94),'#d9f0e6');ellipse((51,51,77,77),'#d9f0e6')
  line([(64,20),(64,108)],'#8fc7ac',1);line([(20,64),(108,64)],'#8fc7ac',1)
  a=t*2*math.pi;line([(64,64),(64+44*math.cos(a),64+44*math.sin(a))],TEAL,3)
  d.ellipse((79,39,87,47),fill=TEAL)
 elif name=='review':
  rect((52,22,113,100),'#fff0cb');line([(65,42),(99,42)],'#b69b5e',2);line([(65,54),(99,54)],'#b69b5e',2)
  ellipse((22,30,54,62),GOLD);d.rounded_rectangle((10,67,66,113),radius=20,fill='#b5d6ee',outline=INK,width=3)
  line([(70,79),(77,86),(95,67)],TEAL if pulse>.3 else '#b3cdb6',4)
 elif name=='alert':
  y=round(pulse*2)
  d.polygon([(64,16+y),(114,105+y),(14,105+y)],fill='#ffe7d1',outline=INK,width=3)
  rect((60,44+y,68,76+y),'#df8376',3);ellipse((60,84+y,68,92+y),'#df8376')
  for x in [20,100]:line([(x,20),(x+(-7 if x<64 else 7),12)],'#dd9885' if pulse>.4 else '#ecd3c7',3)
 elif name=='cloud':
  ellipse((13,41,55,85),'#d1e5fa');ellipse((33,24,87,85),'#d1e5fa');ellipse((72,40,117,85),'#d1e5fa')
  d.rounded_rectangle((15,62,115,85),10,fill='#d1e5fa');line([(22,85),(105,85)])
  d.polygon([(64,47),(43,70),(55,70),(55,107),(73,107),(73,70),(85,70)],fill=WHITE,outline=INK,width=3)
  yy=round(106-t*21);line([(60,yy),(68,yy)],TEAL,3)
 # Render with one reserved palette color for background transparency.
 rgb=Image.new('RGB',im.size,'#ff00ff');rgb.paste(im,mask=im.getchannel('A'))
 pal=rgb.quantize(colors=255)
 palette=pal.getpalette();idx=pal.getpixel((0,0));pal.info['transparency']=idx
 return im,pal
for name in ['satellite','sensor','weather','aggregate','segment','judge','routing','monitor','review','alert','cloud']:
 rgba=[draw_icon(name,i/24)[0] for i in range(24)]
 rgb=[]
 for im in rgba:
  frame=Image.new('RGB',im.size,'white');frame.paste(im,mask=im.getchannel('A'));rgb.append(frame)
 atlas=Image.new('RGB',(128*24,128),'white')
 for i,frame in enumerate(rgb):atlas.paste(frame,(128*i,0))
 palette=atlas.quantize(colors=255)
 values=palette.getpalette();values[765:768]=[255,0,255];palette.putpalette(values)
 frames=[]
 for source,frame in zip(rgba,rgb):
  pal=frame.quantize(palette=palette,dither=Image.Dither.NONE)
  mask=source.getchannel('A').point(lambda a:255 if a==0 else 0)
  pal.paste(255,mask=mask);pal.info['transparency']=255;frames.append(pal)
 frames[0].save(out/(name+'.gif'),save_all=True,append_images=frames[1:],duration=80,loop=0,disposal=2,transparency=255,optimize=False)
 draw_icon(name,.9)[0].save(out/(name+'.png'))
 print(name,Image.open(out/(name+'.gif')).n_frames)
