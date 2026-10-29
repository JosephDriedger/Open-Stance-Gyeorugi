from pathlib import Path
p=Path(__file__).with_name('test_belt_single_contact.py')
code=p.read_text().replace('BeltSingleContact','BeltFittedContact').replace('(.008+.027*max','(.005+.013*max')
exec(compile(code,str(p),'exec'))
