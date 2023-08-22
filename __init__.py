# SPDX-License-Identifier: GPL-2.0-or-later

bl_info = {
    "name": "Apply shapekeyed modifier",
    "description": "Select modifier to apply on object with shapekeys",
    "author": "Samuel Bernou, Christophe Seux, Manuel Rais",
    "version": (1, 0, 1),
    "blender": (2, 8, 0),
    "location": "properties > mesh > shapekey > submenu",
    "warning": "",
    "wiki_url": "",
    "category": "Object" }

import bpy
import mathutils

C = bpy.context
D = bpy.data


def CopyAll(Root, destZone):
    '''copy all attribute value from src to dest'''
    for attr in dir(Root):
        if not attr.startswith('__')  and attr not in ['bl_rna','identifier','name_property','rna_type','properties']:
            try:
                value = getattr(Root,attr)
            except AttributeError:
                value = None
            if value != None:
                if not callable(value):
                    try:
                        # print (attr, value)
                        setattr(destZone, attr, value)
                        ### exec('destZone.%s = value'%(attr))
                        #if getattr(destZone, attr) != value:
                            # print('DIFFERENCE:', attr, value, '>>', getattr(destZone, attr))
                    except(AttributeError):
                        # print("Unchanged(readOnly)>>", Root, attr, value)
                        pass


def driverCopy(src, dest):
    '''Take src mesh and apply all drivers in shapekeys of dest mesh'''
    dest = dest.data
    for d in src.shape_keys.animation_data.drivers:
        shapeName = d.data_path.split('"')[1]
        if dest.shape_keys.key_blocks.get(shapeName): #test if shapekey exist in dest ###shapeName in [kb.name for kb in dest.shape_keys.key_blocks]
            ##create driver in dest
            nd = dest.shape_keys.driver_add(d.data_path)
            
            if nd.modifiers:
                ##clean modifier
                for modifier in nd.modifiers :
                    nd.modifiers.remove(modifier)

                ##create modifier
                for modifier in d.modifiers :
                    mod = nd.modifiers.new(modifier.type)

                    ##copy modifier values
                    CopyAll(modifier, mod)
                    mod.blend_in = modifier.blend_in
                    mod.blend_out = modifier.blend_out
            
            
            ##copy fCurve settings
            if d.keyframe_points:
                for i, kp, in enumerate(d.keyframe_points):
                    nd.keyframe_points.add()
                    CopyAll(kp, nd.keyframe_points[i])

            ##copy variable
            if d.driver.variables:
                for var in d.driver.variables:
                    v = nd.driver.variables.new()
                    CopyAll(var,v)

                    ##copy targets in variable
                    for i, t in enumerate(var.targets):
                        CopyAll(t,v.targets[i])

            ##copy settings
            CopyAll(d,nd)
            CopyAll(d.driver,nd.driver)


        else:
            print (d.name, "wasn't found in", dest.name, 'shapekeys')


def oneMeshPerShapekey(obj, modifiersToBake):
    '''
    take an object and a list of modifiers to apply
    tomesh'it to one mesh per shakepeys
    return the list of generated mesh
    '''
    modState = {}
    shapeState = {}
    meshList = []

    if obj.data.shape_keys:
        for m in obj.modifiers:
            modState[m.name] = m.show_viewport
            if m.name in modifiersToBake:
                m.show_viewport = True
                m.show_render = True

            else:
                m.show_viewport = False
                m.show_render = False

        blocks = obj.data.shape_keys.key_blocks
        for s in blocks:
            shapeState[s.name] = s.value
            
        for s in blocks:
            for shape in blocks: #set each value to 0
                shape.value = 0
            s.value = 1 #set current value to one

            ##ToMesh with current state
            copy = obj.to_mesh(scene = bpy.context.scene, apply_modifiers = True, settings = 'RENDER') #PREVIEW Apply modifier preview settings. RENDER Apply modifier render settings.
            
            ##Store object and name in a list of list #dict: {shapekey-name : object}

            # copy.name = 'meshKey_' + s.name
            meshList.append([s.name, copy])

        ##restore original value
        for m in obj.modifiers:
            m.show_viewport = modState[m.name]
        for s in blocks[1:]:
            s.value = shapeState[s.name]

        return (meshList)

    else:
        print (obj.name, 'has no shapekeys')
        return (None)


