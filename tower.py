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

import pygame
from pygame.locals import *

class Baddie(object):
    def advance(self, old_world, new_world):
        pass

class FallingBaddie(Baddie):
    def advance(self, old_world, new_world):
        old_x, old_y = old_world.get_location(self)

        new_x, new_y = old_x, old_y + 1
        
        if 0 <= new_x < old_world.width and 0 <= new_y < old_world.height:
            new_world.add_object(old_x, old_y + 1, self)

class World(object):
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.objects = [None] * (width * height)

        self.object_to_pos = {}

    def add_object(self, x, y, obj):
        self.objects[x + y * self.width] = obj

        self.object_to_pos[obj] = (x, y)

    def get_object(self, x, y):
        return self.objects[x + y * self.width]

    def get_location(self, obj):
        return self.object_to_pos.get(obj, (-1, -1))

    def advance(self):
        result = World(self.width, self.height)

        for x in range(self.width):
            for y in range(self.height-1, -1, -1):
                obj = self.get_object(x, y)
                if obj is not None:
                    obj.advance(self, result)

        return result

def draw_world(world, surface, x, y, w, h):
    surface.fill(Color(0,0,0,255), Rect(x, y, w, h))

    for obj_x in range(world.width):
        for obj_y in range(world.height):
            obj = world.get_object(obj_x, obj_y)
            if obj is not None:
                draw_x = obj_x * w / world.width
                draw_y = obj_y * h / world.height
                draw_width = w / world.width
                draw_height = h / world.height
                surface.fill(Color(255,0,0,255), Rect(draw_x, draw_y, draw_width, draw_height))

def run(world, x, y, w, h):
    screen = pygame.display.get_surface()
    clock = pygame.time.Clock()
    paused = False
    frame = 0

    while True:
        if not paused:
            clock.tick(60)
        
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
        
        if not paused:
            frame += 1
            if frame % 20 == 0:
                world = world.advance()

        draw_world(world, screen, x, y, w, h)

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

    world.add_object(3, 0, FallingBaddie())

    pygame.display.set_mode((width, height))
    
    run(world, 0, 0, width, height)

if __name__ == '__main__':
    main()
