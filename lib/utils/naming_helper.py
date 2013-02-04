__author__ = 'sfaci'
import sys
import unittest

##Source:   http://wiki.geany.org/howtos/convert_camelcase
#----------------------------------------------------------------------
def camel_case_to_lower_case_underscore(string):
    """
    Split string by upper case letters.

    F.e. useful to convert camel case strings to underscore separated ones.

    @return words (list)
    """
    words = []
    from_char_position = 0
    for current_char_position, char in enumerate(string):
        if char.isupper() and from_char_position < current_char_position:
            words.append(string[from_char_position:current_char_position].lower())
            from_char_position = current_char_position
    words.append(string[from_char_position:].lower())
    return '_'.join(words)


#----------------------------------------------------------------------
def lower_case_underscore_to_camel_case(string):
    """Convert string or unicode from lower-case underscore to camel-case"""
    splitted_string = string.split('_')
    # use string's class to work on the string to keep its type
    class_ = string.__class__
    return splitted_string[0] + class_.join('', map(class_.capitalize, splitted_string[1:]))


def cap_convert(string):
    result = convert(string)
    return result[0].upper() + result[1:]


def convert(string):
    method = detect_conversion_method(string)
    return method(string)

#----------------------------------------------------------------------
def detect_conversion_method(data):
    if '_' in data:
        return lower_case_underscore_to_camel_case
    else:
        return camel_case_to_lower_case_underscore


