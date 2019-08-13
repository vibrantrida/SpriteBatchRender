"""
Sprite Batch Renderer, a Blender addon
Copyright (C) 2015-2016 Pekka Väänänen

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

See COPYING for details.
"""

"""
Renders the scene from multiple directions and saves the results in separate files.
The "front" direction is the same as Blender's front view, in other words your model
should face to the negative y direction.

Multiple frames can be rendered. The animation Frame Range is read from the regular
Start Frame and End Frame rendering properties.

Usage:
	Set your camera (called "Camera") to track an object placed at the origo.
	Place your camera to the distance and height you'd like it to render the object from.
	
	See Sprite Batch Rendering section of the Render-tab for controls.
	
	Note: the rendering process can't be canceled once started, so make sure your
	Frame Range and image resolution are correct.

"""

import os
import bpy
import math
import sys
import time
import mathutils as mu

from bpy.props import *

bl_info = \
	{
		"name" : "Sprite Batch Render",
		"author" : "Pekka Väänänen <pekka.vaananen@iki.fi>",
		"version" : (1, 2, 0),
		"blender" : (2, 6, 0),
		"location" : "Render",
		"description" :
			"Renders the scene from multiple directions.",
		"warning" : "There's currently no way to cancel rendering",
		"wiki_url" : "",
		"tracker_url" : "",
		"category" : "Render",
	}

class SpriteRenderSettings(bpy.types.PropertyGroup):
	path = StringProperty (
		name = "Sprite render path",
		description = """Where to save the sprite frames.""",
		default = "C:/tmp/"
	)

	target = StringProperty (
		name = "Target object",
		description = """The object to be rotated. Usually an Empty
with the actual models as children.""",
		default = ""
	)


class SpriteRenderOperator(bpy.types.Operator):
	bl_idname = "render.spriterender_operator"
	bl_label = "Sprite Render Operator"
	bl_options = {'REGISTER'}
	
	def execute(self, context):
		self.render(
			context.scene,
			context.scene.sprite_render.target,
			context.scene.sprite_render.path,
			context.scene.frame_start,
			context.scene.frame_end
		)
		return {'FINISHED'}

	def render(self, scene, obj_name, filepath,\
			startframe=0, endframe=0):
		os.system("cls")
		camera = scene.camera
		oldframe = scene.frame_current
		
		if not obj_name in scene.objects:
			self.report({'ERROR_INVALID_INPUT'}, "Target object '%s' not found!" % (obj_name))
			return
		obj = scene.objects[obj_name]

		# go through all currently selected meshes
		for selectedObject in bpy.context.selected_objects:
			# skip non-meshes
			if selectedObject.type != 'MESH':
				self.report({'ERROR_INVALID_INPUT'}, "'%s' is not a mesh object!" % (selectedObject.name))
				continue

			steps = 8
			stepnames = "12345678"
			framenames = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
			subframenames = "0123456789"

			# print("steps " + str(stepnames))
			# print("object:", obj_name, obj)

			frame = startframe
			count = 0
			obj.rotation_mode = 'XYZ'
			orig_rotation = obj.rotation_euler.z
			sprSub = 0
			sprSubCounter = oldframe - 1

			for f in range(startframe, endframe+1):
				scene.frame_set(f)

				# only 1 step if there's no rotation
				norotation = bpy.data.objects[obj.name]['NoRotation']
				if norotation == 1:
					steps = 1

				mirror = bpy.data.objects[obj.name]['Mirror']

				print()

				# increase subsprite number
				sprSubCounter += 1
				if sprSubCounter > len(framenames):
					sprSubCounter = 1
					if f > (len(framenames) * 2):
						sprSub += 1

				#print("f " + str(f))
				#print("sprSubCounter " + str(sprSubCounter))
				
				# too many frames
				if f > (len(framenames) * len(subframenames)):
					self.report({'ERROR_INVALID_INPUT'}, "Too many frames!")
					break
					return

				for i in range(0, steps):
					# stop full rotation if mirrored
					if norotation == 0 and mirror == 1 and i >= 5:
						break

					angle = ((math.pi*2.0) / steps) * i

					obj.rotation_euler.z = orig_rotation - angle
					print (obj.rotation_euler.z)

					scene.update()
					bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

					# if norotation is set, force angle 0
					if norotation == 0:
						stepname = stepnames[i]
					else:
						stepname = "0"

					name = framenames[(f - 1) % len(framenames)]

					actobjectname = selectedObject.name
					sprName = bpy.data.objects[actobjectname]['SpriteName']
					sprSubString = subframenames[sprSub]

					# if there are more than 26 frames, remove the last character and append subsprite
					if f > len(framenames):
						sprName = sprName[:-1]
					else:
						sprSubString = ""

					# handle mirroring
					if norotation == 0 and mirror == 1:
						# 2 and 8
						if i == 1:
							stepname = stepname + name + "8"
						# 3 and 7
						elif i == 2:
							stepname = stepname + name + "7"
						# 4 and 6
						elif i == 3:
							stepname = stepname + name + "6"

					scene.render.filepath = filepath + sprName + sprSubString + name + stepname
					bpy.ops.render.render(animation=False, write_still=True)

					#print ("%d:%s: %f,%f" % (f, stepname, camera.location.x, camera.location.y))
					count += 1

			print ("Rendered %d shots" % (count))
			scene.frame_set(oldframe)

			obj.rotation_euler.z = orig_rotation




class SpriteRenderPanel(bpy.types.Panel):
	bl_idname = 'sprite_panel'
	bl_label = 'Sprite Batch Rendering'
	bl_space_type = 'PROPERTIES'
	bl_region_type = 'WINDOW'
	bl_context = "render"
	
	def draw(self, context):
		l = self.layout
		framerow = l.row()
		props = context.scene.sprite_render
		
		l.column().prop_search(props, "target", context.scene, "objects",\
				icon='OBJECT_DATA', text="Target object")

		if props.target not in context.scene.objects:
			l.column().label("Invalid target object '%s'!" % (props.target),
			icon='ERROR')

		l.row().prop(props, "path", text="Output path")
		row = l.row()
		row.operator("render.spriterender_operator", text="Render Batch", icon='RENDER_ANIMATION')

		

def register():
	bpy.utils.register_class(SpriteRenderOperator)
	bpy.utils.register_class(SpriteRenderPanel)
	bpy.utils.register_class(SpriteRenderSettings)

	bpy.types.Scene.sprite_render = bpy.props.PointerProperty(type=SpriteRenderSettings)
	
	
def unregister():
	bpy.utils.unregister_class(SpriteRenderOperator)
	bpy.utils.unregister_class(SpriteRenderPanel)
	bpy.utils.unregister_class(SpriteRenderSettings)
	del bpy.types.Scene.sprite_render


if __name__ == "__main__":
	register()
