"""Append an authoring agent's rows file to rules/CATALOG.md (skips keys already present, strips bold)."""
import re, sys
rows=open(sys.argv[1],encoding='utf-8').read()
lines=[l.replace('**','') for l in rows.splitlines() if l.startswith('| `')]
cat=open('rules/CATALOG.md',encoding='utf-8').read().rstrip('\n')
have=set(re.findall(r'^\| `(\w+)`', cat, re.M))
new=[l for l in lines if re.match(r'^\| `(\w+)`', l).group(1) not in have]
open('rules/CATALOG.md','w',encoding='utf-8').write(cat+'\n'+'\n'.join(new)+'\n')
print(f'appended {len(new)} of {len(lines)} rows from {sys.argv[1]}')
