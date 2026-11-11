"""Seamless 512 px sources (albedo.png, orm.png, normal.png) for a wall or roof material, from a photographic study.

    python tools/materials/facade_sources.py <kind> <study.png> tools/materials/<folder>/<name>/sources

Needs numpy, scipy and Pillow. A study is an orthographic photograph under flat light, edge to edge. Kinds, by what
runs through the material:

    clapboard   horizontal lapped boards: each a wedge standing out at its lower edge
    planks      upright boards with dark gaps between them
    shingles    courses of lapped shingles, laid twice across and twice up the tile
    brick       courses of blocks in stretcher bond, their mortar squeezed out of the joints
    blocks      cast blocks or panels in a plain grid with sunk joints (and their sockets or bolts, by shade)
    render      a plastered wall: chips and cracks sunk
    felt        roofing felt in strips, their laps raised

The broad light is flattened. An axis the material's courses cross is cut to a whole number of them, where the study
goes on as it began, so its courses meet across the tile's edge; any other axis is made seamless along a minimum-error
cut (seamless.py). Normals come from the estimated height, OpenGL convention. A project cloned from
structures/common/weathered-paint reads the three sources into its Material node.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from seamless import across  # noqa: E402

SIZE = 512
# kind: (courses cross the rows, courses cross the columns, tiles across the 512, roughness, normal strength, value)
KINDS = {
    'clapboard': (True, False, 1, .82, 5.0, 1.0),
    'planks': (False, True, 1, .88, 4.0, 1.0),
    'shingles': (True, False, 2, .9, 5.0, 1.0),
    'brick': (True, True, 1, .9, 5.0, .86),
    'blocks': (True, True, 1, .7, 4.0, 1.0),
    'render': (False, False, 1, .9, 3.0, 1.0),
    'felt': (True, False, 1, .93, 3.0, 1.0),
}


def smoothstep(a, b, x):
    t = np.clip((x-a)/(b-a), 0, 1)
    return t*t*(3-2*t)


def blur(a, sigma):
    return gaussian_filter(a, sigma, mode='wrap')


def period(image):
    """The courses' pitch down the rows, in pixels: the strongest repeat of the rows' mean brightness."""
    profile = image.mean((1, 2))
    profile = profile-gaussian_filter(profile, len(profile)/8, mode='reflect')
    spectrum = np.abs(np.fft.rfft(profile*np.hanning(len(profile))))
    return len(profile)/(int(spectrum[3:len(profile)//6].argmax())+3)


def whole_courses(image, band=8):
    """The rows cut to a whole number of courses: a stretch after which the study goes on as it began, its last rows
    faded into the rows before its first."""
    height, pitch = image.shape[0], period(image)
    grey = image.mean(2)
    best = None
    for length in range(int(.72*height), height-2*band):  # Brick repeats every second course: the search finds it.
        for start in range(band, height-band-length+1):
            cost = np.abs(grey[start:start+band]-grey[start+length:start+length+band]).mean()
            if best is None or cost < best[0]:
                best = cost, start, length
    cost, start, length = best
    out = image[start:start+length].copy()
    for i in range(band):
        t = (i+1)/(band+1)
        out[length-band+i] = (1-t)*out[length-band+i]+t*image[start-band+i]
    return out, round(length/pitch)


def sources(kind, study):
    rows, columns, tiles, base_roughness, strength, value = KINDS[kind]
    image = np.asarray(Image.open(study).convert('RGB'), float)/255
    luminance = image.mean(2)
    image = np.clip(image*(luminance.mean()/gaussian_filter(luminance, len(image)/5, mode='reflect'))[..., None], 0, 1)
    counts = [1, 1]
    for axis, coursed in enumerate((rows, columns)):
        turned = np.swapaxes(image, 0, axis)
        if coursed:
            turned, counts[axis] = whole_courses(turned)
        else:
            turned = np.swapaxes(across(np.swapaxes(turned, 0, 1), np.ones(3)), 0, 1)
        image = np.swapaxes(turned, 0, axis)
    side = SIZE//tiles
    tile = np.asarray(Image.fromarray((np.clip(image, 0, 1)*255).round().astype(np.uint8)).resize((side, side), Image.LANCZOS), float)/255
    image = np.tile(tile, (tiles, tiles, 1))*value
    lum = image.mean(2)
    saturation = image.max(2)-image.min(2)
    grain = lum-blur(lum, 2.5)
    grain /= np.abs(grain).max() or 1
    shade = smoothstep(.0, .22, blur(lum, 6)-lum)  # Shadow lines, gaps and joints.
    if kind in ('clapboard', 'shingles'):
        # Each course a wedge: it starts under the shadow of the course above and stands out most at its lower edge.
        pitch = SIZE/(counts[0]*tiles)
        profile = lum.mean(1)
        phase = min(range(round(pitch)), key=lambda s: profile[(np.arange(counts[0]*tiles)*pitch+s).round().astype(int) % SIZE].sum())
        wedge = ((np.arange(SIZE)-phase-1) % pitch)/pitch
        height = np.repeat(wedge[:, None], SIZE, 1)*.8+.1*grain-.3*shade*(kind == 'shingles')
    elif kind == 'brick':
        mortar = blur(smoothstep(.16, .08, saturation), .7)
        image = image*(1-.2*saturation[..., None])+.2*saturation[..., None]*lum[..., None]  # A little less orange.
        height = .45+.3*mortar+.12*grain
    else:
        height = .7-.5*shade+.15*grain
    height = np.clip(height, 0, 1)
    occlusion = np.clip(1-1.6*np.clip(blur(height, 3)-height, 0, 1), .45, 1)
    roughness = np.clip(base_roughness+.12*grain-.1*smoothstep(.02, .15, saturation)*(kind == 'clapboard'), 0, 1)
    dx = (np.roll(height, -1, 1)-np.roll(height, 1, 1))/2
    dy = (np.roll(height, -1, 0)-np.roll(height, 1, 0))/2
    normal = np.stack([-dx*strength, dy*strength, np.ones_like(dx)], -1)  # OpenGL: +Y towards the image's top.
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    orm = np.stack([occlusion, roughness, np.zeros_like(lum)], -1)
    return np.clip(image, 0, 1), orm, (normal+1)/2, counts


if __name__ == '__main__':
    kind, study, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    albedo, orm, normal, counts = sources(kind, study)
    out.mkdir(parents=True, exist_ok=True)
    for name, data in (('albedo', albedo), ('orm', orm), ('normal', normal)):
        Image.fromarray((data*255).round().astype(np.uint8)).save(out/f'{name}.png')
    print(kind, 'courses', counts, 'albedo mean', np.round(albedo.reshape(-1, 3).mean(0), 3), 'roughness', round(float(orm[..., 1].mean()), 2))
