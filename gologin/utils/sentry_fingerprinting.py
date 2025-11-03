def create_error_fingerprint(exc_type, exc_value, tb):
    error_message = str(exc_value).strip()
    error_type = exc_type.__name__
    
    # Network-related errors
    if 'No space left on device' in error_message:
        return ['no-space-left-on-device']
    
    # Authentication errors
    if 'Proxy check failed' in error_message:
        return ['proxy-check-failed']
    
    # File system errors
    if 'You have reached your free API requests limit' in error_message:
        return ['api-limit']
    
    # Default grouping by error type and message
    return ['unknown-error']


