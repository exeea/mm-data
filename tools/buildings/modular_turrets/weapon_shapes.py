"""Exposed weapon housings. Shape, not permanently lit muzzle colour, identifies the weapon.

All ranges use a rear installation datum at Y=0 and can be recessed by the mount.
Native Blender geometry helpers provide watertight bodies and deliberately authored LODs.
"""
import math


def mouth(ref, name, x, y, z, radius, lod, depth=.4):
    """Recessed dark bore, with an actual chamfered rim; no emissive or painted dots."""
    n=12 if lod==0 else 8
    front=[(x+radius*math.cos(i*math.tau/n),y,z+radius*math.sin(i*math.tau/n)) for i in range(n)]
    inner=[(x+radius*.77*math.cos(i*math.tau/n),y-.08,z+radius*.77*math.sin(i*math.tau/n)) for i in range(n)]
    if lod==0:
        back=[(x+radius*.74*math.cos(i*math.tau/n),y-depth,z+radius*.74*math.sin(i*math.tau/n)) for i in range(n)]
        obj=ref.mesh_obj(name,front+inner+back,
              [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]+
              [(i+n,(i+1)%n+n,(i+1)%n+2*n,i+2*n) for i in range(n)]+[tuple(range(2*n,3*n))],'steel')
        obj.data.materials.append(ref.MATS['dark']); obj.data.materials.append(ref.MATS['black'])
        for p in obj.data.polygons:
            p.material_index=2 if len(p.vertices)>4 else 1 if min(p.vertices)>=n else 0
    else:
        obj=ref.mesh_obj(name,front+inner,[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]+[tuple(range(n,2*n))],'steel')
        obj.data.materials.append(ref.MATS['black'])
        for p in obj.data.polygons:
            if len(p.vertices)>4:p.material_index=1
    # Open rings have no interior volume; explicitly orient the front toward +Y.
    for poly in obj.data.polygons:
        if poly.normal.y<-.01: poly.flip()
    return obj


_shape={}
exec(compile((HERE/'hard_surface.py').read_text(),'hard_surface','exec'),_shape)


def laser(ref, size, lod):
    start=len(ref.PARTS); scale={'small':.55,'medium':1.0,'large':1.35}[size]
    _shape['shell'](ref,'Laser power chamber',[(0,2.6,2.8,.45,0),(.6,3.25,3.25,.55,0),
                    (3.9,3.25,3.25,.55,0),(4.7,2.6,2.4,.35,0)],'dark')
    _shape['shell'](ref,'Laser upper power armor',[(.45,2.9,.40,.14,1.42),(3.5,2.9,.55,.18,1.48),
                    (4.3,2.35,.30,.12,1.30)],'armor')
    _shape['shell'](ref,'Laser vented shroud core',[(4.1,2.5,2.4,.3,0),(9.6,2.5,2.4,.3,0),(10.4,1.8,1.8,.25,0)],'dark')
    for sign in (-1,1):
        _shape['side_panel'](ref,'Laser power side plate',sign*1.65,[(.8,-1),(3.3,-1),(3.85,-.4),(3.85,.75),(.8,1.05)],.15,'armor')
        _shape['side_vent'](ref,sign*1.74,2.1,.0,1.8,1.1,lod)
        _shape['side_panel'](ref,'Shroud upper side rail',sign*1.30,[(4.7,.70),(9.5,.70),(9.8,1.10),(4.7,1.10)],.18,'armor')
        _shape['side_panel'](ref,'Shroud lower side rail',sign*1.30,[(4.7,-1.10),(9.8,-1.10),(9.5,-.70),(4.7,-.70)],.18,'armor')
        if lod==0:
            for y in (5.0,5.85,6.7,7.55,8.4,9.25):
                ref.block('Shroud cooling rib',(sign*1.31,y,0),(.20,.18,1.45),'steel',cut=0,bevel=0)
    ref.block('Laser upper spine',(0,7.0,1.22),(1.45,5.4,.25),'armor',cut=.25,bevel=0)
    ref.ring('Focusing assembly',[(10.0,.77),(10.6,.77),(10.9,.59),(13.8,.48),(14.1,.62)],'steel',12 if lod==0 else 8,(0,0),axis='Y')
    if lod==0:
        for y in (11.1,11.75,12.4,13.05):
            ref.ring('Focusing heat fin',[(y,.65),(y+.12,.65)],'dark',8,(0,0),axis='Y')
        for sign in (-1,1):
            _shape['pipe'](ref,'Laser coolant return',[(sign*1.7,.8,-.65),(sign*1.75,1.1,-.65),
                          (sign*1.75,3.0,-.65),(sign*1.4,4.2,-.65)],.10,lod,'steel')
    mouth(ref,'Unlit recessed laser optic',0,14.18,0,.62,lod,.28)
    for obj in ref.PARTS[start:]:
        for v in obj.data.vertices: v.co*=scale
    return [(0,14.18*scale,0)]


