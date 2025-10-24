def create_error_fingerprint(exc_type, exc_value, tb):
    error_message = str(exc_value).strip()
    error_type = exc_type.__name__
    
    # Network-related errors
    if 'No space left on device' in error_message:
        return ['no-space-left-on-device', error_message]
    
    # Authentication errors
    if 'Proxy check failed' in error_message:
        return ['proxy-check-failed', error_message]
    
    # File system errors
    if 'You have reached your free API requests limit' in error_message:
        return ['api-limit', error_message]
    
    # Default grouping by error type and message
    return ['unknown-error', error_type, error_message]
