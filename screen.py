#!/usr/bin/python

from gtk import gdk

width = gdk.screen_width()
height = gdk.screen_height()

target_width = 800
target_height = 480

screenshot = gdk.Pixbuf(gdk.COLORSPACE_RGB, False, 8, width, height)
screenshot.get_from_drawable(gdk.get_default_root_window(),
                            gdk.colormap_get_system(),
                            0, 0, 0, 0,
                            width, height)
if width != target_width or height != target_height:
    screenshot = screenshot.scale_simple(target_width, target_height, gdk.INTERP_BILINEAR)
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
