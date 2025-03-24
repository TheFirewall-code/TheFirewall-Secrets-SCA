def mask_string(s: str) -> str:
    # If the string is shorter than or equal to 5 characters, no masking is
    # needed
    if len(s) <= 5:
        return s
    # Show the first 5 characters and replace the rest with 'x'
    return s[:5] + 'x' * (len(s) - 5)
