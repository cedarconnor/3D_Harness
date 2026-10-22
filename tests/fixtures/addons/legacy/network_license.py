bl_info = {'name':'Unavailable network license fixture', 'version':(1, 0, 0), 'blender':(5, 1, 0),
           'dcc_harness':{'network':'required', 'license_required':True, 'dependencies':[]}}

def register():
    raise RuntimeError('This fixture has no offline license configuration')

def unregister():
    pass
