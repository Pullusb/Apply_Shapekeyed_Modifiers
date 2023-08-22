# SPDX-License-Identifier: GPL-2.0-or-later

bl_info = {
    "name": "Apply Shapekeyed Modifier",
    "description": "Select modifier to apply on object with shapekeys",
    "author": "Samuel Bernou, Christophe Seux, Manuel Rais",
    "version": (1, 0, 1),
    "blender": (3, 0, 0),
    "location": "properties > mesh > shapekey > submenu",
    "category": "Object"
}

import bpy
import mathutils

C = bpy.context
D = bpy.data

def CopyAll(Root, destZone):
    '''Copy all attribute value from src to dest'''
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
            ## create driver in dest
            nd = dest.shape_keys.driver_add(d.data_path)
            
            if nd.modifiers:
                ## clean modifier
                for modifier in nd.modifiers :
                    nd.modifiers.remove(modifier)

                ## create modifier
                for modifier in d.modifiers :
                    mod = nd.modifiers.new(modifier.type)

                    ## copy modifier values
                    CopyAll(modifier, mod)
                    mod.blend_in = modifier.blend_in
                    mod.blend_out = modifier.blend_out
            
            
            ## copy fCurve settings
            if d.keyframe_points:
                for i, kp, in enumerate(d.keyframe_points):
                    nd.keyframe_points.add()
                    CopyAll(kp, nd.keyframe_points[i])

            ## copy variable
            if d.driver.variables:
                for var in d.driver.variables:
                    v = nd.driver.variables.new()
                    CopyAll(var,v)

                    ## copy targets in variable
                    for i, t in enumerate(var.targets):
                        CopyAll(t,v.targets[i])

            ## copy settings
            CopyAll(d,nd)
            CopyAll(d.driver,nd.driver)


        else:
            print (d.name, "wasn't found in", dest.name, 'shapekeys')


def oneMeshPerShapekey(obj, modifiersToBake):
    '''Take an object and a list of modifiers to apply
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
            init_val = s.value
            s.value = 1 #set current value to one

            ## ToMesh with current state
            ## Using copy because mesh becomes invalid afte rbeing passed to reshape
            
            # dg = bpy.context.evaluated_depsgraph_get()
            # copy = obj.to_mesh(preserve_all_data_layers=True, depsgraph=dg).copy()

            copy = obj.to_mesh(preserve_all_data_layers=False)
            meshList.append([s.name, [v.co for v in copy.vertices], init_val])
            #meshList.append([s.name, copy])

        ## restore original value
        for m in obj.modifiers:
            m.show_viewport = modState[m.name]
        for s in blocks[1:]:
            s.value = shapeState[s.name]
        
        return meshList

    else:
        print (obj.name, 'has no shapekeys')
        return


def reshape(obj, modifiersToBake, meshKeys):
    '''
    Get the object, the list of modifier to apply and double list of meshKeys [[shapename, mesh],...]
    and reassign shapekeys to object according to meshKeys
    '''

    ## Here mesh data are invalid
    ## remove modifiers from original object
    for modifiersName in modifiersToBake:
        obj.modifiers.remove(obj.modifiers[modifiersName])

    ## apply new shapekey from meshKeys to 'basis' mesh
    basis = meshKeys[0][1] # mesh equivalent to basis
    originalMesh = obj.data
    originalName = originalMesh.name

    ## replace mesh in object by the basis
    # obj.data = basis

    ## create all shapekeys
    obj.shape_key_clear() # Clear (key block are still there)

    obj.shape_key_add(name='Basis')
    for mk in meshKeys: # mk[0] = shapekey name, mk[1] = mesh
        if 'Basis' in mk[0]:
            continue
        
        name = mk[0]
        print('create key:', name)
        obj.shape_key_add(name=name)

        key = obj.data.shape_keys.key_blocks[name]
        key.value = mk[2]
        for i, v in enumerate(key.data): # for vertex coordinates in shapekey
            # v.co = mk[1].vertices[i].co # Apply vertex coordinate of meshKey
            v.co = mk[1][i] # Apply vertex coordinate of meshKey
        # key.value = mk[2]

    ## get ShapeKey value from previous mesh
    for kb in originalMesh.shape_keys.key_blocks:
        #obj.data.shape_keys.key_blocks[kb.name].value = kb.value
        
        CopyAll(kb, obj.data.shape_keys.key_blocks[kb.name])
        # copyAttr(kb, obj.data.shape_keys.key_blocks[kb.name])

    ## test if driver exist in original Mesh
    animData = originalMesh.shape_keys.animation_data
    if animData:
        if animData.drivers:
            ## save driver and reapply it to copy
            driverCopy(originalMesh, obj)

    ## rename according to original mesh
    originalMesh.name = originalMesh.name + '_old'
    obj.data.name = originalName

    ## clear meshKeys and list
    # for m in meshKeys:
    #     # m[1].use_fake_user = False

    #     if m[1].users > 0: # basis mesh is used by the object
    #         pass ## don't delete Basis shapekey
    #     else:
    #         bpy.data.meshes.remove(m[1])

    del meshKeys # delete list


###----OPERATOR---

# def object_invoke_func(self, context, event):
#     wm = context.window_manager
#     wm.invoke_props_dialog(self)
#     return {'RUNNING_MODAL'}

class APSHAPE_OT_apply_selected_modifiers_with_shapekey(bpy.types.Operator):
    bl_idname = "apshape.apply_selected_modifiers_with_shapekey"
    bl_label = "Apply Selected Modifiers"
    bl_description = "Copy Chosen modifiers from active to selected"
    bl_options = {"REGISTER", "UNDO"}
    
    selection : bpy.props.BoolVectorProperty(size=32, options={'SKIP_SAVE'})

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        for idx, const in enumerate(context.active_object.modifiers):
            layout.prop(self, 'selection', index=idx, text=const.name,
               toggle=True)

    def execute(self, context):
        ob = context.object
        modifiersToBake = []
        for index, flag in enumerate(self.selection):
            # print ('index:', index, 'Flag', flag)
            if flag:
                modifiersToBake.append(ob.modifiers[index].name)

        if modifiersToBake:
            meshKeys = oneMeshPerShapekey(ob, modifiersToBake)
            ## Here mesh data are valid
            if meshKeys:
                reshape(ob, modifiersToBake, meshKeys)
            else:
                self.report({'INFO'}, "No shapekeys")
        
        else:
            ## no modifiers selected - do nothing
            self.report({'WARNING'}, "No modifiers to apply")
            pass

        return {'FINISHED'}


def apply_shape_keyed_mod_panel(self, context):
    '''Path operations'''
    layout = self.layout
    layout.label(text='Test')
    layout.operator('apshape.apply_selected_modifiers_with_shapekey', text = "Apply Modifiers", icon = 'MODIFIER')

###----REGISTER---

def register():
    bpy.utils.register_class(APSHAPE_OT_apply_selected_modifiers_with_shapekey)
    bpy.types.MESH_MT_shape_key_context_menu.append(apply_shape_keyed_mod_panel)
    # bpy.types.DATA_PT_shape_keys.append(apply_shape_keyed_mod_panel) # DATA_PT_shape_keys

def unregister():
    bpy.utils.unregister_class(APSHAPE_OT_apply_selected_modifiers_with_shapekey)
    bpy.types.MESH_MT_shape_key_context_menu.remove(apply_shape_keyed_mod_panel)
    # bpy.types.DATA_PT_shape_keys.remove(apply_shape_keyed_mod_panel)

if __name__ == "__main__":
    register()
