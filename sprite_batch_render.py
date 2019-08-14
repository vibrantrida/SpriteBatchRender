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
			start_frame=0, end_frame=0):
		os.system("cls")
		camera = scene.camera
		old_frame = scene.frame_current
		
		if not obj_name in scene.objects:
			self.report({'ERROR_INVALID_INPUT'}, "Target object '%s' not found!" % (obj_name))
			return
		obj = scene.objects[obj_name]

		# go through all currently selected meshes
		for selected_object in bpy.context.selected_objects:
			# skip non-meshes
			if selected_object.type != 'MESH':
				self.report({'ERROR_INVALID_INPUT'}, "'%s' is not a mesh object!" % (selected_object.name))
				continue

			angles = "12345678"
			frames = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
			subsprites = "0123456789"			
			total_angles = len(angles)			
			total_frames = len(frames)
			total_subsprites = len(subsprites)

			# too many frames
			if end_frame > (total_frames * total_subsprites):
				self.report({'ERROR_INVALID_INPUT'}, "Animation exceeds %i frames!" % total_frames * total_subsprites)
				break
				return

			# print("total_angles " + str(angles))
			# print("object:", obj_name, obj)

			count = 0
			obj.rotation_mode = 'XYZ'
			orig_rotation = obj.rotation_euler.z
			current_subsprite = 0
			current_subsprite_counter = old_frame - 1

			for f in range(start_frame, end_frame+1):
				scene.frame_set(f)

				# only 1 step if there's no rotation
				no_rotation = bpy.data.objects[obj.name]['NoRotation']
				if no_rotation == 1:
					total_angles = 1

				mirror = bpy.data.objects[obj.name]['Mirror']

				print()

				# increase subsprite number
				current_subsprite_counter += 1
				if current_subsprite_counter > total_frames:
					current_subsprite_counter = 1
					if f > (total_frames * 2):
						current_subsprite += 1

				for ang in range(0, total_angles):
					# stop full rotation if mirrored
					if no_rotation == 0 and mirror == 1 and ang >= 5:
						break

					angle = ((math.pi*2.0) / total_angles) * ang

					obj.rotation_euler.z = orig_rotation - angle
					print(obj.rotation_euler.z)

					scene.update()
					bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

					# if no_rotation is true, force angle 0
					if no_rotation == 0:
						angle_string = angles[ang]
					else:
						angle_string = "0"

					frame_string = frames[(f - 1) % total_frames]

					sprite_string = bpy.data.objects[selected_object.name]['SpriteName']
					subsprite_string = subsprites[current_subsprite]

					# if there are more than 26 frames, remove the last
					# character from the sprite name and append the subsprite
					if f > total_frames:
						sprite_string = sprite_string[:-1]
					else:
						subsprite_string = ""

					# handle mirroring
					if no_rotation == 0 and mirror == 1:
						# 2 and 8
						if ang == 1:
							angle_string = angle_string + frame_string + "8"
						# 3 and 7
						elif ang == 2:
							angle_string = angle_string + frame_string + "7"
						# 4 and 6
						elif ang == 3:
							angle_string = angle_string + frame_string + "6"

					scene.render.filepath = filepath + sprite_string + subsprite_string + frame_string + angle_string
					bpy.ops.render.render(animation=False, write_still=True)

					#print ("%d:%s: %f,%f" % (f, angle_string, camera.location.x, camera.location.y))
					count += 1

			print ("Rendered %d shots" % (count))
			scene.frame_set(old_frame)

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
