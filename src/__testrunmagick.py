import os

command = r"""
magick convert X:\Transfer\1\z.jpg -colorspace Gray X:\Transfer\1\z1.jpg
"""
print(os.system(command))