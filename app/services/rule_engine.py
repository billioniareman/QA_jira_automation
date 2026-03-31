import re

VALIDATION_KEYWORDS = ['valid', 'format', 'empty', 'required']

def extract_rules(acceptance_criteria: str):
    """
    Extracts structured rules from acceptance criteria text.
    Returns a list of dicts representing rules.
    """
    if not acceptance_criteria:
        return []
        
    rules = []
    
    # Split by new lines or basic punctuation to get sentences/bullet points
    sentences = re.split(r'\n|\. ', acceptance_criteria)
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # Check rule keywords
        if any(keyword in sentence.lower() for keyword in ['must', 'should', 'required', 'cannot', 'only allowed']):
            rule_type = 'business'
            if any(vk in sentence.lower() for vk in VALIDATION_KEYWORDS):
                rule_type = 'validation'
                
            rules.append({
                'rule_text': sentence,
                'rule_type': rule_type,
                'source_type': 'jira',
                'verification_status': 'verified',
                'confidence': 0.9
            })
            
    return rules
