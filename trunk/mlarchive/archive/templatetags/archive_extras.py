from django import template

register = template.Library()

@register.simple_tag
def get_params(params, exclude):
    '''
    This custom template tag takes a dictionary of parameters (requets.GET) and
    a list of keys to exclude and returns a urlencoded string for use in a link
    '''
    
    for key in exclude:
        if key in params:
            params.pop(key)
    
    url = 'test'
    
    return template.defaultfilters.urlencode(url)
    

@register.simple_tag
def get_column(length,count):
    '''
    This custom tag takes two integers, the length of a ordered list and the count of the current
    list item.  It returns col[1-4] to be used as a class to position the item in the 
    correct column.
    '''
    col_length = length / 4
    if count <= col_length:
        return 'col1'
    elif count <= 2 * col_length:
        return 'col2'
    elif count <= 3 * col_length:
        return 'col3'
    else:
        return 'col4'
    
"""
from: http://djangosnippets.org/snippets/1627/

Decorator to facilitate template tag creation
"""
def easy_tag(func):
    """deal with the repetitive parts of parsing template tags"""
    def inner(parser, token):
        #print token
        try:
            return func(*token.split_contents())
        except TypeError:
            raise template.TemplateSyntaxError('Bad arguments for tag "%s"' % token.split_contents()[0])
    inner.__name__ = func.__name__
    inner.__doc__ = inner.__doc__
    return inner

class AppendGetNode(template.Node):
    '''
    This is a custom tag which takes the 
    '''
    def __init__(self, dict):
        self.dict_pairs = {}
        for pair in dict.split(','):
            pair = pair.split('=')
            self.dict_pairs[pair[0]] = template.Variable(pair[1])
            
    def render(self, context):
        # GET is a QueryDict object
        get = context['request'].GET.copy()

        # use this method to replace keys if they already exist.  update() won't replace
        for key in self.dict_pairs:
            get[key] = self.dict_pairs[key].resolve(context)
        
        path = context['request'].META['PATH_INFO']
        
        if len(get):
            path += "?%s" % get.urlencode()
        
        return path

@register.tag()
@easy_tag
def append_to_get(_tag_name, dict):
    return AppendGetNode(dict)
