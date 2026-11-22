import json, os
from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageChops
root='/mnt/user-data/uploads/photo'
idx={i:p for i,p,s in json.load(open('index.json'))}
OUT='/home/claude/msims-build/site/assets/img'

def trim_white(im, thr=244):
    bg=Image.new('RGB',im.size,(255,255,255))
    diff=ImageChops.difference(im,bg).convert('L').point(lambda v:255 if v>(255-thr) else 0)
    box=diff.getbbox()
    return im.crop(box) if box else im

def crop32(im, fx=0.5, fy=0.5, top=0.0, left=0.0, right=0.0, bottom=0.0):
    w,h=im.size
    im=im.crop((int(w*left),int(h*top),int(w*(1-right)),int(h*(1-bottom))))
    w,h=im.size
    if w/h>1.5:
        nw=int(h*1.5); x=int((w-nw)*fx); im=im.crop((x,0,x+nw,h))
    else:
        nh=int(w/1.5); y=int((h-nh)*fy); im=im.crop((0,y,w,y+nh))
    return im

def enhance(im, photo=True):
    im=ImageOps.autocontrast(im,cutoff=(0.4,0.4),preserve_tone=True)
    im=ImageEnhance.Color(im).enhance(1.07 if photo else 1.04)
    im=ImageEnhance.Contrast(im).enhance(1.05 if photo else 1.02)
    return im

def save(im,name,widths):
    made=[]
    for w in widths:
        if w>im.width*1.06: continue
        r=im.resize((w,round(w/1.5)),Image.LANCZOS) if w!=im.width else im
        r=r.filter(ImageFilter.UnsharpMask(radius=1.0,percent=55,threshold=2))
        p=f'{OUT}/{name}-{w}.webp'; r.save(p,'WEBP',quality=78,method=6); made.append((w,os.path.getsize(p)))
    return made

# nama, indeks, jenis, parameter pangkas
JOBS=[
 ('bot-perikanan-pameran',2,'photo',dict(fy=0.62)),
 ('jentuai-padi-pameran',5,'photo',dict(fy=0.55)),
 ('vr-durian-pavilion',18,'design',dict()),
 ('vr-sayangi-laut-penyu',32,'shot',dict(top=0.15,left=0.12,fx=0.75)),
 ('vr-pukat-tunda-krew',26,'shot',dict(fx=0.45)),
 ('dron-pelatih',11,'photo',dict(fy=0.35)),
 ('vr-durian-belah',14,'shot',dict(top=0.17,fx=0.6)),
 ('vr-mygap-stesen',29,'shot',dict(fx=0.8)),
 # gambar kad
 ('bot-perikanan-kemudi',0,'photo',dict(fy=0.45)),
 ('jentuai-padi-rig',7,'design',dict()),
 ('dron-kelas',8,'design',dict()),
 ('vr-pertanian-pengguna',20,'photo',dict(fy=0.78)),
 ('vr-strawberi-petik',17,'shot',dict(top=0.16,fx=0.7)),
 ('vr-pukat-tunda-geladak',27,'shot',dict(fy=0.4)),
 ('vr-sayangi-laut-karang',35,'shot',dict(top=0.1,fx=0.6)),
]
report={}
for name,i,kind,kw in JOBS:
    im=ImageOps.exif_transpose(Image.open(os.path.join(root,idx[i]))).convert('RGB')
    if kind=='design': im=trim_white(im)
    im=crop32(im,**kw)
    im=enhance(im,photo=(kind!='shot'))
    widths=[1200,600] if im.width>=1130 else ([im.width//2*2] if im.width<700 else [im.width//2*2,600])
    if im.width>=1130: pass
    made=save(im,name,widths)
    report[name]={'src':idx[i],'crop':im.size,'out':made}
    print(name,im.size,made)
json.dump(report,open('report.json','w'),indent=1)
