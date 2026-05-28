import json

def load_schema(schema_path: str) -> dict:
    with open(schema_path,'r') as f:
        return json.load(f)
    

def validate_query(query : str, schema : dict) -> dict:
    if not query.strip():
        return {'is_valid': False, 'error': 'Query is empty'}
    
    for table in schema['tables']:
        if table['name'].lower() in query.lower():
            return {'is_valid': True, 'error': ''}
    
    return {'is_valid': False, 'error': 'No matching tables found'}