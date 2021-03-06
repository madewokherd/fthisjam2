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

class FallingBaddie(Baddie):
    def get_preferred_locations(self, world):
        old_x, old_y = world.get_location(self)

        direction = world.get_state(self)

        yield old_x, old_y + 1, direction
        yield old_x + direction, old_y + 1, direction
        yield old_x - direction, old_y + 1, -direction
        yield old_x + direction, old_y, direction
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

ACTION_NEWWORLD = "ACTION_NEWWORLD"
ACTION_QUIT = "ACTION_QUIT"

class Link(GameObject):
    text = "text"
    size = 1.0
    action = None
    action_args = ()

    def advance(self, old_world, new_world):
        old_x, old_y = old_world.get_location(self)

        new_world.add_object(old_x, old_y, self, None)

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

        self.mouse_pos = (-1, -1)

        self.place_turret_cooldown = 3

        self.place_turret_points = 0

        self.shot_animations = []

        self.turret_health_multiplier = 4

        self.next_turret = self.get_random_turret()

        self.waves = []

        self.lost = False

        self.score = 0

        self.click_to_baddie = False

        self.num_waves = 0

        self.game_ui = True
        
        self.realtime = False

        self.help_text = ""

        self.help_text_on_top = False

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

    def advance(self, shoot=True):
        result = World(self.width, self.height)

        result.lost = self.lost

        result.click_to_baddie = self.click_to_baddie

        result.num_waves = self.num_waves

        result.game_ui = self.game_ui

        result.turret_health_multiplier = self.turret_health_multiplier

        result.realtime = self.realtime

        result.help_text = self.help_text

        result.help_text_on_top = self.help_text_on_top

        while len(self.waves) < self.num_waves:
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

        if shoot:
            for x in range(self.width):
                for y in range(self.height-1, -1, -1):
                    obj = self.get_object(x, y)
                    if obj is not None and not self.is_destroyed(obj):
                        obj.shoot(self, result)

        for x in range(self.width):
            if not isinstance(result.get_object(x, self.height-1), Baddie):
                break
        else:
            result.lost = True

        if result.lost:
            result.score = self.score
        else:
            result.score = self.score + 1

        result.mouse_pos = self.mouse_pos

        result.place_turret_cooldown = self.place_turret_cooldown
        result.place_turret_points = self.place_turret_points + 1
        
        result.next_turret = self.next_turret

        return result

    def clicked(self, x, y):
        obj = self.get_object(x, y)
        if isinstance(obj, Link):
            return obj
        if self.click_to_baddie:
            count, enemy_type, enemy_initial_state, spawnx = self.make_random_wave()
            self.add_object(x, y, enemy_type(), enemy_initial_state)
            return True
        else:
            if self.place_turret_cooldown <= self.place_turret_points and y != 0:
                self.add_object(x, y, self.next_turret)
                self.place_turret_points -= self.place_turret_cooldown
                self.next_turret = self.get_random_turret()
                return True

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
                result.starting_health = 9 * self.turret_health_multiplier
                result.cooldown = 1
            else:
                result.starting_health = self.turret_health_multiplier
            return result
        elif r == 4:
            result = KnightTurret()
            result.starting_health = self.turret_health_multiplier
            return result
        elif r == 5:
            result = BishopTurret()
            result.starting_health = self.turret_health_multiplier
            return result

def draw_text(surface, text, x, y, size):
    font = pygame.font.Font(None, size)

    texts = []

    for line in text.split('\n'):
        text = font.render(line, 1, Color(240,240,240,255))
        texts.append(text)

    text_y = y

    for line in texts:
        textpos = line.get_rect(x=0, y=text_y)
        surface.blit(line, textpos)
        text_y += textpos.height

