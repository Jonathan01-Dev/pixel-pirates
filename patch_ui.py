import sys

with open(r'c:\wamp64\www\pixel-pirates\src\web_ui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if line.startswith('HTML = r"""<!DOCTYPE html>'):
        skip = True
        new_lines.append('''def get_html():\n''')
        new_lines.append('''    try:\n''')
        new_lines.append('''        with open(r"c:\\wamp64\\www\\pixel-pirates\\src\\archipel_ui.html", "r", encoding="utf-8") as html_f:\n''')
        new_lines.append('''            return html_f.read()\n''')
        new_lines.append('''    except Exception as e:\n''')
        new_lines.append('''        return f"<h1>Error loading UI: {e}</h1>"\n\n''')
        continue
    
    if skip and line.startswith('</html>"""'):
        skip = False
        continue
        
    if not skip:
        if 'body = HTML.encode()' in line:
            new_lines.append(line.replace('HTML.encode()', 'get_html().encode("utf-8")'))
        elif 'self.wfile.write(HTML.encode("utf-8"))' in line:
            new_lines.append(line.replace('HTML.encode("utf-8")', 'get_html().encode("utf-8")'))
        else:
            new_lines.append(line)

with open(r'c:\wamp64\www\pixel-pirates\src\web_ui.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("PATCH APPLIED")
