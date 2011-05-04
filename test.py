#!/usr/bin/python

from openclass import screen

if __name__ == "__main__":
	s = screen.Screen()

	s.capture()
	chunks = s.chunks(quality=50)
	for x, y, size_x, size_y, data in chunks:
		fd = open("img_%d_%d.jpg" % (x, y), "w")
		fd.write(data)
		fd.close()
