# 6. core/export.py
with open('src/core/export.py', 'r') as f: content = f.read()
content = content.replace('Environment(loader=FileSystemLoader(self.template_dir))', 'None')
content = content.replace('print(f"Export Error: {e}")', 'import logging\n            logging.exception("Export failed in export function")')
with open('src/core/export.py', 'w') as f: f.write(content)

# 7. core/parser.py
with open('src/core/parser.py', 'r') as f: content = f.read()
content = content.replace('''        for res in result:
            if res['type'] == 'text':
                markdown_content += res['res'][0]['text'] + "\\n"''', '''        for res in result:
            if isinstance(res, dict) and res.get('type') == 'text' and isinstance(res.get('res'), list) and len(res['res']) > 0 and 'text' in res['res'][0]:
                markdown_content += res['res'][0]['text'] + "\\n"''')
with open('src/core/parser.py', 'w') as f: f.write(content)
