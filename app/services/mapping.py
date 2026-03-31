import json

MAPPING_RULES = {
    "Booking": ["Passenger Details", "Payment", "Flight Selection"],
    "Manage Booking": ["Cancellation", "Reschedule", "Refund"]
}

def map_jira_to_module_feature(issue_data):
    """
    Simulates mapping Jira components or labels to a system module/feature.
    """
    components = [c.get('name') for c in issue_data.get('fields', {}).get('components', [])]
    
    # Try to map based on first matched component
    for component in components:
        for module, features in MAPPING_RULES.items():
            if component in features:
                return module, component
    
    # Default fallback
    return "Unknown Module", "Unknown Feature"
