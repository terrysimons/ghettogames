#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import glob
import logging
import multiprocessing

import pygame.freetype
import pygame.gfxdraw
import pygame.locals
from pygame import Rect

from ghettogames.engine import RootScene, GameEngine, FontManager, JoystickManager
from ghettogames.engine import RootSprite
from ghettogames.color import BLACKLUCENT, BLACK, YELLOW, GREEN, BLUE
from ghettogames.color import PURPLE, WHITE

log = logging.getLogger('game')
log.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

log.addHandler(ch)


class ShapesSprite(RootSprite):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.use_gfxdraw = True

        self.screen = pygame.display.get_surface()
        self.screen_width = self.screen.get_width()
        self.screen_height = self.screen.get_height()
        self.screen.convert()
        self.screen.fill(BLACK)
        self.image = self.screen
        self.rect = self.image.get_rect()

        self.point = None
        self.circle = None
        self.triangle = None

        self._draw_point()
        self._draw_triangle()
        self._draw_circle()
        self._draw_rectangle()

        self.dirty = 1
        self.update()

    def move(self, pos):
        self.rect.center = pos
        self.dirty = 1

    def update(self):
        self.dirty = 1

    def _draw_point(self):
        # Draw a yellow point.
        # There's no point API, so we'll fake
        # it with the line API.
        if self.use_gfxdraw:
            pygame.gfxdraw.pixel(self.screen,  # noqa: I1101
                                 self.screen_width // 2,
                                 self.screen_height // 2,
                                 YELLOW)  # noqa: I1101

            self.point = (self.screen_width // 2, self.screen_height // 2)
        else:
            self.point = pygame.draw.line(self.screen,
                                          YELLOW,
                                          (self.screen_width // 2, self.screen_height // 2),
                                          (self.screen_width // 2, self.screen_height // 2))

    def _draw_circle(self):
        # Draw a blue circle.
        if self.use_gfxdraw:
            pygame.gfxdraw.circle(self.screen,  # noqa: I1101
                                  self.screen_width // 2,
                                  self.screen_height // 2,
                                  self.screen_height // 2,
                                  BLUE)
        else:
            pygame.draw.circle(self.screen,
                               BLUE,
                               (self.screen_width // 2, self.screen_height // 2),
                               self.screen_height // 2, 1)

    def _draw_triangle(self):
        # Draw a green triangle.
        # polygon(Surface, color, pointlist, width=0) -> Rect
        x1 = self.screen_width // 2
        y1 = 0
        x2 = self.rectangle.bottomleft[0]
        y2 = self.rectangle.bottomleft[1] - 1
        x3 = self.rectangle.bottomright[0]
        y3 = self.rectangle.bottomright[1] - 1

        top_point = (x1, y1)
        left_point = (x2, y2)
        right_point = (x3, y3)
        pointlist = (top_point, left_point, right_point)

        if self.use_gfxdraw:
            pygame.gfxdraw.polygon(self.screen, pointlist, GREEN)  # noqa: I1101

            # You could also use:
            # pygame.gfxdraw.trigon(self.screen, x1, y1, x2, y2, x3, y3, GREEN)

            self.triangle = pointlist
        else:
            self.triangle = pygame.draw.polygon(self.screen, GREEN, pointlist, 1)

    @property
    def rectangle(self):
        rect = Rect(0, 0, self.screen_height, self.screen_height)
        rect.center = (self.screen_width / 2, self.screen_height / 2)

        return rect

    def _draw_rectangle(self):
        # Draw a purple rectangle.
        # Note that the pygame documentation has a typo
        # Do not use width=1, use 1 instead.
        if self.use_gfxdraw:
            pygame.gfxdraw.rectangle(self.screen, self.rectangle, PURPLE)  # noqa: I1101
        else:
            self.rectangle = pygame.draw.rect(self.screen, PURPLE, self.rectangle, 1)


class TextSprite(RootSprite):
    def __init__(self, background_color=BLACKLUCENT, alpha=0, x=0, y=0):
        self.background_color = background_color
        self.alpha = alpha
        self.x = x
        self.y = y
        self.text_box = None
        super().__init__()

        # Quick and dirty, for now.
        self.image = pygame.Surface((200, 200))
        self.screen = pygame.display.get_surface()

        if not alpha:
            self.image.set_colorkey(self.background_color)
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
        self.rect.x += x
        self.rect.y += y
        self.font_manager = FontManager()
        self.joystick_manager = JoystickManager()
        self.joystick_count = len(self.joystick_manager.joysticks)

        # Interiting from object is default in Python 3.
        # Linters complain if you do it.
        class TextBox:
            def __init__(self, font_controller, x, y, line_height=15):
                super().__init__()
                self.image = None
                self.rect = None
                self.start_x = x
                self.start_y = y
                self.x = self.start_x
                self.y = self.start_y
                self.line_height = line_height

                pygame.freetype.set_default_resolution(font_controller.font_dpi)
                self.font = pygame.freetype.SysFont(name=font_controller.font,
                                                    size=font_controller.font_size)

            def print(self, surface, string):
                (self.image, self.rect) = self.font.render(string, WHITE)
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

        self.text_box = TextBox(font_controller=self.font_manager, x=10, y=10)

        self.update()

    def update(self):
        self.dirty = 2
        self.image.fill(self.background_color)

        pygame.draw.rect(self.image, WHITE, self.image.get_rect(), 7)

        self.text_box.reset()
        self.text_box.print(self.image, f'{Game.NAME} version {Game.VERSION}')

        self.text_box.print(self.image, f'CPUs: {multiprocessing.cpu_count()}')

        self.text_box.print(self.image, f'FPS: {Game.FPS:.0f}')

        self.text_box.print(self.image, "Number of joysticks: {}".format(self.joystick_count))
        if self.joystick_count:
            for i, joystick in enumerate(self.joystick_manager.joysticks):
                self.text_box.print(self.image, f'Joystick {i}')

                # Get the name from the OS for the controller/joystick
                self.text_box.indent()
                self.text_box.print(self.image, f'Joystick name: {joystick.get_name()}')

                # Usually axis run in pairs, up/down for one, and left/right for
                # the other.
                axes = joystick.get_numaxes()
                self.text_box.print(self.image, f'Number of axes: {axes}')

                self.text_box.indent()
                for j in range(axes):
                    self.text_box.print(self.image, 'Axis {} value: {:>6.3f}'
                                        .format(j, joystick.get_axis(j)))
                self.text_box.unindent()

                buttons = joystick.get_numbuttons()
                self.text_box.print(self.image, f'Number of buttons: {joystick.get_numbuttons()}')

                self.text_box.indent()
                for j in range(buttons):
                    self.text_box.print(self.image, 'Button {:>2} value: {}'
                                        .format(j, joystick.get_button(i)))
                self.text_box.unindent()

                # Hat switch. All or nothing for direction, not like joysticks.
                # Value comes back in an array.
                hats = 0
                self.text_box.print(self.image, f'Number of hats: {hats}')

                self.text_box.indent()
                for j in range(hats):
                    self.text_box.print(self.image, f'Hat {j} value: {str(joystick.get_hat(j))}')
                    self.text_box.unindent()
                self.text_box.unindent()


class JoystickScene(RootScene):
    def __init__(self):
        super().__init__()
        self.tiles = []

        # self.load_resources()
        self.shapes_sprite = ShapesSprite()
        # self.text_sprite = TextSprite(background_color=BLACKLUCENT, alpha=0, x=0, y=0)

        self.all_sprites = pygame.sprite.LayeredDirty(
            (
                # self.shapes_sprite,
                # self.text_sprite
            )
        )

        self.all_sprites.clear(self.screen, self.background)
        # self.load_resources()

    def load_resources(self):  # noqa: R0201
        # Load tiles.
        for resource in glob.iglob('resources/*', recursive=True):
            try:
                log.info(f'Load Resource: {resource}')
            except IsADirectoryError:
                pass
        #         self.tiles.append(load_graphic(resource))
        #     except IsADirectoryError:
        #         pass

    def render(self, screen):
        super().render(screen)

        x = 0
        y = 0
        tiles_across = 640 / 32
        # tiles_down = 480 / 32
        for i, graphic in enumerate(self.tiles):
            screen.blit(graphic, (x, y))
            if i % tiles_across == 0:
                x = 0
                y += 32
            else:
                x += 32

    def on_mouse_motion_event(self, event):
        self.shapes_sprite.move(event.pos)

    def on_left_mouse_button_up(self, event):  # noqa: W0613
        self.post_game_event('recharge', {'item': 'bullet', 'rate': 1})

    def on_left_mouse_button_down(self, event):  # noqa: W0613
        self.post_game_event('pew pew', {'bullet': 'big boomies'})

    def on_pew_pew_event(self, event):  # noqa: R0201
        log.info(f'PEW PEW Event: {event}')

    def on_recharge_event(self, event):  # noqa: R0201
        log.info(f'Recharge Event: {event}')


class Game(GameEngine):
    # Set your game name/version here.
    NAME = "Joystick and Font Demo"
    VERSION = "0.0"

    def __init__(self, options):
        super().__init__(options=options)
        self.time = options.get('time')

        # TODO: Write an FPS layer that uses time.ns_time()
        # https://www.pygame.org/docs/ref/display.html#pygame.display.set_mode
        #
        # (0, 0), 0, 0 is the recommended setting for auto-configure.
        # if self.windowed:
        #     self.mode_flags = 0
        # else:
        #     self.mode_flags = pygame.FULLSCREEN
        #     self.screen_width = 0
        #     self.screen_height = 0
        # self.color_depth = 0

        # Uncomment to easily block a class of events, if you
        # don't want them to be processed by the event queue.
        #
        # pygame.event.set_blocked(self.mouse_events)
        # pygame.event.set_blocked(self.joystick_events)
        # pygame.event.set_blocked(self.keyboard_events)

        # Let's hook up the 'pew pew' event.
        # self.register_game_event('pew pew', self.on_pew_pew_event)

        # And the recharge event.
        # self.register_game_event('recharge', self.on_recharge_event)

    # def update_cursor(self):
        # For giggles, we can draw two cursors.
        # This can cause extra flicker on the cursor.
        #
        # We need to re-configure the various cursor attributes once we do this.
    #    self.cursor = [cursor_row for cursor_row in self.cursor]
    #    self.cursor_width = len(self.cursor[0])
    #    self.cursor_height = len(self.cursor)

        # log.info(f'Custom cursor width: {self.cursor_width}, height: {self.cursor_height}')

        # Now call the GameEngine update_cursor method to compile and set the cursor.
        # super().update_cursor()

    @classmethod
    def args(cls, parser):
        # Initialize the game engine's options first.
        # This ensures that our game's specific options
        # are listed last.
        parser = GameEngine.args(parser)

        group = parser.add_argument_group('Game Options')

        group.add_argument('--time',
                           type=int,
                           help='time in seconds to wait before quitting',
                           default=10)
        group.add_argument('-v', '--version',
                           action='store_true',
                           help='print the game version and exit')

        return parser

    def start(self):
        # Call the main game engine's start routine to initialize
        # the screen and set the self.screen_width, self.screen_height variables
        super().start()

        # Note: Due to the way things are wired, you must set self.active_scene after
        # calling super().start() in this method.
        self.clock = pygame.time.Clock()
        self.active_scene = JoystickScene()

        while self.active_scene is not None:
            self.process_events()

            self.active_scene.update()

            self.active_scene.render(self.screen)

            if self.update_type == 'update':
                pygame.display.update(self.active_scene.rects)
            elif self.update_type == 'flip':
                pygame.display.flip()

            self.clock.tick(self.fps)

            self.active_scene = self.active_scene.next

    def quit(self):
        log.info('Quit was called.')

        # Call the GameEngine quit, so it will clean up.
        super().quit()

    def on_key_up_event(self, event):
        # KEYUP            key, mod
        if event.key == pygame.K_q:
            log.info(f'User requested quit.')
            event = pygame.event.Event(pygame.QUIT, {})
            pygame.event.post(event)


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