def reshape(obj, modifiersToBake, meshKeys):
    '''
    Get the object, the list of modifier to apply and double list of meshKeys [[shapename, mesh],...]
    and reassign shapekeys to object according to meshKeys
    '''

    ##remove modifiers from original object
    for modifiersName in modifiersToBake:
        obj.modifiers.remove(obj.modifiers[modifiersName])

    ##apply new shapekey from meshKeys to 'basis' mesh
    basis = meshKeys[0][1] #mesh equivalent to basis
    originalMesh = obj.data
    originalName = originalMesh.name

    ##replace mesh in object by the basis
    obj.data = basis

    ##create all shapekeys
    obj.shape_key_add('Basis')
    for mk in meshKeys: #mk[0] = shapekey name, mk[1] = mesh
        if 'Basis' in mk[0]:
            pass ##don't take Basis shapekey
        else:
            print(mk[0])
            name = mk[0]
            obj.shape_key_add(name) #active ?
            for i, v in enumerate(obj.data.shape_keys.key_blocks[name].data): #for vertex coordinates in shapekey
                v.co = mk[1].vertices[i].co #apply vertex coordinate of meshKey

    ##get ShapeKey value from previous mesh
    for kb in originalMesh.shape_keys.key_blocks:
        #obj.data.shape_keys.key_blocks[kb.name].value = kb.value
        
        CopyAll(kb, obj.data.shape_keys.key_blocks[kb.name])
        # copyAttr(kb, obj.data.shape_keys.key_blocks[kb.name])

    ##test if driver exist in original Mesh
    animData = originalMesh.shape_keys.animation_data
    if animData:
        if animData.drivers:
            ##save driver and reapply it to copy
            driverCopy(originalMesh, obj)

    ##rename according to original mesh
    originalMesh.name = originalMesh.name + '_old'
    obj.data.name = originalName

    ##clear meshKeys and list
    for m in meshKeys:
        if m[1].users > 0: #basis mesh is used by the object
            pass ##don't delete Basis shapekey
        else:
            bpy.data.meshes.remove(m[1])

    del meshKeys #delete list


###----OPERATOR---

def object_invoke_func(self, context, event):
    wm = context.window_manager
    wm.invoke_props_dialog(self)
    return {'RUNNING_MODAL'}

class SelectObjectModifiers(bpy.types.Operator):
    '''Copy Chosen modifiers from active to selected'''
    bl_idname = "shapekeys.apply_selected_modifiers"
    bl_label = "Apply Selected Modifiers"
    selection = bpy.props.BoolVectorProperty(size=32, options={'SKIP_SAVE'})

    # poll = object_poll_func
    invoke = object_invoke_func

    def draw(self, context):
        layout = self.layout
        for idx, const in enumerate(context.active_object.modifiers):
            layout.prop(self, 'selection', index=idx, text=const.name,
               toggle=True)

    def execute(self, context):
        active = context.active_object
        ob = active
        modifiersToBake = []
        for index, flag in enumerate(self.selection):
            # print ('index:', index, 'Flag', flag)
            if flag:
                modifiersToBake.append(active.modifiers[index].name)

        if modifiersToBake:
            meshKeys = oneMeshPerShapekey(ob, modifiersToBake)
            if meshKeys:
                reshape(ob, modifiersToBake, meshKeys)
            else:
                self.report({'INFO'}, "No shapekeys")
        
        else:
            ##no modifiers selected - do nothing
            pass

        return{'FINISHED'}


def ApplyShapeKeyedModPanel(self,context):
    '''Path operations'''
    layout = self.layout
    layout.operator('shapekeys.apply_selected_modifiers', text = "Apply modifiers", icon = 'MODIFIER')


###----REGISTER---

def register():
    bpy.utils.register_module(__name__)
    bpy.types.MESH_MT_shape_key_context_menu.append(ApplyShapeKeyedModPanel) # DATA_PT_shape_keys
    # bpy.types.DATA_PT_shape_keys.append(ApplyShapeKeyedModPanel) # DATA_PT_shape_keys

def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.MESH_MT_shape_key_context_menu.remove(ApplyShapeKeyedModPanel)
    # bpy.types.DATA_PT_shape_keys.remove(ApplyShapeKeyedModPanel)

if __name__ == "__main__":
    register()