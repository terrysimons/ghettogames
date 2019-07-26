#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import collections
import configparser
import logging

from pygame import Rect
import pygame
import pygame.freetype
import pygame.gfxdraw
import pygame.locals

from ghettogames.color import WHITE, BLACKLUCENT
from ghettogames.engine import RootSprite, RootScene, GameEngine, FontManager
from ghettogames.engine import JoystickManager
from ghettogames.engine import pixels_from_data, pixels_from_path
from ghettogames.engine import image_from_pixels
from ghettogames.engine import rgb_triplet_generator

log = logging.getLogger('game')
log.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

log.addHandler(ch)

class BitmappySprite(RootSprite):
    def __init__(self, *args, filename=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.image = None
        self.rect = None
        self.name = kwargs.get('name', 'Untitled')
        self.filename = filename
        self.width = kwargs.get('width', 0)
        self.height = kwargs.get('height', 0)

        # Try to load a file if one was specified, otherwise
        # if a width and height is specified, make a surface.
        if filename:
            (self.image, self.rect, self.name) = self.load(filename=filename)
        elif self.width and self.height:
            self.image = pygame.Surface((self.width, self.height))
            self.image.convert()
            self.rect = self.image.get_rect()
        else:
            raise Exception(f"Can't create Surface(({self.width}, {self.height})).")

    def load(self, filename):
        """
        """
        config = configparser.ConfigParser(dict_type=collections.OrderedDict,
                                           empty_lines_in_values=True,
                                           strict=True)

        config.read(filename)

        # [sprite]
        # name = <name>
        name = config.get(section='sprite', option='name')
        
        # pixels = <pixels>
        pixels = config.get(section='sprite', option='pixels').split('\n')

        # Set our sprite's length and width.
        width = 0
        height = 0
        index = -1

        # This is a bit of a cleanup in case the config contains something like:
        #
        # pixels = \n
        #  .........
        #
        while not width:
            index += 1            
            width = len(pixels[index])
            height = len(pixels[index:])

        # Trim any dead whitespace.
        # We're off by one since we increment the 
        pixels = pixels[index:]
        
        color_map = {}
        for section in config.sections():
            # This is checking the length of the section's name.
            # Colors are length 1.  This works with unicode, too.
            if len(section) == 1:
                red = config.getint(section=section, option='red')
                green = config.getint(section=section, option='green')
                blue = config.getint(section=section, option='blue')

                color_map[section] = (red, green, blue)

        (image, rect) = self.inflate(width=width,
                                     height=height,
                                     pixels=pixels,
                                     color_map=color_map)

        return (image, rect, name)

    def inflate(self, width, height, pixels, color_map):
        """
        """
        image = pygame.Surface((width, height))
        image.convert()

        raw_pixels = []
        for y, row in enumerate(pixels):
            for x, pixel in enumerate(row):
                color = color_map[pixel]
                raw_pixels.append(color)
                pygame.draw.rect(image, color, (x, y, 1, 1))

        return (image, image.get_rect())
    
    def save(self, filename):
        """
        """
        config = self.deflate()
        
        with open(filename, 'w') as deflated_sprite:
            config.write(deflated_sprite)

    def deflate(self):
        config = configparser.ConfigParser(dict_type=collections.OrderedDict,
                                           empty_lines_in_values=True,
                                           strict=True)
        
        # Get the set of distinct pixels.
        color_map = {}
        pixels = []

        raw_pixels = rgb_triplet_generator(
            pixel_data=pygame.image.tostring(self.image, 'RGB')
        )

        # We're utilizing the generator to give us RGB triplets.
        # We need a list here becasue we'll use set() to pull out the
        # unique values, but we also need to consume the list again
        # down below, so we can't solely use a generator.
        raw_pixels = [raw_pixel for raw_pixel in raw_pixels]

        # This gives us the unique rgb triplets in the image.
        colors = set(raw_pixels)

        config.add_section('sprite')
        config.set('sprite', 'name', self.name)

        # Generate the color key
        color_key = chr(47)
        for i, color in enumerate(colors):
            # Characters above doublequote.
            color_key = chr(ord(color_key) + 1)
            config.add_section(color_key)

            color_map[color] = color_key

            log.debug(f'Key: {color} -> {color_key}')
            
            red = color[0]
            config.set(color_key, 'red', str(red))
            
            green = color[1]
            config.set(color_key, 'green', str(green))
            
            blue = color[2]
            config.set(color_key, 'blue', str(blue))

        x = 0
        row = []
        while raw_pixels:
            row.append(color_map[raw_pixels.pop(0)])
            x += 1

            if x % self.rect.width == 0:
                log.debug(f'Row: {row}')
                pixels.append(''.join(row))
                row = []
                x = 0

        log.debug(pixels)

        config.set('sprite', 'pixels', '\n'.join(pixels))

        log.debug(f'Deflated Sprite: {config}')

        return config

class TextBoxSprite(BitmappySprite):
    """
    """

    def __init__(self, *args, **kwargs):
        self.value = None
        self.text = None
        self.name = None
        self.background_color = (0, 0, 0)
        self.border_width = 1

        super().__init__(*args, **kwargs)

        self.name = kwargs.get('name', 'Untitled')
        self.background_color = (0, 0, 0)

        self.callbacks = kwargs.get('callbacks', None)

        self.rect = self.image.get_rect()

        self.text = TextSprite(background_color=self.background_color, x=0, y=0, width=self.width, height=self.height, text=self.value)

    def update(self):
        if self.text:
            self.text.rect.center = self.rect.center

            self.text.background_color = self.background_color
            self.text.dirty = 2
            self.text.update()

            self.image.blit(self.text.image, (0, 0, self.width, self.height))

        if self.border_width:
            pygame.draw.rect(self.image, (128, 128, 128), Rect(0, 0, self.width, self.height), self.border_width)

    def on_left_mouse_button_down_event(self, event):
        self.dirty = 1
        self.background_color = (128, 128, 128)
        self.update()

    def on_left_mouse_button_up_event(self, event):
        self.dirty = 1
        self.background_color = (0, 0, 0)
        self.update()


class ColorWellSprite(BitmappySprite):
    def __init__(self, *args, **kwargs):
        self.name = kwargs.get('name', 'Untitled')
        self.red = 0
        self.green = 0
        self.blue = 0
        self._dirty = 1
        self.text_sprite = TextBoxSprite(name=str(self.active_color), width=100, height=20)
        self.text_sprite.border_width = 0
        super().__init__(*args, **kwargs)

    @property
    def dirty(self):
        return self._dirty
        
    @dirty.setter
    def dirty(self, value):
        self._dirty = value
        self.text_sprite.dirty = value

    @property
    def active_color(self):
        return (self.red, self.green, self.blue)

    @active_color.setter
    def active_color(self, active_color):
        self.red = active_color[0]
        self.green = active_color[1]
        self.blue = active_color[2]
        self.dirty = 1

    @property
    def hex_color(self):
        hex_str = '{:02X}'
        red, green, blue = self.active_color

        red = hex_str.format(red)
        green = hex_str.format(green)
        blue = hex_str.format(blue)
        
        return f'#{red}{green}{blue}'

    def update(self):
        self.text_sprite.rect.midleft = self.rect.midright        
        pygame.draw.rect(self.image, (128, 128, 128), Rect(0, 0, self.width, self.height), 1)
        pygame.draw.rect(self.image, self.active_color, Rect(1, 1, self.width - 2, self.height - 2))
        self.text_sprite.value = str(self.active_color)
        self.text_sprite.text.text = self.hex_color
        self.text_sprite.text.text_box.start_x = 5
        self.text_sprite.text.text_box.start_y = 0#self.text_sprite.width//2
        self.text_sprite.update()
        #print(f'{self.name}: {self.active_color}')


        self.screen.blit(self.text_sprite.image, (self.text_sprite.rect.x, self.text_sprite.rect.y))

    def add(self, *groups):
        super().add(*groups)
        import pdb; pdb.set_trace()
        self.text_sprite.add(self.groups())

    def remove(self, *groups):
        super().add(*groups)
        self.text_sprite.remove(self.groups())

class ButtonSprite(BitmappySprite):
    """
    """

    def __init__(self, *args, **kwargs):
        self.text = None
        self.name = None
        self.background_color = (0, 0, 0)

        super().__init__(*args, **kwargs)

        self.name = kwargs.get('name', 'Untitled')
        self.background_color = (0, 0, 0)

        self.callbacks = kwargs.get('callbacks', None)

        self.rect = self.image.get_rect()
        self.rect.x = self.x
        self.rect.y = self.y

        self.text = TextSprite(background_color=self.background_color, x=0, y=0, width=self.width, height=self.height, text=self.name)

    def update(self):
        if self.text:
            self.text.rect.center = self.rect.center

            self.text.background_color = self.background_color
            self.text.update()

            self.image.blit(self.text.image, (0, 0, self.width, self.height))

        pygame.draw.rect(self.image, (128, 128, 128), Rect(0, 0, self.width, self.height), 1)

    def on_left_mouse_button_down_event(self, event):
        self.dirty = 1
        self.background_color = (128, 128, 128)
        self.update()
        super().on_left_mouse_button_down_event(event)

    def on_left_mouse_button_up_event(self, event):
        self.dirty = 1
        self.background_color = (0, 0, 0)
        self.update()
        super().on_left_mouse_button_up_event(event)      

class CheckboxSprite(ButtonSprite):
    """
    """

    def __init__(self, *args, **kwargs):
        self.checked = False
        self.color = (128, 128, 128)

        super().__init__(*args, **kwargs)

    def update(self):
        if not self.checked:
            self.image.fill((0, 0, 0))

        pygame.draw.rect(self.image, self.color, Rect(0, 0, self.width, self.height), 1)

        if self.checked:
            pygame.draw.line(self.image, self.color, (0, 0), (self.width - 1, self.height - 1), 1)
            pygame.draw.line(self.image, self.color, (0, self.height - 1), (self.width - 1, 0), 1)

        self.rect.x = self.x
        self.rect.y = self.y

    def on_left_mouse_button_down_event(self, event):
        pass

    def on_left_mouse_button_up_event(self, event):
        self.dirty = 1
        self.checked = not self.checked
        self.update()



class ScrollBarSprite(BitmappySprite):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def update(self):
        pass

class ResizeWidgetSprite(BitmappySprite):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def update(self):
        self.dirty = 2
        self.image.fill((255, 255, 255))

    def on_left_mouse_button_down_event(self, event):
        pass

class CanvasSprite(BitmappySprite):
    def __init__(self, *args, has_mini_view=True, **kwargs):
        self.character_sprite = False
        self.color = (128, 128, 128)
        self.grid_color = (255, 255, 0)

        self.border_thickness = 0
        self.border_margin = 0
        self.pixels_across = 32
        self.pixels_tall = 32
        self.pixels = [(255, 0, 255)] * self.pixels_across * self.pixels_tall
        self.grid_line_width = 0
        self.pixel_boxes = []
        self.pixel_width = 1
        self.pixel_height = 1
        self.has_mini_view = has_mini_view
        self.mini_view = None
        self.resize_widget = None
        self.active_color = (255, 255, 255)
        self.dirty = 2

        class MiniView(CanvasSprite):
            def __init__(self, *args, border_thickness=0, pixels=None, **kwargs):
                self.pixels = pixels
                self.dirty_pixels = [True] * len(self.pixels)

                super().__init__(*args, has_mini_view=False, **kwargs)

                self.name = "Mini View"
                self.pixel_width = 2
                self.pixel_height = 2
                self.width = self.pixels_across * self.pixel_width
                self.height = self.pixels_tall * self.pixel_height
                self.border_thickness = 0
                self.border_margin = 0

                self.grid_line_width = 0

                self.image = pygame.Surface((self.width, self.height))
                self.rect = self.image.get_rect()
                self.image.fill((0, 255, 0))
                self.image.set_colorkey((255, 0, 255))
                self.rect.x = self.screen_width - self.width
                self.rect.y = 0
                self.rect.width = self.width
                self.rect.height = self.height

                # Update our pixel boxes.
                #for pixel_box in self.pixel_boxes:
                #    pixel_box.border_thickness = 0
                #    print(f'Pixel Width: {pixel_box.width}')
                self.dirty_pixels = [True] * len(self.pixels)

            def update(self):
                self.dirty = 2
                x = 0
                y = 0

                for i, pixel in enumerate(self.pixels):
                    if self.dirty_pixels[i]:
                        if pixel == (255, 0, 255):
                            pygame.draw.rect(self.image, (0, 255, 0), ((x, y), (self.pixel_width, self.pixel_height)))
                        else:
                            pygame.draw.rect(self.image, pixel, ((x, y), (self.pixel_width, self.pixel_height)))
                            #print(f'Updated pixel {i}')

                        self.dirty_pixels[i] = False                            

                    if (x + self.pixel_width) % (self.pixels_across * self.pixel_width) == 0:
                        x = 0
                        y += self.pixel_height
                    else:
                        x += self.pixel_width
                        
                self.screen.blit(self.image, (self.rect.x, self.rect.y))
                #super().update()
                #pygame.draw.line(self.screen, (255, 0, 0), (0, 0), (240, 240))

            #def on_pixel_update_event(self, event, trigger):
            #    self.pixels[trigger.pixel_number] = trigger.pixel_color
            #    self.dirty_pixels[trigger.pixel_number] = True
            #    self.dirty = 2
            #    self.update()

            def __str__(self):
                return f'pixels across: {self.pixels_across}, pixels tall: {self.pixels_tall}, width: {self.width}, height: {self.height}, pixel width: {self.pixel_width}, pixel_height: {self.pixel_height}, pixels: {len(self.pixels)}, rect: {self.rect}'

        class BitmapPixelSprite(BitmappySprite):
            """
            """

            def __init__(self, *args, border_thickness=1, **kwargs):
                self.name = kwargs.get('name')
                self.pixel_number = kwargs.get('pixel_number')
                self.pixel_width = kwargs.get('width', 1)
                self.pixel_height = kwargs.get('height', 1)
                self.border_thickness = 1
                self.width = self.pixel_width
                self.height = self.pixel_height
                self.color = (96, 96, 96)
                self.pixel_color = (0, 0, 0)

                # Check
                #if self.pixel_width == 0:
                #    self.pixel_width = 4
                    #raise Exception('Pixel Width == 0')

                #if self.pixel_height == 0:
                #    self.pixel_height = 4
                    #raise Exception('Pixel Height == 0')                

                super().__init__(self, *args, width=self.width, height=self.height)

                #print(f'Width: {self.width}, Height: {self.height}')
                #print(f'Pixel Number: {self.pixel_number}')                    

                self.rect = pygame.Rect(0, 0, self.width, self.height)
                self.rect = pygame.draw.rect(self.image, self.color, (0, 0, self.width, self.height), 0)
                    
 
                #-                pygame.draw.rect(self.image, self.pixel_color, (1, 1, self.width - self.border_thickness * 2, self.height - self.border_thickness 
                

            def update(self):
                self.dirty = 2
                #pygame.draw.rect()
                #pygame.draw.rect(self.image, self.pixel_color, (self.border_thickness, self.border_thickness, self.width - self.border_thickness, self.height - self.border_thickness))                
                pygame.draw.rect(self.image, self.pixel_color, (0, 0, self.width, self.height))
                
                # Store this as an image and blit for a speedup.
                if self.border_thickness:
                    pygame.draw.rect(self.image, self.color, (0, 0, self.width, self.height), self.border_thickness)                

            def on_pixel_update_event(self, event):
                callback = None
                
                if self.callbacks:
                    callback = self.callbacks.get('on_pixel_update_event', None)

                if callback:
                    callback(event=event, trigger=self)
                #else:
                #    log.debug(f'{type(self)}: Pixel Update Event: {event} @ {self} (Pixel Number: {self.pixel_number}')

            def on_left_mouse_button_down_event(self, event):
                self.dirty = 2
                self.on_pixel_update_event(event)
                self.update()

            def on_mouse_drag_down_event(self, event, trigger):
                # There's not a good way to pass any useful info, so for now, pass None
                # since we're not using the event for anything in this class.
                self.on_left_mouse_button_down_event(None)

        super().__init__(*args, **kwargs)

        self.name = 'Bitmap Canvas'

        self.pixel_width = self.width//self.pixels_across - self.border_thickness * 2 #(self.width - self.border_margin - self.border_thickness - self.pixels_across) // self.pixels_across
        self.pixel_height = self.width//self.pixels_across - self.border_thickness * 2# (self.height - self.border_margin - self.border_thickness - self.pixels_tall) // self.pixels_tall
        print(f'Pixels Across: {self.pixels_across}')
        print(f'Pixels Tall: {self.pixels_tall}')
        print(f'')

        #self.pixels = pixels_from_path(path='resources/flower_tile1_32.raw', width=32, height=32)

        self.all_sprites = pygame.sprite.LayeredDirty()

        self.pixel_boxes = [BitmapPixelSprite(name=f'pixel {i}',
                                              pixel_number=i,
                                              x=0,
                                              y=0,
                                              height=self.pixel_width,
                                              width=self.pixel_height)
                                              for i in range(self.pixels_across * self.pixels_tall)]

        for i in range(self.pixels_across * self.pixels_tall):
            self.pixel_boxes[i].pixel_color = self.pixels[i]
            self.pixel_boxes[i].add(self.all_sprites)

            # This allows us to update the mini map.
            self.pixel_boxes[i].callbacks = {'on_pixel_update_event': self.on_pixel_update_event}

            # This draws the map box.
            self.pixel_boxes[i].dirty = 1
            self.pixel_boxes[i].update()

        if self.has_mini_view:
            self.mini_view = MiniView(pixels=self.pixels, width=self.pixels_across, height=self.pixels_tall)
            self.mini_view.pixels = self.pixels
            self.mini_view.rect.x = self.screen_width - self.mini_view.width
            self.mini_view.rect.y = 0
            self.mini_view.add(self.all_sprites)
            #self.mini_view.dirty = 1

        # Draw 4 squares around the screen.
        # Green
        # Blue
        # Yellow
        # Red
        self.quadrants = [pygame.Surface((self.screen_width//2, self.screen_height//2))]

        

        # Set up our resize widget.
        #self.resize_widget = ResizeWidgetSprite(width=16, height=16)
        #self.resize_widget.rect.bottomright = self.rect.bottomright
        #self.resize_widget.dirty = 2
        #self.resize_widget.update()

        # Do some cleanup
        # For some reason we have a double grid border, so let's wipe out the canvas.
        self.dirty = 2                        
        self.image.fill((0, 0, 0), rect=self.rect)
        self.update()

    def on_pixel_update_event(self, event, trigger):
        if self.mini_view:
            self.mini_view.pixels[trigger.pixel_number] = trigger.pixel_color

            # Note: Shouldn't we
            self.mini_view.dirty_pixels[trigger.pixel_number] = True
            #self.mini_view.on_pixel_update_event(event, trigger)            

        if self.pixel_boxes[trigger.pixel_number].pixel_color == trigger.pixel_color:
            # This prevents us from updating the pixel if it's already the same color.
            pass
        else:
            #print(f'Pixel Update: {event}, {trigger} Pixel Number: {trigger.pixel_number}, {self.pixel_boxes[trigger.pixel_number].pixel_color} -> {trigger.pixel_color}')            
            self.pixel_boxes[trigger.pixel_number].pixel_color = trigger.pixel_color            
            self.pixel_boxes[trigger.pixel_number].dirty = 2
            self.dirty = 1
            self.update()
            self.pixel_boxes[trigger.pixel_number].update()

    def update(self):
        self.dirty = 2
        if not self.mini_view:
            #self.draw_border()
            self.draw_pixels()
        else:
            # self.border.update()
            # self.grid.update()
            # self.pixels.update()
            #self.draw_border()
            self.draw_grid()
            self.draw_pixels()
            self.mini_view.update()

            #self.resize_widget.rect.bottomright = (32, 32)
            #self.image.blit(self.resize_widget.image, self.resize_widget.rect.bottomright)

        #if self.mini_view:
            #self.mini_view.pixels = [pixel_box.pixel_color for pixel_box in self.pixel_boxes]
        #   self.mini_view.update()
            #print(pygame.image.tostring(self.mini_view.image, 'RGB'))
            #print(pygame.image.tostring(self.image, 'RGB'))
            #self.image.blit(self.mini_view.image, (0, 0))
            #print(f'BLIT: {self.mini_view}')
            #print(f'{self}')

    def draw_pixels(self):
        [pixel_box.update() for pixel_box in self.pixel_boxes]

    def draw_grid(self):
        # Note: We should do this instead.
        # self.grid.update()
        
        x = 0
        y = 0
        self.border_thickness = 0
        self.border_margin = 0
        for i, pixel_box in enumerate(self.pixel_boxes):
            pixel_x = x * pixel_box.pixel_width
            pixel_y = y * pixel_box.pixel_height
            #pixel_x = self.border_margin + self.border_thickness + (x * pixel_box.pixel_width) + (x * pixel_box.border_thickness)
            #pixel_y = self.border_margin + self.border_thickness + (y * pixel_box.pixel_height) + (y * pixel_box.border_thickness)

            # Note: We might be able to do this up above, and make this method super efficient.
            pixel_box.rect.x = pixel_x
            pixel_box.rect.y = pixel_y

            self.image.blit(pixel_box.image, (pixel_x, pixel_y))

            if (x + 1) % self.pixels_across == 0:
                x = 0
                y += 1
            else:
                x += 1

    def draw_border(self):
        pygame.draw.rect(self.image,
                         self.color,
                         Rect(
                              0,
                              0,
                              self.pixel_width * self.pixels_across + self.pixels_across + ((self.border_margin * 2) + (self.border_thickness * 2)) ,
                              self.pixel_height * self.pixels_tall + self.pixels_tall + ((self.border_margin * 2) + (self.border_thickness * 2)) 
                             ),
                              self.border_thickness)

    #def load_image(self, path):
    #    return pixels_from_path(path=path, width=32, height=32)

    def on_left_mouse_button_down_event(self, event):
        # Check for a sprite collision against the mouse pointer.
        #
        # First, we need to create a pygame Sprite that represents the tip of the mouse.
        mouse = MouseSprite(x=event.pos[0],y=event.pos[1] , width=1, height=1)

        collided_sprites = pygame.sprite.spritecollide(mouse, self.all_sprites, False)

        #print(f'collided sprites: {collided_sprites}')

        for sprite in collided_sprites:
            sprite.pixel_color = self.active_color
            sprite.on_left_mouse_button_down_event(event)

        #print(f'Mouse @ {mouse.rect}')
        self.dirty = 1
        self.update()

    def on_mouse_drag_down_event(self, event, trigger):
        # Check for a sprite collision against the mouse pointer.
        #
        # First, we need to create a pygame Sprite that represents the tip of the mouse.
        #mouse = MouseSprite(x=event.pos[0],y=event.pos[1] , width=1, height=1)

        self.on_left_mouse_button_down_event(event)

        #collided_sprites = pygame.sprite.spritecollide(mouse, self.all_sprites, False)

        #print(f'collided sprites: {collided_sprites}')

        #for sprite in collided_sprites:
        #    sprite.on_mouse_drag_down_event(event, trigger)

        #print(f'Mouse @ {mouse.rect}')
        #self.dirty = 1
        #self.update()

    def on_new_file_event(self, event, trigger):        
        for i, pixel in enumerate([(255, 0, 255)] * self.pixels_across * self.pixels_tall):
            event = pygame.event.Event(GameEngine.GAMEEVENT, {'action':'on_load_file_event',
                                                              'pixel_color': pixel,
                                                              'pixel_number': i})

            # Create a pixel update event for the mini map.
            self.on_pixel_update_event(event=event, trigger=event)

        self.dirty = 2
        self.update()

        self.mini_view.dirty = 2
        self.mini_view.update()        

    def on_save_file_event(self, event, trigger):
        pixels = []
        
        for pixel_box in self.pixel_boxes:
            pixels.append(pixel_box.pixel_color)

        # Generate a new bitmappy sprite and tell it to save.
        save_sprite = BitmappySprite(width=self.pixels_across,
                                     height=self.pixels_tall,
                                     name='Tiley McTile Face')

        save_sprite.image = image_from_pixels(pixels=pixels,
                                              width=save_sprite.width,
                                              height=save_sprite.height)

        save_sprite.save(filename='savefile.cfg')

        self.save(filename='screenshot.cfg')
            

    def on_load_file_event(self, event, trigger):
        load_sprite = BitmappySprite(filename='savefile.cfg',
                                     width=self.pixels_across,
                                     height=self.pixels_tall)

        pixel_data = pygame.image.tostring(load_sprite.image, 'RGB')

        pixels = pixels_from_data(pixel_data=pixel_data)


        # Update the canvas' pixels across and tall
        self.pixels_across = load_sprite.width
        self.pixels_tall = load_sprite.height

        # pixels = [pixel_box.pixel_color for pixel_box in self.pixel_boxes]
        #pixels = [(255, 255, 255)] * 1024

        #print(pixels)

        for i, pixel in enumerate(pixels):
            trigger.pixel_number = i
            trigger.pixel_color = (255, 255, 255)

            event = pygame.event.Event(GameEngine.GAMEEVENT, {'action':'on_load_file_event',
                                                              'pixel_color': pixels[i],
                                                              'pixel_number': i})

            # Create a pixel update event for the mini map.
            self.on_pixel_update_event(event=event, trigger=event)

            #self.update()
        #self.dirty = 1
        #self.dirty = 1
        #self.mini_view.dirty = 1
        #self.mini_view.update()
        #self.update()

        self.dirty = 2
        self.update()

        self.mini_view.dirty = 2
        self.mini_view.update()        

class TextSprite(RootSprite):
    def __init__(self, *args, background_color=BLACKLUCENT, alpha=0, text='Text', **kwargs):
        self.background_color = (0, 0, 0)
        self.alpha = 0
        self.text = text
        self.font_manager = FontManager(self)
        self.joystick_manager = JoystickManager(self)
        self.joystick_count = len(self.joystick_manager.joysticks)

        class TextBox(object):
            def __init__(self, font_controller, x, y, line_height=15, text='Text'):
                self.image = None
                self.rect = None
                self.start_x = x
                self.start_y = y
                self.line_height = line_height

                super().__init__()


                pygame.freetype.set_default_resolution(font_controller.font_dpi)
                self.font = pygame.freetype.SysFont(name=font_controller.font,
                                                    size=font_controller.font_size)

            def print(self, surface, string):
                (self.image, self.rect) = self.font.render(string, WHITE)
                
                #pygame.draw.rect(self.image, (255, 255, 0), self.rect, 0)

                surface.blit(self.image, (self.x, self.y))
                self.rect.x = self.x
                self.rect.y = self.y
                self.y += self.line_height

            def reset(self):
                self.x = self.start_x
                self.y = self.start_y

            def indent(self):
                self.x += 10

            def unindent(self):
                self.x -= 10

        self.text_box = TextBox(font_controller=self.font_manager, x=0, y=0, text=self.text)

        super().__init__(*args, **kwargs)

        self.text_box.start_x = self.rect.centerx - 10
        self.text_box.start_y = self.rect.centery - 5


        self.background_color = background_color
        self.alpha = alpha

        if not alpha:
            #self.image.set_colorkey(self.background_color)
            self.image.convert()
        else:
            # Enabling set_alpha() and also setting a color
            # key will let you hide the background
            # but things that are blited otherwise will
            # be translucent.  This can be an easy
            # hack to get a translucent image which
            # does not have a border, but it causes issues
            # with edge-bleed.
            #
            # What if we blitted the translucent background
            # to the screen, then copied it and used the copy
            # to write the text on top of when translucency
            # is set?  That would allow us to also control
            # whether the text is opaque or translucent, and
            # it would also allow a different translucency level
            # on the text than the window.
            self.image.convert_alpha()
            self.image.set_alpha(self.alpha)

        self.rect = self.image.get_rect()
        self.rect.x += self.x
        self.rect.y += self.y

        

        self.update()

    def update(self):
        self.dirty = 2
        self.image.fill(self.background_color)

        self.text_box.reset()
        self.text_box.print(self.image, f'{self.text}')

class SliderSprite(BitmappySprite):
    def __init__(self, *args, **kwargs):
        self.name = kwargs.get('name', 'Untitled')                
        self.height = kwargs.get('height')
        self.width = kwargs.get('width')
        self.x = kwargs.get('x')
        self.y = kwargs.get('y')
        self.text = TextSprite(background_color=(255, 0, 0), x=0, y=0, width=0, height=self.height, text=self.name)

        self.width = self.text.width + self.width + 20
        self.height = self.text.height + self.height


        class SliderKnobSprite(BitmappySprite):
            def __init__(self, *args, **kwargs):
                self.name = kwargs.get('name', 'Untitled')
                self.value = 0

                super().__init__(*args, **kwargs)

                #self.image.set_colorkey((0, 0, 0))
                self.image.fill((0, 0, 0))

                self.rect = Rect(1, 1, self.width - 2, self.height - 2)

                self.update()

            def update(self):
                pygame.draw.rect(self.image, (127, 127, 127), self.rect)  
                #pygame.draw_rect(self.image, (0, 0, 0))

            def on_left_mouse_button_down_event(self, event):
                self.dirty = 1
                self.value = event.pos[0]

                # Hack            
                if self.value > 255:
                    self.value = 255
                elif self.value < 0:
                    self.value = 0
                
                self.rect.x = self.value
                self.update()
                super().on_left_mouse_button_down_event(event)

            def on_mouse_drag_down_event(self, event, trigger):
                # There's not a good way to pass any useful info, so for now, pass None
                # since we're not using the event for anything in this class.
                self.on_left_mouse_button_down_event(event)

        self.slider_knob = SliderKnobSprite(name=self.name, width=self.height//2, height=self.height//2)

        super().__init__(height=self.height, width=self.width, x=self.x, y=self.y)

        self.name = kwargs.get('name', 'Untitled')        

        # This is the stuff pygame really cares about.
        self.image = pygame.Surface((self.width, self.height))
        self.background = pygame.Surface((self.width, self.height))
        self.image.fill((255,255,255))
        self.rect = self.image.get_rect()

        self.image.blit(self.text.image, (0, 0))
        self.rect.x = self.x
        self.rect.y = self.y
        self.text.start_x = 0
        self.text.start_y = 0

        #self.all_sprites = pygame.sprite.LayeredDirty((self.slider_knob))

    @property
    def value(self):
        return self.slider_knob.value

    @value.setter
    def value(self, value):
        log.info('SLIDER')
        self.slider_knob.value = value

    def update(self):
        #pygame.draw.rect(self.image, (255, 0, 0), Rect(self.rect.centerx, self.rect.centery, self.rect.width, self.rect.height), 1)

        self.image.fill((0, 0, 0))

        color = (255, 255, 255)
        
        for i in range(256):
            color = (i, i, i)
            
            if self.name == 'R':
                color = (i, 0, 0)
            elif self.name == 'G':
                color = (0, i, 0)
            elif self.name == 'B':
                color = (0, 0, i)
                
            pygame.draw.line(self.image,
                             color,
                             (self.text.width + i, self.height//2 - 1),
                             (self.text.width + i, self.height//2), 1)
                
            pygame.draw.line(self.image,
                             color,
                             (self.text.width + i, self.height//2),
                             (self.text.width + i, self.height//2), 1)
                
            pygame.draw.line(self.image,
                             color,
                             (self.text.width + i,
                              self.height//2 + 1),
                             (self.text.width + i, self.height//2), 1)

        # Draw the knob
        self.image.blit(self.slider_knob.image, (self.slider_knob.value, self.rect.height//4))
        super().update()


    def on_left_mouse_button_down_event(self, event):
        self.dirty = 1

        log.debug('Calling Slider Knob Callback')
        self.slider_knob.on_left_mouse_button_down_event(event)
        self.update()
        super().on_left_mouse_button_down_event(event)

    def on_mouse_drag_down_event(self, event, trigger):
        self.dirty = 1
        self.on_left_mouse_button_down_event(event)
        # There's not a good way to pass any useful info, so for now, pass None
        # since we're not using the event for anything in this class.
        #self.slider_knob.on_mouse_drag_down_event(event, trigger)
        #self.update()
        #super().on_mouse_drag_down_event(event)        
        

class LabeledSliderSprite(SliderSprite):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class MouseSprite(BitmappySprite):
    def __init__(self, *args, **kwargs):
        self.x = kwargs.get('x')
        self.y = kwargs.get('y')

        super().__init__(*args, **kwargs)

        self.rect.x = self.x
        self.rect.y = self.y

class BitmapEditorScene(RootScene):
    def __init__(self):
        super().__init__()
        self.screen = pygame.display.get_surface()
        self.screen_width = self.screen.get_width()
        self.screen_height = self.screen.get_height()
        self.button_width = 75

        self.scroll_bar_sprite = ScrollBarSprite(name='File List', x=0, y=0, width=20, height=300)

        # We'll use the top left quartile of the screen to draw the canvas.
        # We want a square canvas, so we'll use the height as our input.
        self.canvas_sprite = CanvasSprite(name='Bitmap Canvas', x=0, y=0, width=int(self.screen_height * 0.75), height=int(self.screen_height * 0.75))
        self.new_button_sprite = ButtonSprite(name='New', x=self.screen_width - self.button_width, y=219, width=self.button_width, height=20)

        self.new_button_sprite.callbacks = {'on_left_mouse_button_down_event': self.on_new_file_event}

        self.save_button_sprite = ButtonSprite(name='Save', x=self.screen_width - self.button_width, y=249, width=self.button_width, height=20)

        self.save_button_sprite.callbacks = {'on_left_mouse_button_down_event': self.on_save_file_event}

        self.load_button_sprite = ButtonSprite(name='Load', x=self.screen_width - self.button_width, y=279, width=self.button_width, height=20)

        self.load_button_sprite.callbacks = {'on_left_mouse_button_down_event': self.on_load_file_event}

        self.quit_button_sprite = ButtonSprite(name='Quit', x=self.screen_width - self.button_width, y=309, width=self.button_width, height=20)

        self.quit_button_sprite.callbacks = {'on_left_mouse_button_down_event': self.on_quit_event}

        self.red_slider_sprite = LabeledSliderSprite(name='R', x=0, y=self.screen_height - 70, width=256, height=10)

        self.red_slider_sprite.callbacks = {'on_left_mouse_button_down_event': self.on_slider_event}

        self.green_slider_sprite = LabeledSliderSprite(name='G', x=0, y=self.screen_height - 50, width=256, height=10)

        self.green_slider_sprite.callbacks = {'on_left_mouse_button_down_event': self.on_slider_event}

        self.blue_slider_sprite = LabeledSliderSprite(name='B', x=0, y=self.screen_height - 30, width=256, height=10)

        self.blue_slider_sprite.callbacks = {'on_left_mouse_button_down_event': self.on_slider_event}

        self.color_well_sprite = ColorWellSprite(name='Colorwell', x=0, y=0, width=64, height=64)

        self.color_well_sprite.rect.midleft = self.green_slider_sprite.rect.midright
        self.color_well_sprite.rect.x += 15

        self.red = self.red_slider_sprite.value
        self.green = self.green_slider_sprite.value
        self.blue = self.blue_slider_sprite.value

        self.canvas_sprite.active_color = (self.red, self.green, self.blue)

        self.all_sprites = pygame.sprite.LayeredDirty(
            (
                #self.scroll_bar_sprite,
                self.canvas_sprite,
                self.canvas_sprite.mini_view,
                #self.canvas_sprite.resize_widget,
                self.new_button_sprite,
                self.save_button_sprite,
                self.load_button_sprite,
                self.quit_button_sprite,
                self.red_slider_sprite,
                self.blue_slider_sprite,
                self.green_slider_sprite,
                self.color_well_sprite,
                self.color_well_sprite.text_sprite
                #self.checkbox_sprite
            )
        )

        self.all_sprites.clear(self.screen, self.background)

    def update(self):
        super().update()

    def render(self, screen):
        super().render(screen)

    def switch_to_scene(self, next_scene):
        super().switch_to_scene(next_scene)

    def on_new_file_event(self, event, trigger):
        log.info(f'New File: event: {event}, trigger: {trigger}')
        self.canvas_sprite.on_new_file_event(event, trigger)

    def on_load_file_event(self, event, trigger):
        log.info(f'Load File: event: {event}, trigger: {trigger}')
        self.canvas_sprite.on_load_file_event(event, trigger)

    def on_save_file_event(self, event, trigger):
        log.info(f'Safe File: event: {event}, trigger: {trigger}')
        self.canvas_sprite.on_save_file_event(event, trigger)

    def on_slider_event(self, event, trigger):
        value = trigger.value

        if value < 0:
            value = 0
            trigger.value = 0
        elif value > 255:
            value = 255
            trigger.value = 255
            log.info(f'Slider: event: {event}, trigger: {trigger} value: {value}')            
        
        if trigger.name == 'R':
            self.red = value
        elif trigger.name == 'G':
            self.green = value
        elif trigger.name == 'B':
            self.blue = value
        #else:


        self.canvas_sprite.active_color = (self.red, self.green, self.blue)
        self.canvas_sprite.dirty = 2
        self.canvas_sprite.update()

        self.color_well_sprite.active_color = (self.red, self.green, self.blue)
        self.color_well_sprite.dirty = 1
        self.color_well_sprite.update()


    def on_key_up_event(self, event):
        # 1-8 selects Sprite Frame
        # Spacebar
        # Escape quits
        # c cycles through color boxes
        # r swap recent colors
        # n new bitmap
        # l load bitmap
        # s save bitmap
        pass

    def on_key_down_event(self, event):
        pass

    def on_right_mouse_button_down_event(self, event):
        pass

    def on_left_mouse_button_down_event(self, event):
        # Check for a sprite collision against the mouse pointer.
        #
        # First, we need to create a pygame Sprite that represents the tip of the mouse.
        mouse = MouseSprite(x=event.pos[0],y=event.pos[1] , width=1, height=1)

        collided_sprites = pygame.sprite.spritecollide(mouse, self.all_sprites, False)

        for sprite in collided_sprites:
            sprite.on_left_mouse_button_down_event(event)

        #print(f'Mouse @ {mouse.rect}')

    def on_left_mouse_button_up_event(self, event):
        # Check for a sprite collision against the mouse pointer.
        #
        # First, we need to create a pygame Sprite that represents the tip of the mouse.
        mouse = MouseSprite(x=event.pos[0],y=event.pos[1] , width=1, height=1)

        collided_sprites = pygame.sprite.spritecollide(mouse, self.all_sprites, False)

        for sprite in collided_sprites:
            sprite.on_left_mouse_button_up_event(event)

        #print(f'Mouse @ {mouse.rect}')

    def on_mouse_drag_down_event(self, event, trigger):
        # Check for a sprite collision against the mouse pointer.
        #
        # First, we need to create a pygame Sprite that represents the tip of the mouse.
        mouse = MouseSprite(x=event.pos[0],y=event.pos[1] , width=1, height=1)

        collided_sprites = pygame.sprite.spritecollide(mouse, self.all_sprites, False)

        for sprite in collided_sprites:
            sprite.on_mouse_drag_down_event(event, trigger)

        #print(f'Mouse Drag @ {mouse.rect}')

    def on_mouse_drag_up_event(self, event):
        # Check for a sprite collision against the mouse pointer.
        #
        # First, we need to create a pygame Sprite that represents the tip of the mouse.
        mouse = MouseSprite(x=event.pos[0],y=event.pos[1] , width=1, height=1)

        collided_sprites = pygame.sprite.spritecollide(mouse, self.all_sprites, False)

        for sprite in collided_sprites:
            sprite.on_mouse_drag_up_event(event)

        #print(f'Mouse Drag @ {mouse.rect}')

class Game(GameEngine):
    # Set your game name/version here.
    NAME = "Bitmappy"
    VERSION = "0.0"

    def __init__(self, options):
        super().__init__(options=options)
        self.load_resources()

        # pygame.event.set_blocked(self.mouse_events)
        # pygame.event.set_blocked(self.joystick_events)
        # pygame.event.set_blocked(self.keyboard_events)

        # Hook up some events.
        #self.register_game_event('save', self.on_save_event)
        #self.register_game_event('load', self.on_load_event)

    @classmethod
    def args(cls, parser):
        # Initialize the game engine's options first.
        # This ensures that our game's specific options
        # are listed last.
        parser = GameEngine.args(parser)

        group = parser.add_argument_group('Game Options')

        group.add_argument('-v', '--version',
                        action='store_true',
                        help='print the game version and exit')

        return parser

    def start(self):
        # This is a simple class that will help us print to the screen
        # It has nothing to do with the joysticks, just outputting the
        # information.

        # Call the main game engine's start routine to initialize
        # the screen and set the self.screen_width, self.screen_height variables
        # and do a few other init related things.
        super().start()

        # Note: Due to the way things are wired, you must set self.active_scene after
        # calling super().start() in this method.
        self.clock = pygame.time.Clock()
        self.active_scene = BitmapEditorScene()

        while self.active_scene != None:
            self.process_events()

            self.active_scene.update()

            self.active_scene.render(self.screen)

            self.clock.tick(self.fps)

            if self.update_type == 'update':
                pygame.display.update(self.active_scene.rects)
            elif self.update_type == 'flip':
                pygame.display.flip()                    

            self.active_scene = self.active_scene.next


    #def load_resources(self):
    #    for resource in glob.iglob('resources/*', recursive=True):
    #        try:
    #            pass
    #        except IsADirectoryError:
    #            pass

    def on_key_up_event(self, event):
        self.active_scene.on_key_up_event(event)

        # KEYUP            key, mod
        if event.key == pygame.K_q:
            log.info(f'User requested quit.')
            event = pygame.event.Event(pygame.QUIT, {})
            pygame.event.post(event)

    # This will catch calls which our scene engine doesn't yet implement.
    def __getattr__(self, attr):
        try:
            if self.active_scene:
                return getattr(self.active_scene, attr)
            else:
                raise Exception(f'Scene not activated in call to {attr}()')
        except AttributeError:
            raise AttributeError(f'{attr} is not implemented in Game {type(self)} or active scene {type(self.active_scene)}.')

def main():
    parser = argparse.ArgumentParser(f"{Game.NAME} version {Game.VERSION}")

    # args is a class method, which allows us to call it before initializing a game
    # object, which allows us to query all of the game engine objects for their
    # command line parameters.
    parser = Game.args(parser)
    args = parser.parse_args()
    game = Game(options=vars(args))
    game.start()

if __name__ == '__main__':
    try:
        main()
        log.info('Done')
    except Exception as e:
        raise e
    finally:
        log.info('Shutting down pygame.')
        pygame.quit()