def draw_world(old_world, world, t, surface, x, y, w, h, paused=False):
    surface.fill(Color(0,0,0,255), Rect(x, y, w, h))
    diagonal_pattern_surface = None

    if world.help_text and not world.help_text_on_top:
        draw_text(surface, world.help_text, 0, 0, int(h / world.height / 2))

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
                    elif isinstance(obj, FallingBaddie):
                        direction = world.get_state(obj)
                        prev_direction = old_world.get_state(obj, direction)

                        direction = ((1.0-t) * prev_direction + t * direction)

                        vert_x1 = int((direction + 1.5) * draw_width / 3)

                        vert_x2 = int((direction + 2.0) * draw_width / 6)

                        pygame.draw.polygon(surface, Color(0,0,0,255),
                                            [(draw_x + vert_x1, draw_y + draw_height / 2),
                                             (draw_x + vert_x2 + draw_width / 3, draw_y + draw_height * 5 / 6),
                                             (draw_x + vert_x1, draw_y + draw_height * 5 / 6),
                                             (draw_x + vert_x2, draw_y + draw_height * 5 / 6),
                                             ])

                elif isinstance(obj, Turret):
                    surface.fill(Color(0,0,255,255), Rect(draw_x+2, draw_y+2, draw_width-4, draw_height-4))

                    cooldown, health = world.get_state(obj, (0, obj.starting_health))

                    if isinstance(obj, DirectionalTurret):
                        marking_width = draw_width * 2 / 5
                        marking_height = draw_height * 2 / 5

                        if obj.direction[0] == -1:
                            marking_x = draw_x
                        elif obj.direction[0] == 0:
                            marking_x = draw_x + (draw_width - marking_width) / 2
                        else:
                            marking_x = draw_x + draw_width - marking_width

                        if obj.direction[1] == -1:
                            marking_y = draw_y
                        elif obj.direction[1] == 0:
                            marking_y = draw_y + (draw_height - marking_height) / 2
                        else:
                            marking_y = draw_y + draw_height - marking_height

                        surface.fill(Color(48,48,48,255), Rect(marking_x, marking_y, marking_width, marking_height), BLEND_ADD)
                    elif isinstance(obj, BishopTurret):
                        if diagonal_pattern_surface is None:
                            diagonal_pattern_surface = pygame.Surface((draw_width, draw_height), HWSURFACE)

                            marking_width = draw_width / 5
                            marking_height = draw_height / 5

                            for dir_x in (-1,1):
                                for dir_y in (-1,1):
                                    if dir_x == -1:
                                        x_pos = (0,
                                                 marking_width,
                                                 marking_width * 2,
                                                 marking_width * 2,
                                                 marking_width,
                                                 0)
                                    else:
                                        x_pos = (draw_width - 1,
                                                 draw_width - 1 - marking_width,
                                                 draw_width - 1 - marking_width * 2,
                                                 draw_width - 1 - marking_width * 2,
                                                 draw_width - 1 - marking_width,
                                                 draw_width - 1)

                                    if dir_y == -1:
                                        y_pos = (0,
                                                 0,
                                                 marking_height,
                                                 marking_height * 2,
                                                 marking_height * 2,
                                                 marking_height)
                                    else:
                                        y_pos = (draw_height - 1,
                                                 draw_height - 1,
                                                 draw_height - 1 - marking_height,
                                                 draw_height - 1 - marking_height * 2,
                                                 draw_height - 1 - marking_height * 2,
                                                 draw_height - 1 - marking_height)

                                    pygame.draw.polygon(diagonal_pattern_surface, Color(48,48,48,255), zip(x_pos, y_pos))

                        surface.blit(diagonal_pattern_surface, (draw_x, draw_y), special_flags=BLEND_ADD)
                    elif isinstance(obj, KnightTurret):
                        pygame.draw.circle(surface, Color(48,48,255,255),
                                           (draw_x + draw_width/2, draw_y + draw_height/2),
                                           (draw_width / 2) - 2)

                        pygame.draw.circle(surface, Color(0,0,255,255),
                                           (draw_x + draw_width/2, draw_y + draw_height/2),
                                           draw_width / 4)

                    #draw stats
                    font = pygame.font.Font(None, draw_height / 3)

                    # cooldown
                    if obj.cooldown > 1:
                        text = font.render("%s/%s" % (cooldown, obj.cooldown)
                            , 1, Color(240, 240, 240, 255))
                        textpos = text.get_rect(centerx=draw_x+draw_width/2, centery=draw_y+draw_height/3)
                        surface.blit(text, textpos)

                    # health
                    text = font.render("%s/%s" % (health, obj.starting_health)
                        , 1, Color(240, 240, 240, 255))
                    if isinstance(obj, DirectionalTurret) and obj.direction == (0, 1):
                        textpos = text.get_rect(centerx=draw_x+draw_width/2, centery=draw_y+draw_height/3)
                    elif isinstance(obj, DirectionalTurret) and obj.direction == (0, -1):
                        textpos = text.get_rect(centerx=draw_x+draw_width/2, centery=draw_y+draw_height*2/3)
                    else:
                        textpos = text.get_rect(centerx=draw_x+draw_width/2, centery=draw_y+draw_height/2)
                    surface.blit(text, textpos)
                elif isinstance(obj, Link):
                    if world.mouse_pos == (obj_x, obj_y):
                        link_color = Color(0,255,0,255)
                    else:
                        link_color = Color(0,128,0,255)
                    surface.fill(link_color, Rect(draw_x+2, draw_y+2, draw_width-4, draw_height-4))

                    font = pygame.font.Font(None, int(draw_height * obj.size))

                    texts = []

                    for line in obj.text.split('\n'):
                        text = font.render(line, 1, Color(0, 0, 0, 255), link_color)
                        texts.append(text)

                    vert_height = sum(line.get_height() for line in texts)

                    text_y = draw_y + (draw_height - vert_height) / 2

                    for line in texts:
                        textpos = line.get_rect(centerx=draw_x+draw_width/2, y=text_y)
                        surface.blit(line, textpos)
                        text_y += textpos.height
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
                        if paused:
                            surface.fill(Color(48,0,0,255), Rect(draw_x+2, draw_y+2, draw_width-4, draw_height-4))
                        else:
                            surface.fill(Color(255,0,0,255), Rect(draw_x+2, draw_y+2, draw_width-4, draw_height-4))
                    elif isinstance(obj, Turret):
                        if paused:
                            surface.fill(Color(0,0,48,255), Rect(draw_x+2, draw_y+2, draw_width-4, draw_height-4))
                        else:
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

    if not paused:
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
            if isinstance(source, Baddie):
                surface.fill(Color(0,255,128,255), Rect(draw_x, draw_y, bullet_width, bullet_height))
            else:
                surface.fill(Color(255,128,0,255), Rect(draw_x, draw_y, bullet_width, bullet_height))

    if not world.click_to_baddie and world.place_turret_cooldown <= world.place_turret_points:
        # draw turret to be placed

        mouse_x, mouse_y = world.mouse_pos

        if mouse_y != 0 and mouse_y != -1 and not isinstance(world.get_object(mouse_x, mouse_y), Link):
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

    if world.help_text and world.help_text_on_top:
        draw_text(surface, world.help_text, 0, 0, int(h / world.height / 2))

