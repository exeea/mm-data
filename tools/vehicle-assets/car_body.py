"""A road car read off its reference sheet: where its four views lie, its outline along its length, its belt line and
roof, its width, and its wheels. build.py lofts the body through the outlines this gives and lays every face on the
view it faces, so a new car needs its sheet and its length, nothing measured by hand.

The sheet: side view top left and top view bottom left, both with the front to the left; front view top right, rear
view bottom right; a flat background.
"""
import numpy as np
from PIL import Image
from scipy import ndimage

from photo_shell import Sheet


def boxes(solid):
    """The four views' boxes: side, top, front, rear."""
    labels, _ = ndimage.label(ndimage.binary_dilation(solid, iterations=6))
    found = []
    for index, area in enumerate(ndimage.find_objects(labels), 1):
        part = solid[area] & (labels[area] == index)
        if part.sum() > 4000:
            ys, xs = np.where(part)
            found.append((area[1].start+xs.min(), area[0].start+ys.min(), area[1].start+xs.max()+1, area[0].start+ys.max()+1))
    assert len(found) == 4, found
    middle_x, middle_y = solid.shape[1]/2, solid.shape[0]/2
    place = {(b[0] > middle_x, b[1]+b[3] > 2*middle_y): b for b in found}
    return place[(False, False)], place[(False, True)], place[(True, False)], place[(True, True)]


def width_below(view, share):
    """The middle and half width of a front or rear view's body below `share` of its height: under its mirrors."""
    rows = view[int(view.shape[0]*share):int(view.shape[0]*.9)]
    left = np.median([np.argmax(row) for row in rows if row.any()])
    right = np.median([len(row)-np.argmax(row[::-1]) for row in rows if row.any()])
    return (left+right)/2, (right-left)/2


class Car:
    """A car's measures, in model units: y from its nose (-length/2) to its tail, z up from the ground."""

    def __init__(self, name, sheet_file, length, roof_inset=None):
        image = np.asarray(Image.open(sheet_file).convert('RGB')).astype(float)
        flat = np.median(image[:8, :8].reshape(-1, 3), axis=0)
        solid = ndimage.binary_opening(np.abs(image-flat).max(axis=2) > 14, iterations=1)
        side, top, front, rear = boxes(solid)
        self.length = length
        scale = self.scale = length/(side[2]-side[0])  # Units a side-view pixel.
        mask = solid[side[1]:side[3], side[0]:side[2]]
        high, wide = mask.shape
        ground = high  # The tyres stand on the box's lowest row.
        outline = np.array([ground-np.argmax(column) if column.any() else 0 for column in mask.T], float)  # Top of the body, by column.
        # Wheels: below the sills only the tyres are solid, and a tyre's chord at a height tells its radius.
        self.wheels = []
        h = max(6, round(.035*wide*.5))
        chord = mask[ground-h]
        runs, _ = ndimage.label(chord)
        for run in ndimage.find_objects(runs):
            w = run[0].stop-run[0].start
            if w > .03*wide:
                self.wheels.append((((run[0].start+run[0].stop)/2-wide/2)*scale, (w*w/4+h*h)/(2*h)*scale))
        assert len(self.wheels) == 2, self.wheels
        between = int((self.wheels[0][0]+self.wheels[1][0])/2/scale+wide/2)
        self.sill = (ground-np.max(np.where(mask[:, between])[0])-1)*scale
        # Glass: the dark band in the upper body. Its foot is the belt line, its ends the cabin's.
        pixels = image[side[1]:side[3], side[0]:side[2]]
        roof = outline.max()
        dark = (pixels.max(axis=2) < 95) & mask
        dark[int(high-.45*roof):] = False
        dark = ndimage.binary_opening(dark, iterations=2)
        tall = [column for column in dark.T if column.sum() > .12*roof]  # The side windows' columns.
        belt_row = float(np.median([np.max(np.where(column)[0]) for column in tall]))
        self.belt = (ground-belt_row-1)*scale
        dark[int(belt_row)+1:] = False  # Lamps and grilles lie under the belt.
        xs = np.where(dark)[1]
        cabin = (np.percentile(xs, .5), np.percentile(xs, 99.5))
        flat_roof = np.where(outline > roof-.035*roof)[0]
        marks = [0, .055*wide, cabin[0], flat_roof.min(), flat_roof.max(), cabin[1], wide-.045*wide, wide-1]
        for k in range(1, len(marks)):  # In order, each a little past the one before.
            marks[k] = max(marks[k], marks[k-1]+.02*wide)
        marks[-1] = wide-1
        for k in range(len(marks)-2, 0, -1):
            marks[k] = min(marks[k], marks[k+1]-.02*wide)
        # Widths: the top view's outline by column (its mirrors stand out of it), the roof's share from the front view.
        plan = solid[top[1]:top[3], top[0]:top[2]]
        plan_middle = plan.shape[0]/2
        plan_scale = length/plan.shape[1]
        halves = np.array([(len(column)-np.argmax(column[::-1])-np.argmax(column))/2 if column.any() else 0 for column in plan.T])*plan_scale
        body = np.percentile(halves, 80)
        halves = np.minimum(halves, body)
        self.half = body
        face = solid[front[1]:front[3], front[0]:front[2]]
        back = solid[rear[1]:rear[3], rear[0]:rear[2]]
        face_scale = roof*scale/face.shape[0]
        back_scale = roof*scale/back.shape[0]
        face_middle, face_half = width_below(face, .55)
        back_middle, _ = width_below(back, .55)
        crown = face[int(face.shape[0]*.06)]
        roof_share = roof_inset or min(.9, (crown.sum()/2)/face_half)
        self.stations = []
        for k, mark in enumerate(marks):
            column = int(min(wide-1, mark))
            near = slice(max(0, column-2), column+3)
            y = (mark-wide/2)*scale
            inward = min(max(column, .02*wide), .98*wide)  # A nose or tail's face is as wide as the body just behind it.
            half = max(.55*body, float(halves[int(np.clip(inward*plan.shape[1]/wide, 0, plan.shape[1]-1))]))
            top_z = float(np.median(outline[near]))*scale
            cabin_part = 2 <= k <= 5
            shoulder = min(top_z, self.belt) if cabin_part else top_z
            low = [(half-.08, self.sill), (half, self.sill+.5*(shoulder-self.sill)), (half, shoulder-.1)]
            if cabin_part:
                roof_half = body*roof_share if k in (3, 4) else half-.16
                upper = [(half-.13, shoulder), (roof_half, max(top_z, shoulder+.02)), (0, max(top_z, shoulder+.02)+.04)]
            else:
                upper = [(half-.16, shoulder-.02), (half-.55, shoulder+.02), (0, shoulder+.04)]
            self.stations.append((y, low+upper))
        self.sheet = Sheet(name, {
            'side': {'box': side, 'rect': (0, 0, .70, .44),
                     'map': lambda x, y, z: (side[0]+wide/2+y/scale, side[3]-z/scale)},
            'front': {'box': front, 'rect': (.70, 0, 1, .44),
                      'map': lambda x, y, z: (front[0]+face_middle+x/face_scale, front[3]-z/face_scale)},
            'top': {'box': top, 'rect': (0, .44, .70, 1),
                    'map': lambda x, y, z: (top[0]+plan.shape[1]/2+y/plan_scale, top[1]+plan_middle+x/plan_scale)},
            'rear': {'box': rear, 'rect': (.70, .44, 1, 1),
                     'map': lambda x, y, z: (rear[0]+back_middle-x/back_scale, rear[3]-z/back_scale)}})
