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
    in_collision_check = False
    
    def collision_check(self, new_x, new_y, old_world, new_world):
        obj = new_world.get_object(new_x, new_y)
        if obj is not None and obj is not self:
            return obj

        obj = old_world.get_object(new_x, new_y)
        if obj is not None and obj is not self and not old_world.is_destroyed(obj):
            oth_x, oth_y = new_world.get_location(obj)
            if oth_x == -1:
                if self.in_collision_check:
                    return True
                else:
                    self.in_collision_check = True
                    obj.advance(old_world, new_world)
                    self.in_collision_check = False
                    oth_x, oth_y = new_world.get_location(obj)
                    if (oth_x, oth_y) == (new_x, new_y):
                        return True

    def shoot(self, old_world, new_world):
        pass

    def get_initial_state(self):
        pass

class Baddie(GameObject):
    def collision_check(self, new_x, new_y, old_world, new_world):
        result = GameObject.collision_check(self, new_x, new_y, old_world, new_world)
        if result is not None:
            return result

        obj = old_world.get_object(new_x, new_y)
        if obj is not None and obj is not self and isinstance(obj, Baddie) and not old_world.is_destroyed(obj):
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

    def shoot(self, old_world, new_world):
        target = None
        target_health = 0
        my_x, my_y = old_world.get_location(self)
        for xofs, yofs in ((-1,0),(1,0),(0,-1),(0,1)):
            obj = new_world.get_object(my_x + xofs, my_y + yofs)
            if isinstance(obj, Turret):
                cooldown, health = new_world.get_state(obj)
                if target is None or health < target_health:
                    target = obj
                    target_health = health

        if target is not None:
            cooldown, health = new_world.get_state(target)
            new_health = health - 4
            x, y = new_world.get_location(target)
            new_world.add_shot_animation(self, target)
            if new_health <= 0:
                new_world.destroy_object(target, self)
            else:
                new_world.add_object(x, y, target, (cooldown, new_health))

class MarchingBaddie(Baddie):
    def get_preferred_locations(self, world):
        old_x, old_y = world.get_location(self)

        direction = world.get_state(self)

        yield old_x + direction, old_y, direction
        yield old_x, old_y + 1, -direction
        yield old_x - direction, old_y, -direction
        yield old_x, old_y, -direction

    def get_initial_state(self):
        return random.randint(0, 1) or -1

class Turret(GameObject):
    cooldown = 1
    starting_health = 4
    
    def advance(self, old_world, new_world):
        old_x, old_y = old_world.get_location(self)

        cooldown, health = old_world.get_state(self)

        if cooldown > 0:
            cooldown -= 1

        new_world.add_object(old_x, old_y, self, (cooldown, health))

    def shoot(self, old_world, new_world):
        cooldown, health = new_world.get_state(self, (0, 12))
        if cooldown:
            return
        
        for x, y, in self.get_covered_locations(new_world):
            obj = new_world.get_object(x, y)
            if isinstance(obj, Baddie) and not new_world.is_destroyed(obj):
                new_world.add_shot_animation(self, obj)
                new_world.destroy_object(obj, self)

                old_x, old_y = old_world.get_location(self)
                cooldown = self.cooldown
                health -= 1
                if health <= 0:
                    new_world.destroy_object(self)
                else:
                    new_world.add_object(old_x, old_y, self, (cooldown, health))
                break

    def get_covered_locations_at(self, world, x, y):
        return ()

    def get_covered_locations(self, world):
        x, y = world.get_location(self)
        return self.get_covered_locations_at(world, x, y)

    def get_initial_state(self):
        return (1, self.starting_health)

class DirectionalTurret(Turret):
    direction = (0, -1)

    def get_covered_locations_at(self, world, x, y):
        x_ofs, y_ofs = self.direction

        while True:
            x, y = x + x_ofs, y + y_ofs
            obj = world.get_object(x, y)
            if isinstance(obj, (OutOfBounds, Turret)):
                break
            yield x, y

class KnightTurret(Turret):
    def get_covered_locations_at(self, world, x, y):
        for xofs, yofs in ((-1,2),(1,2),(-1,-2),(1,-2),(-2,1),(2,1),(-2,-1),(2,-1)):
            obj = world.get_object(x + xofs, y + yofs)
            if not isinstance(obj, (OutOfBounds, Turret)):
                yield x + xofs, y + yofs

