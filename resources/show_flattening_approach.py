#!/usr/bin/env python
"""Show how we'll flatten edge attributes for Neo4j"""

import pickle
import json

def flatten_attributes(attrs, prefix=''):
    """
    Flatten nested dictionaries into flat key-value pairs.
    Neo4j can only store primitive types (string, number, boolean) 
    or arrays of primitives.
    """
    flattened = {}
    
    for key, value in attrs.items():
        full_key = f"{prefix}{key}" if prefix else key
        
        if value is None:
            # Skip None values - Neo4j doesn't need them
            continue
            
        elif isinstance(value, (str, int, float, bool)):
            # Primitive types - keep as-is
            flattened[full_key] = value
            
        elif isinstance(value, dict):
            # Nested dict - flatten with prefix
            nested_flat = flatten_attributes(value, prefix=f"{key}_")
            flattened.update(nested_flat)
            
        elif isinstance(value, (list, tuple)):
            # Arrays - only keep if all elements are primitives
            if all(isinstance(item, (str, int, float, bool)) for item in value):
                flattened[full_key] = list(value)
            else:
                # Complex array - convert to JSON string
                flattened[f"{full_key}_json"] = json.dumps(value, ensure_ascii=False)
                
        else:
            # Unknown type - convert to string
            flattened[f"{full_key}_str"] = str(value)
    
    return flattened

# Test with sample NetworkX edge
print("=" * 60)
print("SAMPLE EDGE FLATTENING")
print("=" * 60)

# Load actual graph to show real example
with open('G_synonyms_2024_09_18.pickle', 'rb') as f:
    g = pickle.load(f)

# Find an edge with complex attributes
complex_edge = None
for u, v, attrs in g.edges(data=True):
    # Look for edge with nested attributes
    for key, value in attrs.items():
        if isinstance(value, dict):
            complex_edge = (u, v, attrs)
            break
    if complex_edge:
        break

if complex_edge:
    u, v, original_attrs = complex_edge
    print(f"\nEdge: '{u}' -> '{v}'")
    print("\nORIGINAL attributes:")
    for k, v in original_attrs.items():
        if isinstance(v, dict):
            print(f"  {k}: {type(v).__name__}")
            for sub_k, sub_v in v.items():
                print(f"    {sub_k}: {sub_v}")
        else:
            print(f"  {k}: {v}")
    
    print("\nFLATTENED attributes:")
    flattened = flatten_attributes(original_attrs)
    for k, v in flattened.items():
        print(f"  {k}: {v} (type: {type(v).__name__})")
    
    print("\nCypher-ready check:")
    for k, v in flattened.items():
        if isinstance(v, (str, int, float, bool)):
            print(f"  ✓ {k}: primitive")
        elif isinstance(v, list) and all(isinstance(item, (str, int, float, bool)) for item in v):
            print(f"  ✓ {k}: primitive array")
        else:
            print(f"  ✗ {k}: NEEDS CONVERSION - {type(v)}")
else:
    # Show a regular edge
    sample_edge = list(g.edges(data=True))[0]
    u, v, attrs = sample_edge
    print(f"\nSample edge: '{u}' -> '{v}'")
    print("\nAttributes (already flat):")
    flattened = flatten_attributes(attrs)
    for k, v in flattened.items():
        print(f"  {k}: {v}")
