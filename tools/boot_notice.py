"""Render the identified CHS legal notice without changing its meaning or texture layout.

Entry 14753 format 1 stores BGRA, verified by the user screenshot (red heading)
and the original pixels (00 00 FF FF). The generic G1T reader exposes raw RGBA
channels, so this renderer explicitly converts only this identified texture.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT = r'C:\Windows\Fonts\NotoSansKR-VF.ttf'


def swap_rb(im):
    r, g, b, a = im.split()
    return Image.merge('RGBA', (b, g, r, a))


def render_notice(stored_image, spec):
    assert stored_image.size == (2048, 2048)
    assert spec['storage_order'] == 'BGRA'
    original = swap_rb(stored_image)
    arr = np.asarray(original)
    # Reject an unexpected source instead of painting over an unrelated resource.
    vx0, vy0, vx1, vy1 = spec['visible_rect']
    assert np.all(arr[vy0:vy1, vx0:vx1, 3] == 255), 'visible notice must be opaque'
    title = arr[110:230, 700:1200, :3]
    assert ((title[..., 0] > 200) & (title[..., 1] < 20) & (title[..., 2] < 20)).sum() > 1000
    x0, y0, x1, y1 = spec['edit_rect']
    outside = arr.copy()
    outside[y0:y1, x0:x1, :3] = 0
    assert not outside[..., :3].any(), 'unexpected artwork outside notice rectangle'
    out = original.copy()
    dr = ImageDraw.Draw(out)
    dr.rectangle((x0,y0,x1-1,y1-1),fill=(0,0,0,255))
    body = ImageFont.truetype(FONT, spec['font_size'])
    body.set_variation_by_name('Regular')
    heading = ImageFont.truetype(FONT, spec['title_size'])
    heading.set_variation_by_name('Regular')
    cx, cy = spec['title_center']
    title_ko = spec['title_ko']
    title_box = dr.textbbox((cx,cy),title_ko,font=heading,anchor='mm')
    dr.text((cx,cy),title_ko,font=heading,anchor='mm',fill=(255,0,0,255))
    uy=spec['underline_y']
    dr.line((title_box[0],uy,title_box[2],uy),fill=(255,0,0,255),width=3)
    boxes = []
    for paragraph,y in zip(spec['paragraphs_ko'],spec['paragraph_y'],strict=True):
        for line in paragraph.split('\n'):
            xy=(spec['body_x'],y)
            box=dr.textbbox(xy,line,font=body,anchor='lt')
            assert box[0]>=x0 and box[1]>=y0 and box[2]<x1 and box[3]<y1, (line,box)
            dr.text(xy,line,font=body,anchor='lt',fill=(255,255,255,255))
            boxes.append({'text':line,'box':list(box)})
            y+=spec['line_height']
    after=np.asarray(out)
    changed=np.any(arr!=after,axis=2)
    changed[y0:y1,x0:x1]=False
    assert not changed.any(), 'pixels outside notice changed'
    return swap_rb(out), [{'text':title_ko,'body':boxes,'storage_order':'BGRA','outside_rect_changed':0}]
