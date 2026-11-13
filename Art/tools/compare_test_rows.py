"""Living mud LM4e: every GrandTour.Mud / GrandTour.Snow test row (the log's Snow:, Settle:, Lumps:, Throw:, Variety: lines and
the test results) of two Art/mud_shape_test.ps1 logs, and which rows differ. python Art/tools/compare_test_rows.py before.log after.log"""
import re,sys
def rows(path):
    out=[]
    for line in open(path,encoding='utf-8',errors='replace'):
        m=re.search(r'LogAutomationController: (?:Display: )?((?:Snow|Settle|Lumps|Throw|Variety): .*)',line)
        if m:out.append(m.group(1).strip())
        m=re.search(r'Test Completed\. Result=\{([^}]*)\} Name=\{([^}]*)\} Path=\{([^}]*)\}',line)
        if m:out.append('RESULT %s %s'%(m.group(3),m.group(1)))
    seen=set();uniq=[]
    for r in out:
        if r not in seen:seen.add(r);uniq.append(r)
    return uniq
a=rows(sys.argv[1]);b=rows(sys.argv[2])
sb=set(b);sa=set(a)
print('rows: %d before, %d after; identical %d'%(len(a),len(b),len(sa&sb)))
for r in [x for x in a if x.startswith('RESULT')]:print(r)
changed=[x for x in a if x not in sb]
print('changed rows: %d'%len(changed))
for x in changed:
    key=x[:70];match=[y for y in b if y[:70]==key and y not in sa]
    print('BEFORE: '+x[:600])
    print('AFTER : '+(match[0][:600] if match else '(no row with the same start)'))
for y in [y for y in b if y not in sa and not any(y[:70]==x[:70] for x in changed)]:print('NEW   : '+y[:600])
