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
            return True

        obj = old_world.get_object(new_x, new_y)
        if obj is not None and obj is not self and new_world.get_location(obj) == (-1, -1):
            return True

        return False

class Baddie(GameObject):
    def advance(self, old_world, new_world):
        pass

class MarchingBaddie(Baddie):
    def advance(self, old_world, new_world):
        Baddie.advance(self, old_world, new_world)
        
        old_x, old_y = old_world.get_location(self)

        direction = old_world.get_state(self, random.randint(0, 1) or -1)

        new_x, new_y = old_x + direction, old_y
        if self.collision_check(new_x, new_y, old_world, new_world):
            direction = -direction
            new_x, new_y = old_x, old_y + 1
            if self.collision_check(new_x, new_y, old_world, new_world):
                new_x, new_y = old_x + direction, old_y
                if self.collision_check(new_x, new_y, old_world, new_world):
                    new_x, new_y = old_x, old_y
        
        new_world.add_object(new_x, new_y, self, direction)

class Turret(GameObject):
    def advance(self, old_world, new_world):
        old_x, old_y = old_world.get_location(self)

        new_world.add_object(old_x, old_y, self)

class DirectionalTurret(Turret):
    def advance(self, old_world, new_world):
        Turret.advance(self, old_world, new_world)

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

    def advance(self):
        result = World(self.width, self.height)

        result.add_object(random.randint(0, self.width-1), 0, MarchingBaddie())

        for x in range(self.width):
            for y in range(self.height-1, -1, -1):
                obj = self.get_object(x, y)
                if obj is not None:
                    obj.advance(self, result)

        return result

    def clicked(self, x, y):
        self.add_object(x, y, DirectionalTurret())

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
                if event.button == 1:
                    world.clicked(press_x, press_y)
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
