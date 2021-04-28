from pelican import signals, contents
import os.path
from copy import copy
from itertools import chain

'''
This plugin creates a URL hierarchy for pages that matches the
directory hierarchy of their sources.
'''

class UnexpectedException(Exception): pass

def get_path(page, settings):
    ''' Return the dirname relative to PAGE_PATHS prefix. '''
    path = os.path.split(page.get_relative_source_path())[0] + '/'
    path = path.replace( os.path.sep, '/' )

    try:
        if path and path.index("plugins") > -1:
            return path
    except ValueError:
        # Try to lstrip the longest prefix first
        for prefix in sorted(settings['PAGE_PATHS'], key=len, reverse=True):
            if not prefix.endswith('/'): prefix += '/'
            if path.startswith(prefix):
                return path[len(prefix):-1]
        raise UnexpectedException('Page outside of PAGE_PATHS ?!?')

def in_default_lang(page):
    # page.in_default_lang property is undocumented (=unstable) interface
    return page.lang == page.settings['DEFAULT_LANG']

def override_metadata(content_object):
    if type(content_object) is not contents.Page:
        return

    #ignore include files
    if not hasattr(content_object, 'slug'):
        return

    page = content_object
    path = get_path(page, page.settings)

    fullpath = os.path.split(page.get_relative_source_path())[0]

    #add images static paths automatically
    page.settings['STATIC_PATHS'].append(path + "/images")


    #print(page)


    def _override_value(page, key):
        metadata = copy(page.metadata)
        # We override the slug to include the path up to the filename
        metadata['slug'] = os.path.join(path, page.slug)
        # We have to account for non-default language and format either,
        # e.g., PAGE_SAVE_AS or PAGE_LANG_SAVE_AS
        infix = '' if in_default_lang(page) else 'LANG_'
        return page.settings['PAGE_' + infix + key.upper()].format(**metadata)

    for key in ('save_as', 'url'):
        #print( _override_value(page, key))
        if not hasattr(page, 'override_' + key):
            setattr(page, 'override_' + key, _override_value(page, key))

    #print("page")
    #print(page.metadata)

def set_relationships(generator):
    
    def _all_pages():
        return chain(generator.pages, generator.translations)

    # initialize parents and children lists
    for page in _all_pages():
        page.parent = None
        page.parents = []
        page.children = []

    # set immediate parents and children
    for page in _all_pages():
        #print(page.url)
        # Parent of /a/b/ is /a/, parent of /a/b.html is /a/
        parent_url = os.path.dirname(page.url[:-1])
        if parent_url: parent_url += '/'
        for page2 in _all_pages():
            if page2.url == parent_url and page2 != page:
                page.parent = page2
            
                if page.settings['PAGE_INHERIT_METADATA_LIST'] is not None:
                    _inheritMetadata(page)

                page2.children.append(page)
        # If no parent found, try the parent of the default language page
        if not page.parent and not in_default_lang(page):
            for page2 in generator.pages:
                if (page.slug == page2.slug and
                    os.path.dirname(page.source_path) ==
                    os.path.dirname(page2.source_path)):
                    # Only set the parent but not the children, obviously
                    page.parent = page2.parent

    # set all parents (ancestors)
    for page in _all_pages():
        p = page
        #print(p)
        while p.parent:
            page.parents.insert(0, p.parent)
            p = p.parent

def _inheritMetadata(child):

    parent = child.parent

    for key, value in parent.metadata.items():
        if key not in child.metadata and (key in child.settings['PAGE_INHERIT_METADATA_LIST']):
            child.metadata[key] = value

    #print(child.metadata)

def page_context(generator, content):
    #print(generator.pages)
    #print("page2")
    #print(content.parent)

    page = content

    if page.settings['PAGE_INHERIT_METADATA_LIST'] is not None and page.parent is not None:
        _inheritMetadata(page)

def register():
    #signals.page_generator_write_page.connect(page_context)
    signals.content_object_init.connect(override_metadata)
    signals.page_generator_finalized.connect(set_relationships)
