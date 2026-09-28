import sys, time
import numpy as np
from PIL import Image, ImageDraw
from core import W, H
import scene


def to_img(surf):
    buf = np.ndarray((H, W, 4), np.uint8, surf.get_data())
    return Image.fromarray(buf[:, :, [2, 1, 0]].copy())


if __name__ == '__main__':
    out = sys.argv[1]
    times = [float(x) for x in sys.argv[2:]]
    scale = 0.3 if len(times) > 1 else 1.0
    ims = []
    for t in times:
        t0 = time.time()
        im = to_img(scene.render(t))
        print(f't={t:.2f} rendered in {time.time() - t0:.2f}s', flush=True)
        if scale != 1.0:
            im = im.resize((int(W * scale), int(H * scale)), Image.LANCZOS)
            d = ImageDraw.Draw(im)
            d.rectangle((0, 0, 70, 22), fill=(0, 0, 0))
            d.text((4, 4), f'{t:.2f}s', fill=(255, 255, 255))
        ims.append(im)
    if len(ims) == 1:
        ims[0].save(out)
    else:
        cols = min(len(ims), 5)
        rows = (len(ims) + cols - 1) // cols
        w, h = ims[0].size
        sheet = Image.new('RGB', (cols * w, rows * h), (255, 255, 255))
        for i, im in enumerate(ims):
            sheet.paste(im, ((i % cols) * w, (i // cols) * h))
        sheet.save(out)