class BishopTurret(Turret):
    def get_covered_locations_at(self, world, x, y):
        for x_ofs, y_ofs in ((-1,-1), (-1,1), (1,-1), (1,1)):
            cx, cy = x, y
            for i in range(2):
                cx, cy = cx + x_ofs, cy + y_ofs
                obj = world.get_object(cx, cy)
                if isinstance(obj, (OutOfBounds, Turret)):
                    break
                yield cx, cy

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

        self.place_turret_cooldown = 0

        self.shot_animations = []

        self.next_turret = self.get_random_turret()

        self.waves = []

    def add_object(self, x, y, obj, state=None):
        self.objects[x + y * self.width] = obj

        self.object_to_pos[obj] = (x, y)

        if state is None:
            state = obj.get_initial_state()

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

    def make_random_wave(self):
        count = random.randint(3,12)
        enemy_type = MarchingBaddie
        enemy_initial_state = enemy_type().get_initial_state()
        spawnx = random.randint(0,self.width-1)
        return count, enemy_type, enemy_initial_state, spawnx

    def advance(self):
        result = World(self.width, self.height)

        while len(self.waves) < 1:
            self.waves.append(self.make_random_wave())

        for count, enemy_type, enemy_initial_state, spawnx in self.waves:
            enemy = enemy_type()
            result.add_object(spawnx, 0, enemy, enemy_initial_state)
            if count > 1:
                result.waves.append((count-1, enemy_type, enemy_initial_state, spawnx))

        for x in range(self.width):
            for y in range(self.height-1, -1, -1):
                obj = self.get_object(x, y)
                if obj is not None and not self.is_destroyed(obj) and result.get_location(obj) == (-1,-1):
                    obj.advance(self, result)

        for x in range(self.width):
            for y in range(self.height-1, -1, -1):
                obj = self.get_object(x, y)
                if obj is not None and not self.is_destroyed(obj):
                    obj.shoot(self, result)

        result.mouse_pos = self.mouse_pos

        result.place_turret_cooldown = self.place_turret_cooldown
        result.next_turret = self.next_turret
        if result.place_turret_cooldown != 0:
            result.place_turret_cooldown -= 1
            if result.place_turret_cooldown == 0:
                result.next_turret = result.get_random_turret()

        return result

    def clicked(self, x, y):
        if not self.place_turret_cooldown and y != 0:
            self.add_object(x, y, self.next_turret)
            self.place_turret_cooldown = 3

    def hover(self, x, y):
        self.mouse_pos = (x, y)

    def add_shot_animation(self, source, target):
        self.shot_animations.append((source, target))

    def get_random_turret(self):
        r = random.randint(0,5)
        if r < 4:
            result = DirectionalTurret()
            result.direction = ((-1,0),(1,0),(0,-1),(0,1))[r]
            if r == 3:
                result.starting_health = 32
                result.cooldown = 1
            return result
        elif r == 4:
            return KnightTurret()
        elif r == 5:
            return BishopTurret()

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

                    if isinstance(obj, MarchingBaddie):
                        direction = world.get_state(obj)
                        prev_direction = old_world.get_state(obj, direction)

                        direction = ((1.0-t) * prev_direction + t * direction)

                        vert_x = int((direction + 1.5) * draw_width / 3)

                        pygame.draw.line(surface, Color(0,0,0,255),
                                         (draw_x + vert_x, draw_y + draw_height / 2),
                                         (draw_x + vert_x, draw_y + draw_height * 5 / 6),
                                         2)

                        vert_x = int((direction + 2.0) * draw_width / 6)

                        pygame.draw.line(surface, Color(0,0,0,255),
                                         (draw_x + vert_x, draw_y + draw_height * 5 / 6),
                                         (draw_x + vert_x + draw_width / 3, draw_y + draw_height * 5 / 6),
                                         2)
                                    
                elif isinstance(obj, Turret):
                    surface.fill(Color(0,0,255,255), Rect(draw_x+2, draw_y+2, draw_width-4, draw_height-4))

                    cooldown, health = world.get_state(obj, (0, obj.starting_health))

                    #draw stats
                    font = pygame.font.Font(None, draw_height / 3)

                    # cooldown
                    text = font.render("%s/%s" % (cooldown, obj.cooldown)
                        , 1, Color(240, 240, 240, 255))
                    textpos = text.get_rect(centerx=draw_x+draw_width/2, centery=draw_y+draw_height/3)
                    surface.blit(text, textpos)

                    # health
                    text = font.render("%s/%s" % (health, obj.starting_health)
                        , 1, Color(240, 240, 240, 255))
                    textpos = text.get_rect(centerx=draw_x+draw_width/2, centery=draw_y+draw_height*2/3)
                    surface.blit(text, textpos)
                else:
                    surface.fill(Color(255,0,255,255), Rect(draw_x, draw_y, draw_width, draw_height))

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

    for obj_x in range(world.width):
        for obj_y in range(world.height):
            obj = world.get_object(obj_x, obj_y)
            if isinstance(obj, Turret):
                for cx, cy in obj.get_covered_locations(world):
                    draw_x = cx * w / world.width
                    draw_y = cy * h / world.height
                    
                    draw_width = w / world.width
                    draw_height = h / world.height
                    surface.fill(Color(48,48,48,255), Rect(draw_x, draw_y, draw_width, draw_height), BLEND_ADD)

    for source, target in world.shot_animations:
        prev_x, prev_y = old_world.get_location(source)
        obj_x, obj_y = world.get_location(target)
        
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

    if not world.place_turret_cooldown:
        # draw turret to be placed

        mouse_x, mouse_y = world.mouse_pos

        if mouse_y != 0:
            draw_x = mouse_x * w / world.width + x
            draw_y = mouse_y * h / world.height + y
            
            draw_width = w / world.width
            draw_height = h / world.height
            obj_width = w / world.width * 2 / 3
            obj_height = h / world.height * 2 / 3
            draw_x += (draw_width - obj_width) / 2
            draw_y += (draw_height - obj_height) / 2
            pygame.draw.rect(surface, Color(128,128,255,168), Rect(draw_x, draw_y, obj_width, obj_height), 2)

            for target_x, target_y in world.next_turret.get_covered_locations_at(world, mouse_x, mouse_y):
                draw_x = target_x * w / world.width + x
                draw_y = target_y * h / world.height + y

                obj_width = w / world.width * 2 / 3
                obj_height = h / world.height * 2 / 3
                draw_x += (draw_width - obj_width) / 2
                draw_y += (draw_height - obj_height) / 2

                pygame.draw.line(surface, Color(128,0,0,255),
                                 (draw_x, draw_y),
                                 (draw_x + obj_width, draw_y + obj_height),
                                 2)

                pygame.draw.line(surface, Color(128,0,0,255),
                                 (draw_x, draw_y + obj_height),
                                 (draw_x + obj_width, draw_y),
                                 2)

                pygame.draw.rect(surface, Color(128,0,0,168), Rect(draw_x, draw_y, obj_width, obj_height), 2)
    
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
                    if world.place_turret_cooldown:
                        old_world, world = world, world.advance()
                    else:
                        frame -= 1

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
