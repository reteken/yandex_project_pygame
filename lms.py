import pygame
from pygame.locals import *
import sys
import random
import time

pygame.init()

SCREEN_WIDTH = 1080
SCREEN_HEIGHT = 800
FPS = 60

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GREEN = (0, 250, 0)
GRAY = (128, 128, 128)

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Dmitriy Combat 2D")
clock = pygame.time.Clock()

characters = ["durov", "rectangle"]
player1_choice = 0
player2_choice = 0


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, direction, owner, animation_frames):
        super().__init__()
        self.animation_frames = animation_frames
        self.current_frame = 0
        self.image = self.animation_frames[self.current_frame]
        self.rect = self.image.get_rect()
        self.rect.topleft = (x + random.randint(10, 50), y + random.randint(-10, 10))
        self.speed = 10 * direction
        self.owner = owner
        self.animation_speed = 1
        self.frame_counter = 0

    def update(self):
        self.rect.x += self.speed
        if self.rect.right < 0 or self.rect.left > SCREEN_WIDTH:
            self.kill()
        self.frame_counter += self.animation_speed
        if self.frame_counter >= 1:
            self.current_frame = (self.current_frame + 1) % len(self.animation_frames)
            self.image = self.animation_frames[self.current_frame]
            self.frame_counter = 0


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, character, animation_frames, jump_frames, hit_frames):
        super().__init__()
        self.character = character
        self.animation_frames = animation_frames
        self.jump_frames = jump_frames
        self.hit_frames = hit_frames
        self.current_frame = 0
        self.jump_frame = 0
        self.hit_frame = 0
        self.animation_speed = 1.05
        self.frame_counter = 0
        self.image = self.animation_frames[self.current_frame]
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.mask = pygame.mask.from_surface(self.image)
        self.health = 100
        self.speed = 5
        self.jump_speed = -15
        self.gravity = 0.8
        self.dy = 0
        self.on_ground = False
        self.is_moving = False
        self.is_jumping = False
        self.is_hitting = False
        self.facing_right = True
        self.last_shot_time = 0
        self.last_hit_time = 0

    def update(self, other, keys, controls, bullets_group, bullet_animation_frames):
        self.is_moving = False
        if keys[controls["left"]] and self.rect.x > 0:
            self.rect.x -= self.speed
            self.is_moving = True
            if self.facing_right:
                self.facing_right = False
                self.flip_images()
        if keys[controls["right"]] and self.rect.x + 50 < SCREEN_WIDTH:
            self.rect.x += self.speed
            self.is_moving = True
            if not self.facing_right:
                self.facing_right = True
                self.flip_images()
        if keys[controls["jump"]] and self.on_ground:
            self.dy = self.jump_speed
            self.on_ground = False
            self.is_jumping = True
        self.gravity_helper()

    def flip_images(self):
        self.animation_frames = [
            pygame.transform.flip(frame, True, False) for frame in self.animation_frames
        ]
        self.jump_frames = [
            pygame.transform.flip(frame, True, False) for frame in self.jump_frames
        ]
        self.hit_frames = [
            pygame.transform.flip(frame, True, False) for frame in self.hit_frames
        ]
        self.image = self.animation_frames[self.current_frame]
        self.mask = pygame.mask.from_surface(self.image)

    def gravity_helper(self):
        self.dy += self.gravity
        self.rect.y += self.dy
        if self.rect.bottom >= SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT
            self.dy = 0
            self.on_ground = True
            self.is_jumping = False
            self.jump_frame = 0


def main_menu():
    global player1_choice, player2_choice
    font = pygame.font.SysFont(None, 74)
    button_rects = []
    for i in range(3):
        button_rects.append(pygame.Rect(100, 300 + i * 80, 200, 60))
        button_rects.append(pygame.Rect(SCREEN_WIDTH - 300, 300 + i * 80, 200, 60))
    running = True
    while running:
        screen.fill(WHITE)
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                for i, rect in enumerate(button_rects):
                    if rect.collidepoint(event.pos):
                        if i < 3:
                            player1_choice = i % len(characters)
                        else:
                            player2_choice = i % len(characters)
        pygame.draw.rect(
            screen, BLACK, (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 - 50, 300, 100)
        )
        text = font.render("Start Game", True, WHITE)
        screen.blit(text, (SCREEN_WIDTH // 2 - 75, SCREEN_HEIGHT // 2 - 25))
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main_menu()
