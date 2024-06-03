from img2table.document import Image

# Instantiation of the image
img = Image(src=r"raw_images/Городницкая Я.М. ИП_193_сч 193 ИП Городницкая Я.М. от 25.03.2024 - СБТ0001-1.jpg")

# Table identification
img_tables = img.extract_tables()

# Result of table identification
print(img_tables)

print(img_tables[0])