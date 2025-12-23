from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Get item from dictionary by key
    
    Usage in template:
        {{ schedule_grid|get_item:staff.id|get_item:day }}
    
    This is equivalent to Python:
        schedule_grid[staff.id][day]
    """
    if dictionary:
        return dictionary.get(key)
    return None