def make_hard_game(width, height):
    world = World(width, height)
    world.num_waves = 1
    world.place_turret_cooldown = 4

    return world

def make_insane_game(width, height):
    world = World(width, height)
    world.turret_health_multiplier = 6
    world.place_turret_cooldown = 8
    world.num_waves = 1
    world.next_turret = world.get_random_turret() #FIXME
    world.realtime = True

    return world

def make_normal_game(width, height):
    world = World(width, height)
    world.num_waves = 1

    return world

def make_easy_game(width, height):
    world = World(width, height)
    world.turret_health_multiplier = 5
    world.num_waves = 1
    world.next_turret = world.get_random_turret() #FIXME

    return world

def make_help_world1(width, height):
    world = World(width, height)
    world.place_turret_cooldown = 1
    world.game_ui = False

    world.help_text = """
Click to place a turret.

The red x's show where the new
turret will be able to fire.

Every few turns, a new turret
can be placed.

The types of new turrets are
chosen randomly.

Squares covered by turrets
are brightened."""

    link = Link()
    link.text = "Title"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_title_world
    world.add_object(0, 7, link)

    link = Link()
    link.text = "" # Prev
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world1
    world.add_object(1, 7, link)

    link = Link()
    link.text = "Page\n1 of 5"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world1
    world.add_object(2, 7, link)

    link = Link()
    link.text = "Next"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world2
    world.add_object(3, 7, link)

    link = Link()
    link.text = ""
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world1
    world.add_object(4, 7, link)

    link = Link()
    link.text = "Reset"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world1
    world.add_object(5, 7, link)

    return world

