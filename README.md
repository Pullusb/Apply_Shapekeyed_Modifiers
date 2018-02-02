# Apply Shapekeyed modifier

Apply Selected modifiers even if there is shapekey on the mesh  
  
**[Download latest](https://raw.githubusercontent.com/Pullusb/Apply_Shapekeyed_Modifiers/master/applyShapekeyedModifier.py)** (right click, save Target as)  
  
---
> /!\ experimental : some modifiers will alter the geometry.
Currently working for applying mirror and subsurf modifier (tested succesfully).
Other modifier may cause changes in geometry at the apply. (simple deform for exemple give bad results !).

The apply menu is available in the submenu “special” of the shapekey pannel.

![Apply Shapekeyed modifier - panel](https://github.com/Pullusb/images_repo/raw/master/blender_ApplyShapekeyedModifier_panel.png)

It calls a popup menu to select modifiers to apply.

![Apply Shapekeyed modifier - popup](https://github.com/Pullusb/images_repo/raw/master/blender_ApplyShapekeyedModifier_panel_popup.png)
