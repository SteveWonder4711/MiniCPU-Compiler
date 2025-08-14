from PIL import Image
import sys



palette = [
    0,  0,  0,
    0,  85, 0,
    0,  170,0,
    0,  255,0,
    255,0,  0,
    255,85, 0,
    255,170,0,
    255,255,0,
    0,  0,  255,
    0,  85, 255,
    0,  170,255,
    0,  255,255,
    255,0,  255,
    255,85, 255,
    255,170,255,
    255,255,255
]

packedpalette = []

for i in range(len(palette), 3):
    packedpalette.append((palette[i], palette[i+1], palette[i+2]))


img = Image.open(sys.argv[1])

p_img = Image.new('P', (16, 16))
p_img.putpalette(palette * 16)

conv = img.quantize(palette=p_img)
conv.show()

colorlist = []
out = "pointer image inline "

width, height = conv.size
for x in range(width):
    for y in range(height):
        colorlist.append(conv.getpixel((x,y)))

for i in range(0,len(colorlist),4):
    out += f"{hex(colorlist[i+3] + colorlist[i+2]*16 + colorlist[i+1]*16*16 + colorlist[i]*16*16*16)}; "
            
with open("temp", "w") as outfile:
    outfile.write(out.strip("; ")+"\n")