def make_help_world2(width, height):
    world = World(width, height)
    world.click_to_baddie = True
    world.game_ui = False

    world.help_text = """
Click to place an enemy.

Pay attention to how they move.

Enemies will always move in the
direction they face when possible.

Otherwise, they will turn around,
and attempt to move down.

Failing that, they will try to move
to the new direction they face.

Predicting where enemies will go
is very important."""

    link = Link()
    link.text = "Title"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_title_world
    world.add_object(0, 7, link)

    link = Link()
    link.text = "Prev"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world1
    world.add_object(1, 7, link)

    link = Link()
    link.text = "Page\n2 of 5"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world2
    world.add_object(2, 7, link)

    link = Link()
    link.text = "Next"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world3
    world.add_object(3, 7, link)

    link = Link()
    link.text = ""
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world2
    world.add_object(4, 7, link)

    link = Link()
    link.text = "Reset"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world2
    world.add_object(5, 7, link)

    return world

def make_help_world3(width, height):
    world = World(width, height)
    world.click_to_baddie = True
    world.game_ui = False
    world.num_waves = 1
    world.help_text_on_top = True

    world.help_text = """
Enemies appear constantly at the
top of the screen.

When the bottom row is filled
with enemies, the game is lost.

The goal is to survive as long
as possible."""

    link = Link()
    link.text = "Title"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_title_world
    world.add_object(0, 7, link)

    link = Link()
    link.text = "Prev"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world2
    world.add_object(1, 7, link)

    link = Link()
    link.text = "Page\n3 of 5"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world3
    world.add_object(2, 7, link)

    link = Link()
    link.text = "Next"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world4
    world.add_object(3, 7, link)

    link = Link()
    link.text = ""
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world3
    world.add_object(4, 7, link)

    link = Link()
    link.text = "Reset"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world3
    world.add_object(5, 7, link)

    return world

def make_help_world4(width, height):
    world = World(width, height)
    world.place_turret_cooldown = 10000
    world.place_turret_points = 10000
    world.game_ui = False
    world.next_turret = DirectionalTurret()

    world.help_text = """
Enemies move, but turrets do not.

It takes a single turn to fire.

That means that a turret can hit
an enemy only if the enemy WILL
BE in the turret's range next turn.

Enemies will attack your turrets
when they are directly adjacent."""

    link = Link()
    link.text = "Title"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_title_world
    world.add_object(0, 7, link)

    link = Link()
    link.text = "Prev"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world3
    world.add_object(1, 7, link)

    link = Link()
    link.text = "Page\n4 of 5"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world4
    world.add_object(2, 7, link)

    link = Link()
    link.text = "Next"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world5
    world.add_object(3, 7, link)

    link = Link()
    link.text = ""
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world4
    world.add_object(4, 7, link)

    link = Link()
    link.text = "Reset"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world4
    world.add_object(5, 7, link)

    world.add_object(3, 5, MarchingBaddie(), -1)
    world.add_object(4, 4, MarchingBaddie(), -1)

    return world

def make_help_world5(width, height):
    world = World(width, height)
    world.place_turret_cooldown = 0
    world.place_turret_points = 0
    world.realtime = True
    world.game_ui = False
    world.num_waves = 1
    world.help_text_on_top = True

    world.help_text = """
Firing at an enemy will deplete
1 health from the turret.

If a turret is attacked, it will
lose 4 health.

Placing a turret directly on
another object will kill it."""

    link = Link()
    link.text = "Title"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_title_world
    world.add_object(0, 7, link)

    link = Link()
    link.text = "Prev"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world4
    world.add_object(1, 7, link)

    link = Link()
    link.text = "Page\n5 of 5"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world5
    world.add_object(2, 7, link)

    link = Link()
    link.text = "" # Next
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world5
    world.add_object(3, 7, link)

    link = Link()
    link.text = ""
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world5
    world.add_object(4, 7, link)

    link = Link()
    link.text = "Reset"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world5
    world.add_object(5, 7, link)

    return world

def make_title_world(width, height):
    world = World(width, height)
    world.num_waves = 0 # don't spawn enemies
    world.click_to_baddie = True
    world.game_ui = False

    link = Link()
    link.text = "Easy\nGame"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_easy_game
    world.add_object(1, 3, link)

    link = Link()
    link.text = "Normal\nGame"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_normal_game
    world.add_object(2, 4, link)

    link = Link()
    link.text = "Hard\nGame"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_hard_game
    world.add_object(3, 3, link)

    link = Link()
    link.text = "Insane\nGame"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_insane_game
    world.add_object(4, 4, link)

    x = 0
    for char in "Chary":
        link = Link()
        link.text = char
        link.size = 1.0
        link.action = ACTION_NEWWORLD
        link.action_args = make_title_world
        world.add_object(x, 1, link)
        x += 1

    link = Link()
    link.text = "Help"
    link.size = 0.35
    link.action = ACTION_NEWWORLD
    link.action_args = make_help_world1
    world.add_object(1, 6, link)

    link = Link()
    link.text = "Quit"
    link.size = 0.35
    link.action = ACTION_QUIT
    world.add_object(3, 6, link)

    return world

