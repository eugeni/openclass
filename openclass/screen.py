#!/usr/bin/python
"""Screen capturing and processing module"""

from gtk import gdk

class Screen:
    """Screen capturing class"""
    def __init__(self, width=None, height=None, target_width=None, target_height=None):
        if not width:
            width = gdk.screen_width()
        self.width = width
        if not height:
            height = gdk.screen_height()
            self.height = height

        if not target_width:
            target_width = 800
        self.target_width = target_width
        if not target_height:
            target_height = 480
        self.target_height = target_height

    def capture(self):
        """Captures a screenshot"""

        screenshot = gdk.Pixbuf(gdk.COLORSPACE_RGB, False, 8, self.width, self.height)
        screenshot.get_from_drawable(gdk.get_default_root_window(),
                                    gdk.colormap_get_system(),
                                    0, 0, 0, 0,
                                    self.width, self.height)
        if self.width != self.target_width or self.height != self.target_height:
            screenshot = screenshot.scale_simple(self.target_width, self.target_height, gdk.INTERP_BILINEAR)

        # process screenshot
        # screenshot.save_to_callback(...)
        sp = screenshot.subpixbuf(0, 0, 320, 240)
        screenshot.save("tela.jpg", "jpeg", {"quality": "75"})
        sp.save("sp.jpg", "jpeg", {"quality": "75"})
        print screenshot.get_pixels().__hash__()
        s2 = screenshot.copy()
        print s2.get_pixels().__hash__()
        print sp.get_pixels().__hash__()
        #data = screenshot.get_pixels()

        # vamos tentar carregar agora
        data = open("sp.jpg").read()
        loader = gdk.PixbufLoader(image_type="jpeg")
        loader.write(data)
        loader.close()
        pb = loader.get_pixbuf()
        pb.save("sp2.jpg", "jpeg", {"quality": "30"})
