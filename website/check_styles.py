import re
html = open(r'C:\Users\Dell\mod\website\formatted_nova.html', encoding='utf-8').read()
styles = re.findall(r'style=\"(.*?)\"', html)
print(f"Total inline styles: {len(styles)}")
for s in styles[:10]:
    print(s)
