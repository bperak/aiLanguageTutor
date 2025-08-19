#!/usr/bin/env python
"""Analyze relationship types in the NetworkX graph"""

import pickle
from collections import defaultdict

# Load NetworkX graph
with open('G_synonyms_2024_09_18.pickle', 'rb') as f:
    g = pickle.load(f)

print("=" * 60)
print("ANALYZING RELATIONSHIP TYPES")
print("=" * 60)

# Collect relationship type info
rel_types = defaultdict(int)
relation_type_values = defaultdict(int)
type_field_values = defaultdict(int)

# Sample edges for each category
samples = {
    'synonym': None,
    'antonym': None,
    'hierarchical': None,
    'other': None
}

for u, v, attrs in g.edges(data=True):
    # Check 'type' field
    if 'type' in attrs:
        type_field_values[attrs['type']] += 1
        
    # Check 'relation_type' field
    if 'relation_type' in attrs:
        relation_type_values[attrs['relation_type']] += 1
    
    # Check for antonym (nested dict or flag)
    if 'antonym' in attrs:
        if isinstance(attrs['antonym'], dict):
            rel_types['antonym_nested_dict'] += 1
            if not samples['antonym']:
                samples['antonym'] = (u, v, attrs)
        elif attrs['antonym'] == True:
            rel_types['antonym_flag_true'] += 1
            if not samples['antonym']:
                samples['antonym'] = (u, v, attrs)
        else:
            rel_types['antonym_flag_false'] += 1
    
    # Check for synonym flag
    if 'synonym' in attrs:
        if attrs['synonym'] == True:
            rel_types['synonym_flag_true'] += 1
            if not samples['synonym']:
                samples['synonym'] = (u, v, attrs)
        else:
            rel_types['synonym_flag_false'] += 1
    
    # Check for hierarchical relations
    if 'relation_type' in attrs:
        rt = attrs['relation_type']
        if rt and isinstance(rt, str) and ('HYPER' in rt or 'HYPO' in rt or 'MERO' in rt or 'HOLO' in rt):
            rel_types['hierarchical'] += 1
            if not samples['hierarchical']:
                samples['hierarchical'] = (u, v, attrs)
    
    # Default synonym (no special markers)
    if 'antonym' not in attrs and 'relation_type' not in attrs:
        rel_types['default_synonym'] += 1
        if not samples['other']:
            samples['other'] = (u, v, attrs)

print("\nRelationship categories found:")
for k, v in sorted(rel_types.items()):
    print(f"  {k}: {v}")

print("\n'type' field values:")
for k, v in sorted(type_field_values.items())[:10]:
    print(f"  {k}: {v}")

print("\n'relation_type' field values:")
for k, v in sorted(relation_type_values.items(), key=lambda x: (str(x[0]), x[1]))[:20]:
    print(f"  {str(k)}: {v}")

print("\n" + "=" * 60)
print("PROPOSED NEO4J RELATIONSHIP MAPPING")
print("=" * 60)

print("""
1. :SYNONYM_OF
   - Default for most edges
   - When 'synonym' flag is true or absent
   - When no 'antonym' dict/flag and no hierarchical relation_type
   
2. :ANTONYM_OF  
   - When 'antonym' dict exists
   - When 'antonym' flag is true
   - When 'type' == 'antonym'
   
3. :DOMAIN_OF (hierarchical)
   - When relation_type contains: HYPERNYM, HYPONYM, MERONYM, HOLONYM
   - TR_HYPERNYM → :DOMAIN_OF with subtype='hypernym'
   - TR_HYPONYM → :DOMAIN_OF with subtype='hyponym'
   - TR_MERONYM → :DOMAIN_OF with subtype='meronym'
   - TR_HOLONYM → :DOMAIN_OF with subtype='holonym'
""")

print("\nSample edges for each type:")
for category, sample in samples.items():
    if sample:
        u, v, attrs = sample
        print(f"\n{category.upper()}: '{u}' -> '{v}'")
        for k, v in list(attrs.items())[:5]:
            if isinstance(v, dict):
                print(f"  {k}: <nested dict with {len(v)} keys>")
            else:
                print(f"  {k}: {v}")

# Count edges by proposed mapping
print("\n" + "=" * 60)
print("EDGE COUNT BY PROPOSED MAPPING")
print("=" * 60)

synonym_count = 0
antonym_count = 0
domain_count = 0

for u, v, attrs in g.edges(data=True):
    # Check for antonym
    if ('antonym' in attrs and (isinstance(attrs['antonym'], dict) or attrs['antonym'] == True)) or \
       ('type' in attrs and attrs['type'] == 'antonym'):
        antonym_count += 1
    # Check for hierarchical
    elif 'relation_type' in attrs and attrs['relation_type'] and \
         isinstance(attrs['relation_type'], str) and \
         any(x in attrs['relation_type'] for x in ['HYPER', 'HYPO', 'MERO', 'HOLO']):
        domain_count += 1
    # Everything else is synonym
    else:
        synonym_count += 1

print(f"  :SYNONYM_OF  {synonym_count:,} edges")
print(f"  :ANTONYM_OF  {antonym_count:,} edges")
print(f"  :DOMAIN_OF   {domain_count:,} edges")
print(f"  TOTAL:       {synonym_count + antonym_count + domain_count:,} edges")
