import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Pattern matches:
# { category: "...", icon: "...", name: "...", location: "...", distance: "...", desc: "..." }image: "URL", icon: "...", NAMElocation: "...", distance: "...", desc: "..." },
pattern = r'\{ category: "(.*?)", icon: "(.*?)", name: "(.*?)", location: "(.*?)", distance: "(.*?)", desc: "(.*?)" \}image: "(.*?)", icon: ".*?", .*?location: ".*?", distance: ".*?", desc: ".*?" \},'

def fix_match(m):
    category = m.group(1)
    icon = m.group(2)
    name = m.group(3)
    location = m.group(4)
    distance = m.group(5)
    desc = m.group(6)
    image = m.group(7)
    return f'{{ category: "{category}", image: "{image}", icon: "{icon}", name: "{name}", location: "{location}", distance: "{distance}", desc: "{desc}" }},'

fixed_html = re.sub(pattern, fix_match, html)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(fixed_html)

print("Fixed")
