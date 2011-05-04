#!/usr/bin/python
"""Screen capturing and processing module"""

from gtk import gdk

class Screen:
    """Screen capturing class"""
    def __init__(self, width=None, height=None):
        if not width:
            width = gdk.screen_width()
        self.width = width
        if not height:
            height = gdk.screen_height()
            self.height = height

    def capture(self, scale_x=None, scale_y=None, quality=75, raw=False):
        """Captures a screenshot and returns in for width, height, data"""

        screenshot = gdk.Pixbuf(gdk.COLORSPACE_RGB, False, 8, self.width, self.height)
        screenshot.get_from_drawable(gdk.get_default_root_window(),
                                    gdk.colormap_get_system(),
                                    0, 0, 0, 0,
                                    self.width, self.height)

        if not scale_x:
            scale_x = self.width
        if not scale_y:
            scale_y = self.height
        if self.width != scale_x or self.height != scale_y:
            screenshot = screenshot.scale_simple(scale_x, scale_y, gdk.INTERP_BILINEAR)

        if raw:
            return scale_x, scale_y, screenshot
        else:
            image=[]
            screenshot.save_to_callback(lambda buf, image: image.append(buf), "jpeg", {"quality": str(quality)}, image)
            return scale_x, scale_y, "".join(image)

    def chunks(self, chunks_x=4, chunks_y=4, quality=75):
        """Captures a screenshot and converts it into a serie of smaller shots"""

        width, height, image = self.capture(raw=True)

        step_x = width / chunks_x
        step_y = height / chunks_y

        chunks=[]

        print "%d %d" % (width, height)
        for y in range(chunks_y):
            pos_y = y * step_y
            for x in range(chunks_x):
                pos_x = x * step_x

                chunk = image.subpixbuf(pos_x, pos_y, step_x, step_y)
                img = []
                chunk.save_to_callback(lambda buf, img: img.append(buf), "jpeg", {"quality": str(quality)}, img)
                chunks.append((pos_x, pos_y, step_x, step_y, "".join(img)))
        return chunks
