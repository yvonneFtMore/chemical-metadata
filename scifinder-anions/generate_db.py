#! /home/caleb/.anaconda3/bin/python
import sys

import rdkit
from rdkit import Chem
from rdkit.Chem import Descriptors, inchi
from rdkit.Chem.rdMolDescriptors import CalcMolFormula
from pubchempy import get_compounds, Compound
import json
from collections import Counter

syn_data = open('Good synoynms by CAS.json').read()
syn_data = json.loads(syn_data)

all_user_names = []
for CAS, d in syn_data.items():
    if 'synonyms' in d:
        all_user_names.extend(d['synonyms'])
all_user_names = set(all_user_names)



pdf_data = open('Parsed scifinder metadata.json').read()
pdf_data = json.loads(pdf_data)

all_names = []
for CAS, d in pdf_data.items():
    if 'Other Names' in d:
        all_names.extend(d['Other Names'])
    if 'Name' in d:
        all_names.append(d['Name'])
    if 'Deleted CAS' in d:
        all_names.extend(d['Deleted CAS'])
    if 'Alternate CAS' in d:
        all_names.extend(d['Alternate CAS'])
    all_names.append(CAS)
dup_names =  [item for item, count in Counter(all_names).items() if count > 1]
all_names = set(all_names)

failed_mol = set(['11062-77-4',# No charge
                  ])

arg = sys.argv[0:]
arg.pop(0)
for f in arg:
    try:
        mol = Chem.MolFromMolFile(f)
        assert mol is not None
    except:
        print('Cannot read ', f)
        continue
    try:
        inchi_val = inchi.MolToInchi(mol)
    except:
        print('BAILING ON', f)
        continue
    
    mol = inchi.MolFromInchi(inchi_val) # Works better for ions
    if mol is None:
        print('BAILING ON %s'%f)
        continue
    smi = Chem.MolToSmiles(mol, True)
    inchi_val = inchi.MolToInchi(mol)
    inchikey = inchi.InchiToInchiKey(inchi_val)
    mw = Descriptors.MolWt(mol)
    formula = CalcMolFormula(mol)
    CAS = f.split('/')[1] if '/' in f else f
    CAS = CAS.split('.')[0]
    
    try:
        pc = get_compounds(inchikey, 'inchikey')[0]
        cid = pc.cid
        iupac_name = pc.iupac_name
        names = pc.synonyms
    except:
        cid = -1
        iupac_name = ''
        names = ['']
    
    other_CAS = []
    if CAS in pdf_data:
        d = pdf_data[CAS]
        name = d['Name']
        if 'Other Names' in d:
            syns = d['Other Names']
        else:
            syns = []
        if not iupac_name:
            iupac_name = name
        else:
            syns.insert(0, name)
        if 'Deleted CAS' in d:
            other_CAS.extend(d['Deleted CAS'])
        if 'Alternate CAS' in d:
            other_CAS.extend(d['Alternate CAS'])
            
        syns = [i for i in syns if i not in dup_names]
        names =  syns + [i for i in names if i not in all_names] + other_CAS
    actual_names = []
    for name in names:
        if name in all_user_names:
            # If the name is in the user db, only add it if it corresponds to this CAS number
            if CAS in syn_data and 'synonyms' in syn_data[CAS] and name in syn_data[CAS]['synonyms']:
                actual_names.append(name)
            else:
                # Discard it otherwise
                pass
        else:
            # If the name is not in the user db we're all good
            actual_names.append(name)
    if CAS in syn_data and 'synonyms' in syn_data[CAS]:
        # If the user has any syns for this cas number, add those names if the name hasn't already been aded
        for n in syn_data[CAS]['synonyms']:
            if n not in actual_names:
                actual_names.append(n)

    actual_names = [i for i in actual_names if i]
    s = '%d\t%s\t%s\t%g\t%s\t%s\t%s\t%s\t' %(cid, CAS, formula, mw, smi, inchi_val, inchikey, iupac_name)
    
    
    s += '\t'.join(actual_names)
    print(s)