def run(x, y, w, h, game_width, game_height):
    screen = pygame.display.get_surface()
    paused = False
    frame = 0
    pygame.time.set_timer(pygame.USEREVENT, 15)
    timer_activated = True
    waiting_for_player = False

    world = make_title_world(game_width, game_height)
    old_world, world = world, world.advance()

    while True:
        events = pygame.event.get()
        
        if not events:
            events = [pygame.event.wait()]
        
        for event in events:
            if event.type == QUIT:
                return
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    return
                elif event.key == K_PAUSE or event.key == K_p:
                    paused = not paused
            elif event.type == MOUSEBUTTONDOWN:
                press_x = event.pos[0] * world.width / w + x
                press_y = event.pos[1] * world.height / h + y
                if 0 <= press_x < world.width and 0 <= press_y < world.height:
                    world.hover(press_x, press_y)
                    if event.button == 1:
                        if paused:
                            paused = not paused
                        else:
                            res = world.clicked(press_x, press_y)
                            if isinstance(res, Link):
                                if res.action == ACTION_NEWWORLD:
                                    world = res.action_args(game_width, game_height)
                                    old_world, world = world, world.advance()
                                    waiting_for_player = False
                                elif res.action == ACTION_QUIT:
                                    return
                            elif res:
                                waiting_for_player = False
                    elif event.button == 3:
                        if old_world.game_ui:
                            if old_world.lost or paused:
                                world = make_title_world(game_width, game_height)
                                old_world, world = world, world.advance()
                                paused = False
                            else:
                                paused = not paused
            elif paused:
                continue
            elif event.type == pygame.MOUSEMOTION:
                press_x = event.pos[0] * world.width / w + x
                press_y = event.pos[1] * world.height / h + y
                if 0 <= press_x < world.width and 0 <= press_y < world.height:
                    world.hover(press_x, press_y)
            elif event.type == pygame.USEREVENT:
                if world.place_turret_cooldown <= world.place_turret_points and not world.click_to_baddie and not world.lost and not world.realtime and frame % 20 == 19:
                    waiting_for_player = True
                else:
                    frame += 1
                    if frame % 20 == 0:
                        old_world, world = world, world.advance()

        if waiting_for_player:
            temporary_new_world = world.advance(shoot=False)
            draw_world(world, temporary_new_world, 0.0, screen, x, y, w, h, True)
        else:
            draw_world(old_world, world, (frame % 20) / 20.0, screen, x, y, w, h)

        screen.fill(Color(0,0,32,255), Rect(0, h, w, 48))

        if world.game_ui:
            font = pygame.font.Font(None, 48)
            text = font.render(str(old_world.score), 1, Color(240, 240, 240, 255))
            screen.blit(text, (0, h))

        if world.game_ui and pygame.font:
            if paused:
                text = font.render("Paused", 1, Color(240, 240, 240, 255))
                textpos = text.get_rect(centerx=x+w//2, centery=y+h//2)
                screen.blit(text, textpos)
            elif old_world.lost:
                text = font.render("Game Over", 1, Color(240, 240, 240, 255))
                textpos = text.get_rect(centerx=x+w//2, centery=y+h//2)
                screen.blit(text, textpos)
            if paused or old_world.lost:
                text = font.render("Right-click to end", 1, Color(240, 240, 240, 255))
                textpos = text.get_rect(centerx=x+w//2, y=textpos.y + textpos.height)
                screen.blit(text, textpos)

        pygame.display.flip()

        if timer_activated != bool(not paused and not waiting_for_player):
            timer_activated = not timer_activated
            if timer_activated:
                pygame.time.set_timer(pygame.USEREVENT, 15)
            else:
                pygame.time.set_timer(pygame.USEREVENT, 0)

def main():
    game_width = 6
    game_height = 8
    width = game_width * 64
    height = game_height * 64

    pygame.init()

    pygame.display.set_mode((width, height + 48))
    
    run(0, 0, width, height, game_width, game_height)

if __name__ == '__main__':
    main()
