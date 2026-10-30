"""The machine gun's full receiver, and the trunnion layout of the machine gun and lasers."""
_shape={}
exec(compile((HERE/'hard_surface.py').read_text(),'hard_surface','exec'),_shape)


def layout(family, variant):
    # Trunnion width, barrel front datum, longitudinal pivot, height above hull socket.
    if family=='machine-gun': return (2.0,4.2,2.2,5.3)
    s={'small':.55,'medium':1,'large':1.35}[variant]
    return (3.5*s,0,2.3*s,5.3 if variant=='small' else 6.8)


def body(ref, family, variant, lod):
    w,length,cy,cz=layout(family,variant)
    start=len(ref.PARTS)
    if family!='machine-gun': return []
    h=1.9
    sw=w*.92
    _shape['shell'](ref,'Complete recoil receiver',[(0,sw*.88,h*.84,.45,0),(.65,sw,h,.55,0),
                     (length*.65,sw,h,.55,0),(length,sw*.75,h*.78,.4,0)],'dark')
    _shape['shell'](ref,'Receiver top armor',[(.55,sw*.92,.50,.15,h*.43),(length*.55,sw*.92,.60,.18,h*.48),
                     (length*.78,sw*.66,.34,.12,h*.43)],'armor')
    for sign in (-1,1):
        x=sign*(sw/2+.055)
        outline=[(.9,-h*.25),(length*.56,-h*.25),(length*.72,-h*.05),(length*.62,h*.25),(.9,h*.25)]
        _shape['side_panel'](ref,'Receiver removable side armor',x,outline,.13,'armor')
        _shape['side_vent'](ref,x+sign*.08,length*.29,0,length*.27,h*.30,lod)
        ref.ring('Recoil recuperator',[(length*.48,.13),(length+.45,.13)],
                 'steel',8 if lod==0 else 6,(sign*sw*.31,-h*.37),axis='Y')
    _shape['shell'](ref,'Rear breech service armor',[(.04,sw*.88,h*.84,.4,0),(.32,sw*.88,h*.84,.4,0)],'steel')
    for sign in (-1,1):
        ref.block('Receiver side feed coupling',(sign*sw*.49,cy,0),(.36,1.5,1.35),
                  'steel',cut=.12,bevel=0)
    if lod==0:
        def armor_top(y):
            a,b=(.55,length*.55) if y<=length*.55 else (length*.55,length*.78)
            za,zb=(h*.43+.25,h*.48+.30) if y<=length*.55 else (h*.48+.30,h*.43+.17)
            return za+(zb-za)*(y-a)/(b-a)
        for y in (.95,length*.42,length*.64):
            for s in (-1,1): ref.bolt((s*sw*.30,y,armor_top(y)-.058),radius=.075)
        ref.block('Breech inspection hatch',(0,length*.28,h*.52),(sw*.52,length*.22,.16),'steel',cut=.2,bevel=0)
    fixed=ref.PARTS[start:].copy()
    ref.block('Recoiling breech slide',(0,length*.72,h*.37),(sw*.38,length*.39,.55),'steel',cut=.16,bevel=0)
    return fixed