_racks={}
exec(compile((HERE/'racks.py').read_text(),'racks','exec'),_racks)


def missile(ref, kind, count, lod):
    rack=_racks['RACKS'][kind]
    cell,cols=rack['cell'],rack['cols'][count]
    rows=math.ceil(count/cols); w=cols*cell+.65; h=rows*cell+.65
    length=rack['length']
    _shape['shell'](ref,'Sealed launcher cassette',[(0,w*.90,h*.88,.35,0),(.5,w,h,.42,0),
                    (length-1.1,w,h,.42,0),(length-.65,w*.94,h*.94,.38,0)],'dark')
    _shape['shell'](ref,'Rear launcher armor',[(.08,w*.96,h*.96,.4,0),(.55,w*.96,h*.96,.4,0)],'armor')
    # One chamfered continuous armored face, with deep tubes and a dark recessed backing.
    _shape['frame'](ref,'Launcher armored face',length+.05,w+.18,h+.18,.27,.8,'steel')
    ref.block('Launcher dark recessed backing',(0,length-.68,0),(w-.25,.08,h-.25),'black',cut=.25,bevel=0)
    tips=[]
    for i in range(count):
        row,col=divmod(i,cols); row_count=min(cols,count-row*cols)
        x=(col-(row_count-1)/2)*cell; z=((rows-1)/2-row)*cell
        mouth(ref,'Launch tube',x,length,z,cell*.40,lod,.55)
        tips.append((x,length+.02,z))
    for sign in (-1,1):
        side_x=sign*(w/2+.04)
        outline=[(.7,-h*.34),(length-1.35,-h*.34),(length-1.35,h*.25),
                 (length-2.3,h*.38),(.7,h*.38)]
        _shape['side_panel'](ref,'Launcher layered upper armor',side_x,outline,.18,'armor')
        ref.block('Launcher side control housing',(sign*(w/2+.20),length*.45,-h*.08),
                  (.45,1.25,h*.46),'steel',cut=.16,bevel=0)
        _shape['side_vent'](ref,sign*(w/2+.145),length*.22,-h*.20,length*.19,h*.22,lod)
        _shape['pipe'](ref,'Launcher routed service line',[(side_x,length-1.5,h*.12),
                      (sign*(w/2+.30),length-1.7,h*.12),(sign*(w/2+.30),length-2.2,-h*.14),
                      (sign*(w/2+.30),length*.49,-h*.14)],.095,lod,'steel')
        if lod==0:
            for y in [y for y in (1.0,2.3,3.6,4.9,6.2) if y<length-1.3]:
                ref.block('Launcher lower armor fastener',(sign*(w/2-max(0,.42-h*.10)+.03),y,-h*.40),(.18,.22,.22),'steel',cut=.03,bevel=0)
    _shape['shell'](ref,'Launcher ridged top armor',[(.6,w*.84,.26,.1,h*.46),
                    (1.2,w*.84,.5,.16,h*.51),(length-1.7,w*.84,.5,.16,h*.51),
                    (length-1.1,w*.72,.24,.1,h*.46)],'armor')
    if lod==0:
        for y in (1.5,2.1,length-2.8,length-2.2):
            ref.block('Launcher top recessed seam',(0,y,h*.51+.255),(w*.67,.09,.02),'dark',cut=0,bevel=0)
    return tips


def draw(ref, family, variant, lod):
    if family=='laser': return laser(ref,variant,lod)
    return missile(ref,*variant,lod)
