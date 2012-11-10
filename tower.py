# Copyright 2012 Vincent Povirk
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import random
random.seed()

import pygame
from pygame.locals import *

class GameObject(object):
    def collision_check(self, new_x, new_y, old_world, new_world):
        obj = new_world.get_object(new_x, new_y)
        if obj is not None:
            return obj

        obj = old_world.get_object(new_x, new_y)
        if obj is not None and obj is not self:
            oth_x, oth_y = new_world.get_location(obj)
            if oth_x == -1:
                return obj # advance the other obj, maybe?

    def shoot(self, old_world, new_world):
        pass

class Baddie(GameObject):
    def collision_check(self, new_x, new_y, old_world, new_world):
        result = GameObject.collision_check(self, new_x, new_y, old_world, new_world)
        if result is not None:
            return result

        obj = old_world.get_object(new_x, new_y)
        if obj is not None and obj is not self and isinstance(obj, Baddie):
            old_x, old_y = old_world.get_location(self)
            oth_x, oth_y = new_world.get_location(obj)
            for oth_pref_x, oth_pref_y, oth_pref_state in obj.get_preferred_locations(old_world):
                if oth_pref_x == old_x and oth_pref_y == old_y:
                    return obj
                elif oth_pref_x == oth_x and oth_pref_y == oth_y:
                    break
    
    def advance(self, old_world, new_world):
        for x, y, new_state in self.get_preferred_locations(old_world):
            if not self.collision_check(x, y, old_world, new_world):
                new_world.add_object(x, y, self, new_state)
                break
        else:
            old_x, old_y = old_world.get_location(self)

            state = old_world.get_state(self, None)
            new_world.add_object(old_x, old_y, self, state)

    def get_preferred_locations(self, world):
        return ()

class MarchingBaddie(Baddie):
    def get_preferred_locations(self, world):
        old_x, old_y = world.get_location(self)

        direction = world.get_state(self, random.randint(0, 1) or -1)

        yield old_x + direction, old_y, direction
        yield old_x, old_y + 1, -direction
        yield old_x - direction, old_y, -direction
        yield old_x, old_y, -direction

class Turret(GameObject):
    def advance(self, old_world, new_world):
        old_x, old_y = old_world.get_location(self)

        new_world.add_object(old_x, old_y, self)

    def shoot(self, old_world, new_world):
        for x, y, in self.get_covered_locations(new_world):
            obj = new_world.get_object(x, y)
            if isinstance(obj, Baddie) and not new_world.is_destroyed(obj):
                new_world.destroy_object(obj, self)
                break

    def get_covered_locations(self, world):
        return ()

class DirectionalTurret(Turret):
    direction = (0, -1)

    def get_covered_locations(self, world):
        x, y = world.get_location(self)
        x_ofs, y_ofs = self.direction

        while True:
            x, y = x + x_ofs, y + y_ofs
            obj = world.get_object(x, y)
            if isinstance(obj, (OutOfBounds, Turret)):
                break
            yield x, y

class OutOfBounds(object):
    pass

out_of_bounds = OutOfBounds()

