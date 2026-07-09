import urllib.request, re
req = urllib.request.Request('https://klipy.com/gifs/atomic-bomb-explosion-6', headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')
print(re.findall(r'https://[^\"\'\s]+\.gif', html))

