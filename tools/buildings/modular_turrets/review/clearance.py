"""Read-only exported-GLB receiver/hull clearance audit. Does not modify assets.
A vertex below an upward-visible hull surface is evidence to inspect, not a complete
triangle collision solver. Intentional mounting overlap is excluded by selecting moving parts.
"""
import json, struct, math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[4]/'data/models/buildings/turrets/modular'


def load(name, lod=0, ignore_black=False):
    raw=(ROOT/(name+'.glb')).read_bytes()
    size=struct.unpack_from('<I',raw,12)[0]
    doc=json.loads(raw[20:20+size]); binary=raw[28+size:]; nodes=doc['nodes']; out={}; matrices={}
    def accessor(index):
        a=doc['accessors'][index]; v=doc['bufferViews'][a['bufferView']]
        dt={5126:'<f4',5123:'<u2',5125:'<u4',5121:'u1'}[a['componentType']]
        k={'VEC3':3,'SCALAR':1}[a['type']]
        stride=v.get('byteStride',np.dtype(dt).itemsize*k)
        off=v.get('byteOffset',0)+a.get('byteOffset',0)
        return np.ndarray((a['count'],k),dtype=dt,buffer=binary,offset=off,
                          strides=(stride,np.dtype(dt).itemsize)).copy()
    def matrix(node):
        if 'matrix' in node: return np.array(node['matrix']).reshape(4,4).T
        m=np.eye(4); x,y,z,w=node.get('rotation',[0,0,0,1])
        m[:3,:3]=[[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                  [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                  [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]
        m[:3,:3]@=np.diag(node.get('scale',[1,1,1]));m[:3,3]=node.get('translation',[0,0,0])
        return m
    # GLB Y-up/-Z forward to engine Z-up/+Y forward.
    convert=np.array([[1,0,0],[0,0,-1],[0,1,0]])
    def walk(index,parent):
        node=nodes[index]; transform=parent@matrix(node)
        matrices[node.get('name')]=convert@transform[:3,3]
        if 'mesh' in node:
            triangles=[]
            for primitive in doc['meshes'][node['mesh']]['primitives']:
                if ignore_black and doc['materials'][primitive.get('material',0)].get('name','').startswith('authored/black'): continue
                v=accessor(primitive['attributes']['POSITION'])
                v=(np.c_[v,np.ones(len(v))]@transform.T)[:,:3]@convert.T
                indices=accessor(primitive['indices']).ravel() if 'indices' in primitive else np.arange(len(v))
                triangles.extend(v[indices.reshape(-1,3)])
            out[node['name']]=np.array(triangles)
        for child in node.get('children',[]): walk(child,transform)
    root=next(i for i,n in enumerate(nodes) if n.get('name','').endswith('-lod'+str(lod)))
    walk(root,np.eye(4))
    return out,matrices


class Roof:
    def __init__(self, triangles):
        self.a,self.b,self.c=triangles[:,0],triangles[:,1],triangles[:,2]
        self.u=self.b[:,:2]-self.a[:,:2];self.v=self.c[:,:2]-self.a[:,:2]
        self.d=self.u[:,0]*self.v[:,1]-self.u[:,1]*self.v[:,0]
        self.valid=np.abs(self.d)>1e-8
    def at(self,x,y):
        q=np.array([x,y])-self.a[:,:2]
        u=np.divide(q[:,0]*self.v[:,1]-q[:,1]*self.v[:,0],self.d,out=np.zeros(len(self.d)),where=self.valid)
        v=np.divide(self.u[:,0]*q[:,1]-self.u[:,1]*q[:,0],self.d,out=np.zeros(len(self.d)),where=self.valid)
        mask=self.valid&(u>=0)&(v>=0)&(u+v<=1)
        if not mask.any(): return None
        return float(np.max((self.a[:,2]+u*(self.b[:,2]-self.a[:,2])+v*(self.c[:,2]-self.a[:,2]))[mask]))


def shoulder_intersections(triangles, points, pivot):
    a,b,c=triangles[:,0],triangles[:,1],triangles[:,2]
    e1=b-a;e2=c-a
    # Open surface details (service recess patches) flip one ray's parity, so a point is inside only when two
    # unrelated rays agree.
    rays=[]
    for ray in ([.917,.371,.143],[.143,-.371,-.917]):
        ray=np.array(ray);ray/=np.linalg.norm(ray);h=np.cross(ray,e2);det=np.einsum('ij,ij->i',e1,h)
        valid=np.abs(det)>1e-7;rays.append((ray,h,valid,np.divide(1.,det,out=np.zeros(len(det)),where=valid)))
    hits=[]
    lower=triangles.min(axis=(0,1)); upper=triangles.max(axis=(0,1))
    for point in points:
        # A point outside the entire support bounds cannot be inside it. Surface
        # detail in the joined triangle soup can otherwise leave odd ray parity.
        if np.any(point < lower-1e-6) or np.any(point > upper+1e-6): continue
        # Bearing axle passing into its support is intentional.
        if np.linalg.norm((point-pivot)[1:])<1.12: continue
        tvec=point-a;q=np.cross(tvec,e1);inside=True
        for ray,h,valid,inv in rays:
            u=inv*np.einsum('ij,ij->i',tvec,h);v=inv*(q@ray);t=inv*np.einsum('ij,ij->i',e2,q)
            keep=valid&(u>=0)&(v>=0)&(u+v<=1)&(t>1e-5)
            inside&=len(np.unique(np.round(t[keep],5)))%2==1
        if inside: hits.append(point.tolist())
    return hits