class World(object):
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.objects = [None] * (width * height)

        self.object_to_pos = {}

        self.object_state = {}

        self.destroyed_objects = {}

        self.mouse_pos = (0, 0)

    def add_object(self, x, y, obj, state=None):
        self.objects[x + y * self.width] = obj

        self.object_to_pos[obj] = (x, y)

        if state is not None:
            self.object_state[obj] = state

    def get_object(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.objects[x + y * self.width]

        return out_of_bounds

    def get_location(self, obj):
        return self.object_to_pos.get(obj, (-1, -1))

    def get_state(self, obj, default = None):
        return self.object_state.get(obj, default)

    def destroy_object(self, obj, destroyed_by=None):
        self.destroyed_objects[obj] = destroyed_by

    def is_destroyed(self, obj):
        return obj in self.destroyed_objects

    def destroyer(self, obj):
        return self.destroyed_objects.get(obj, None)

    def advance(self):
        result = World(self.width, self.height)

        if random.randint(0, 3) == 0:
            result.add_object(random.randint(0, self.width-1), 0, MarchingBaddie())

        for x in range(self.width):
            for y in range(self.height-1, -1, -1):
                obj = self.get_object(x, y)
                if obj is not None and not self.is_destroyed(obj):
                    obj.advance(self, result)

        for x in range(self.width):
            for y in range(self.height-1, -1, -1):
                obj = self.get_object(x, y)
                if obj is not None and not self.is_destroyed(obj):
                    obj.shoot(self, result)

        result.mouse_pos = self.mouse_pos

        return result

    def clicked(self, x, y):
        self.add_object(x, y, DirectionalTurret())

    def hover(self, x, y):
        self.mouse_pos = (x, y)

def draw_world(old_world, world, t, surface, x, y, w, h):
    surface.fill(Color(0,0,0,255), Rect(x, y, w, h))

    for obj_x in range(world.width):
        for obj_y in range(world.height):
            obj = world.get_object(obj_x, obj_y)
            if obj is not None:
                prev_x, prev_y = old_world.get_location(obj)
                
                if prev_x in (obj_x, -1):
                    draw_x = obj_x * w / world.width
                else:
                    draw_x = int(((1.0-t) * prev_x + t * obj_x) * w / world.width)
                if prev_y in (obj_y, -1):
                    draw_y = obj_y * h / world.height
                else:
                    draw_y = int(((1.0-t) * prev_y + t * obj_y) * h / world.height)
                
                draw_width = w / world.width
                draw_height = h / world.height
                surface.fill(Color(0,0,0,255), Rect(draw_x, draw_y, draw_width, draw_height))
                if isinstance(obj, Baddie):
                    surface.fill(Color(255,0,0,255), Rect(draw_x+2, draw_y+2, draw_width-4, draw_height-4))
                elif isinstance(obj, Turret):
                    surface.fill(Color(0,0,255,255), Rect(draw_x+2, draw_y+2, draw_width-4, draw_height-4))
                else:
                    surface.fill(Color(255,0,255,255), Rect(draw_x, draw_y, draw_width, draw_height))

                destroyer = world.destroyer(obj)
                if destroyer is not None:
                    prev_x, prev_y = world.get_location(destroyer)
                    
                    if prev_x in (obj_x, -1):
                        draw_x = obj_x * w / world.width
                    else:
                        draw_x = int(((1.0-t) * prev_x + t * obj_x) * w / world.width)
                    if prev_y in (obj_y, -1):
                        draw_y = obj_y * h / world.height
                    else:
                        draw_y = int(((1.0-t) * prev_y + t * obj_y) * h / world.height)
                    
                    draw_width = w / world.width
                    draw_height = h / world.height
                    bullet_width = w / world.width / 8
                    bullet_height = h / world.height / 8
                    draw_x += (draw_width - bullet_width) / 2
                    draw_y += (draw_height - bullet_height) / 2
                    surface.fill(Color(255,128,0,255), Rect(draw_x, draw_y, bullet_width, bullet_height))

            obj = old_world.get_object(obj_x, obj_y)
            if obj is not None and world.get_location(obj) == (-1,-1):
                obj_x, obj_y = old_world.get_location(obj)
                
                draw_x = obj_x * w / world.width
                draw_y = obj_y * h / world.height
                
                full_draw_width = w / world.width
                full_draw_height = h / world.height

                draw_width = int((1.0-t) * full_draw_width)
                draw_height = int((1.0-t) * full_draw_height)

                if draw_width > 4 and draw_height > 4:
                    draw_x += (full_draw_width - draw_width) / 2
                    draw_y += (full_draw_height - draw_height) / 2
                
                    surface.fill(Color(0,0,0,255), Rect(draw_x, draw_y, draw_width, draw_height))
                    if isinstance(obj, Baddie):
                        surface.fill(Color(255,0,0,255), Rect(draw_x+2, draw_y+2, draw_width-4, draw_height-4))
                    elif isinstance(obj, Turret):
                        surface.fill(Color(0,0,255,255), Rect(draw_x+2, draw_y+2, draw_width-4, draw_height-4))
                    else:
                        surface.fill(Color(255,0,255,255), Rect(draw_x, draw_y, draw_width, draw_height))

    if True: #replace with "can place turret" condition
        # draw turret to be placed

        mouse_x, mouse_y = world.mouse_pos

        draw_x = mouse_x * w / world.width
        draw_y = mouse_y * h / world.height
        
        draw_width = w / world.width
        draw_height = h / world.height
        obj_width = w / world.width * 2 / 3
        obj_height = h / world.height * 2 / 3
        draw_x += (draw_width - obj_width) / 2
        draw_y += (draw_height - obj_height) / 2
        surface.fill(Color(128,128,255,168), Rect(draw_x, draw_y, obj_width, obj_height))

def run(world, x, y, w, h):
    screen = pygame.display.get_surface()
    clock = pygame.time.Clock()
    paused = False
    frame = 0
    old_world, world = world, world.advance()
    pygame.time.set_timer(pygame.USEREVENT, 15)

    while True:
        events = pygame.event.get()
        
        if paused and not events:
            events = [pygame.event.wait()]
        
        for event in events:
            if event.type == QUIT:
                return
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    return
                elif event.key == K_PAUSE or event.key == K_p:
                    paused = not paused
            elif paused:
                continue
            elif event.type == MOUSEBUTTONDOWN:
                press_x = event.pos[0] * world.width / w + x
                press_y = event.pos[1] * world.height / h + y
                world.hover(press_x, press_y)
                if event.button == 1:
                    world.clicked(press_x, press_y)
            elif event.type == pygame.MOUSEMOTION:
                press_x = event.pos[0] * world.width / w + x
                press_y = event.pos[1] * world.height / h + y
                world.hover(press_x, press_y)
            elif event.type == pygame.USEREVENT:
                frame += 1
                if frame % 20 == 0:
                    old_world, world = world, world.advance()

        draw_world(old_world, world, (frame % 20) / 20.0, screen, x, y, w, h)

        if paused:
            if pygame.font:
                font = pygame.font.Font(None, 48)
                text = font.render("Paused", 1, Color(240, 240, 240, 255))
                textpos = text.get_rect(centerx=x+w//2, centery=y+h//2)
                screen.blit(text, textpos)

        pygame.display.flip()

def main():
    game_width = 6
    game_height = 8
    width = game_width * 64
    height = game_height * 64

    pygame.init()

    world = World(game_width, game_height)

    pygame.display.set_mode((width, height))
    
    run(world, 0, 0, width, height)

if __name__ == '__main__':
    main()
