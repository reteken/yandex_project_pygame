import pygame
from pygame.locals import *
import sys
import random
import time
import cv2
import numpy as np
import json
from network import NetworkClient  # импортируем наш модуль сетевого клиента

pygame.init()
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
FPS = 60
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GREEN = (0, 250, 0)
GRAY = (128, 128, 128)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Dmitriy Combat 2D")
clock = pygame.time.Clock()


def get_frame_surface(cap, w, h):
    ret, frame = cap.read()
    if not ret:
        # Если не удалось прочитать кадр, сбрасываем видео и пробуем снова
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = cap.read()
        if not ret:
            return None
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = cv2.resize(frame, (w, h))
    return pygame.surfarray.make_surface(np.transpose(frame, (1, 0, 2)))


class Button:
    def __init__(
        self,
        rect,
        color,
        text,
        text_color=WHITE,
        border_color=GRAY,
        no_background=False,
    ):
        self.rect = rect
        self.color = color
        self.text = text
        self.text_color = text_color
        self.border_color = border_color
        self.font = pygame.font.SysFont(None, 36)
        self.no_background = no_background

    def draw(self, surface):
        if not self.no_background:
            pygame.draw.rect(
                surface, self.border_color, self.rect.inflate(10, 10), border_radius=10
            )
            pygame.draw.rect(surface, self.color, self.rect, border_radius=10)
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, direction, owner, animation_frames, bullet_type):
        super().__init__()
        self.animation_frames = animation_frames
        self.current_frame = 0
        self.bullet_type = bullet_type
        if direction < 0:
            self.animation_frames = [
                pygame.transform.flip(f, True, False) for f in self.animation_frames
            ]
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
    def __init__(
        self, x, y, run_frames, jump_frames, hit_frames, idle_frames, is_pepe=False
    ):
        super().__init__()
        self.is_pepe = is_pepe
        self.animation_frames = run_frames
        self.jump_frames = jump_frames
        self.hit_frames = hit_frames
        self.idle_frames = idle_frames
        self.idle_frame = 0
        self.current_frame = 0
        self.jump_frame = 0
        self.hit_frame = 0
        self.animation_speed = 1.1
        self.frame_counter = 0
        self.image = self.animation_frames[self.current_frame]
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.mask = pygame.mask.from_surface(self.image)
        self.health = 100
        self.speed = 10
        self.jump_speed = -25
        self.gravity = 0.85
        self.dy = 0
        self.on_ground = False
        self.is_moving = False
        self.is_jumping = False
        self.is_hitting = False
        self.facing_right = True
        self.last_shot_time = 0
        self.last_hit_time = 0

    def animate(self):
        if self.is_jumping:
            self.jump_frame += self.animation_speed
            if self.jump_frame >= len(self.jump_frames):
                self.jump_frame = len(self.jump_frames) - 1
            self.image = self.jump_frames[int(self.jump_frame)]
        elif self.is_hitting:
            self.hit_frame += self.animation_speed
            if self.hit_frame >= len(self.hit_frames):
                self.hit_frame = 0
                self.is_hitting = False
            self.image = self.hit_frames[int(self.hit_frame)]
        elif self.is_moving:
            self.frame_counter += self.animation_speed
            if self.frame_counter >= 1:
                self.current_frame = (self.current_frame + 1) % len(
                    self.animation_frames
                )
                self.image = self.animation_frames[self.current_frame]
                self.frame_counter = 0
        else:
            self.idle_frame += self.animation_speed
            if self.idle_frame >= len(self.idle_frames):
                self.idle_frame = 0
            self.image = self.idle_frames[int(self.idle_frame)]
        self.mask = pygame.mask.from_surface(self.image)

    def inputer(
        self, other, keys, controls, bullets_group, bullet_animation_frames, bullet_type
    ):
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
        current_time = time.time()
        if keys[controls["shoot"]] and current_time - self.last_shot_time > 1:
            self.last_shot_time = current_time
            direction = 1 if self.rect.x < other.rect.x else -1
            for i in range(3):
                bullet = Bullet(
                    self.rect.centerx,
                    self.rect.centery - 10 + i * 10,
                    direction,
                    self,
                    bullet_animation_frames,
                    bullet_type,
                )
                bullets_group.add(bullet)
        if keys[controls["hit"]] and current_time - self.last_hit_time > 0.5:
            self.is_hitting = True
            self.hit_frame = 0
            self.last_hit_time = current_time
            if self.facing_right:
                self.rect.x += 10
            else:
                self.rect.x -= 10
            if self.rect.colliderect(other.rect):
                other.health -= 15

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
        self.idle_frames = [
            pygame.transform.flip(frame, True, False) for frame in self.idle_frames
        ]
        self.image = self.animation_frames[self.current_frame]
        self.mask = pygame.mask.from_surface(self.image)

    def gravity_helper(self):
        self.dy += self.gravity
        self.rect.y += self.dy
        floor_level = SCREEN_HEIGHT - 100
        if self.rect.bottom >= floor_level:
            self.rect.bottom = floor_level
            self.dy = 0
            self.on_ground = True
            self.is_jumping = False
            self.jump_frame = 0

    def update(
        self, other, keys, controls, bullets_group, bullet_animation_frames, bullet_type
    ):
        self.inputer(
            other, keys, controls, bullets_group, bullet_animation_frames, bullet_type
        )
        self.animate()
        self.gravity_helper()

    def draw_health_bar(self, screen, x, y):
        bar_width = 200
        bar_height = 20

        # Рисуем фон HP-бар (красный)
        pygame.draw.rect(screen, RED, (x, y, bar_width, bar_height))

        # Вычисляем отношение оставшегося здоровья (от 0 до 1)
        ratio = self.health / 100.0

        # Интерполируем цвет: при 100% здоровья – зеленый (0,255,0), при 0% – красный (255,0,0)
        health_color = (0, 255, 0)

        current_health_width = ratio * bar_width
        pygame.draw.rect(screen, health_color, (x, y, current_health_width, bar_height))

        # Если у игрока установлена XP-рамка (PNG-окоемка), выводим её, центрируя относительно HP-бар
        if hasattr(self, "xp_frame") and self.xp_frame is not None:
            frame = self.xp_frame
            frame_w = frame.get_width()
            frame_h = frame.get_height()
            new_x = x - (frame_w - bar_width) // 2
            new_y = y - (frame_h - bar_height) // 2
            screen.blit(frame, (new_x, new_y))


class AIPlayer(Player):
    def inputer(
        self, other, keys, controls, bullets_group, bullet_animation_frames, bullet_type
    ):
        self.is_moving = False
        direction = 1 if other.rect.x > self.rect.x else -1
        distance = abs(self.rect.centerx - other.rect.centerx)
        if distance < 180:
            if random.random() < 0.1:
                self.rect.x -= self.speed * direction
                self.is_moving = True
                if direction == 1 and self.facing_right:
                    self.flip_images()
                    self.facing_right = False
                elif direction == -1 and not self.facing_right:
                    self.flip_images()
                    self.facing_right = True
            else:
                self.rect.x += self.speed * direction
                self.is_moving = True
                if direction == 1 and not self.facing_right:
                    self.flip_images()
                    self.facing_right = True
                elif direction == -1 and self.facing_right:
                    self.flip_images()
                    self.facing_right = False
        elif distance > 800:
            self.rect.x += self.speed * direction
            self.is_moving = True
            if direction == 1 and not self.facing_right:
                self.flip_images()
                self.facing_right = True
            elif direction == -1 and self.facing_right:
                self.flip_images()
                self.facing_right = False
        else:
            if random.random() < 0.02:
                step_dir = 1 if random.random() < 0.5 else -1
                self.rect.x += step_dir * self.speed
                self.is_moving = True
                if step_dir == 1 and not self.facing_right:
                    self.flip_images()
                    self.facing_right = True
                elif step_dir == -1 and self.facing_right:
                    self.flip_images()
                    self.facing_right = False
        self.rect.x = max(0, min(self.rect.x, SCREEN_WIDTH - self.rect.width))
        if self.on_ground and random.random() < 0.03:
            self.dy = self.jump_speed
            self.on_ground = False
            self.is_jumping = True
        current_time = time.time()
        if current_time - self.last_shot_time > 0.2:
            self.last_shot_time = current_time
            for i in range(3):
                bullet = Bullet(
                    self.rect.centerx,
                    self.rect.centery - 10 + i * 10,
                    direction,
                    self,
                    bullet_animation_frames,
                    bullet_type,
                )
                bullets_group.add(bullet)
        if distance < 110 and current_time - self.last_hit_time > 1.0:
            if random.random() < 0.6:
                self.is_hitting = True
                self.hit_frame = 0
                self.last_hit_time = current_time
                if direction == 1:
                    self.rect.x += 15
                else:
                    self.rect.x -= 15
                if self.rect.colliderect(other.rect):
                    other.health -= 10
        self.rect.x = max(0, min(self.rect.x, SCREEN_WIDTH - self.rect.width))
        floor_level = SCREEN_HEIGHT - 100
        if self.rect.bottom >= floor_level:
            self.rect.bottom = floor_level
            self.dy = 0
            self.on_ground = True
            self.is_jumping = False
            self.jump_frame = 0


def load_image_with_fallback(path, width, height, fallback_color):
    try:
        image = pygame.image.load(path).convert_alpha()
    except:
        image = pygame.Surface((width, height))
        image.fill(fallback_color)
    return pygame.transform.scale(image, (width, height))


def load_animation(folder, frame_count, prefix, width=350, height=350):
    frames = []
    for i in range(frame_count):
        path = f"{folder}/{prefix}_{i+1}.png"
        frame_surf = load_image_with_fallback(path, width, height, ORANGE)
        frames.append(frame_surf)
    return frames


def create_pepe_animation(folder, frame_count, prefix, width=350, height=350):
    frames = []
    for i in range(frame_count):
        frame_number = str(i).zfill(5)
        path = f"{folder}/{prefix}_{frame_number}.png"
        frame_surf = load_image_with_fallback(path, width, height, BLUE)
        frames.append(frame_surf)
    return frames


def load_bullet_animation(
    folder, frame_count, prefix, width=300, height=150, color=GRAY
):
    frames = []
    for i in range(frame_count):
        frame_number = str(i).zfill(5)
        path = f"{folder}/{prefix}_{frame_number}.png"
        frame_surf = load_image_with_fallback(path, width, height, color)
        frames.append(frame_surf)
    return frames


def show_loading_screen(progress, total):
    screen.fill(BLACK)
    font = pygame.font.SysFont(None, 74)
    loading_text = font.render("Loading...", True, WHITE)
    loading_rect = loading_text.get_rect(
        center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50)
    )
    screen.blit(loading_text, loading_rect)
    bar_width = 400
    bar_height = 30
    bar_x = (SCREEN_WIDTH - bar_width) // 2
    bar_y = SCREEN_HEIGHT // 2
    pygame.draw.rect(
        screen, GRAY, (bar_x, bar_y, bar_width, bar_height), border_radius=5
    )
    loaded_width = int(bar_width * (progress / total))
    pygame.draw.rect(
        screen, GREEN, (bar_x, bar_y, loaded_width, bar_height), border_radius=5
    )
    pygame.display.flip()


def load_all_assets():
    total_load_steps = 800
    current_progress = 0
    show_loading_screen(current_progress, total_load_steps)

    durov_run = load_animation("durov", 20, "дуров бежит")
    current_progress += 20
    show_loading_screen(current_progress, total_load_steps)

    durov_jump = load_animation("durov_jump", 49, "durov_jump")
    current_progress += 49
    show_loading_screen(current_progress, total_load_steps)

    durov_hit = load_animation("damage_1", 37, "durov_hit")
    current_progress += 37
    show_loading_screen(current_progress, total_load_steps)

    durov_idle = create_pepe_animation("waiter_durov", 55, "стойкаааааааааааа")
    current_progress += 55
    show_loading_screen(current_progress, total_load_steps)

    pepe_run = create_pepe_animation("pepe_run", 31, "бег пепе")
    current_progress += 31
    show_loading_screen(current_progress, total_load_steps)

    pepe_jump = create_pepe_animation("pepe_run", 30, "бег пепе")
    current_progress += 30
    show_loading_screen(current_progress, total_load_steps)

    pepe_hit = create_pepe_animation("hit_pepe_1", 28, "удар пепе 1")
    current_progress += 28
    show_loading_screen(current_progress, total_load_steps)

    pepe_idle = create_pepe_animation("waiter_pepe", 60, "пепе стойка")
    current_progress += 60
    show_loading_screen(current_progress, total_load_steps)

    # Увеличенные анимации пуль (150x75)
    ton_bullet = load_bullet_animation("ton coin", 155, "ton coin", 150, 75, GRAY)
    current_progress += 155
    show_loading_screen(current_progress, total_load_steps)

    pepe_bullet = load_bullet_animation("pepe coin", 155, "пепе пуля", 150, 75, PURPLE)
    current_progress += 155
    show_loading_screen(current_progress, total_load_steps)

    main_video = cv2.VideoCapture("поле_1.mp4")
    current_progress += 1
    show_loading_screen(current_progress, total_load_steps)

    lobby_video = cv2.VideoCapture("лобби.mp4")
    current_progress += 1
    show_loading_screen(current_progress, total_load_steps)

    start_game_anim = create_pepe_animation("start game", 65, "start game", 472, 100)
    current_progress += 65
    show_loading_screen(current_progress, total_load_steps)

    ai_image = load_image_with_fallback("AI_name.png", 300, 300, GRAY)
    current_progress += 1
    show_loading_screen(current_progress, total_load_steps)

    # Загрузка glow-анимаций
    left_glow = create_pepe_animation("свечение_левое", 41, "Left glow", 1920, 1080)
    current_progress += 41
    show_loading_screen(current_progress, total_load_steps)

    right_glow = create_pepe_animation("свечение_правое", 41, "Right glow", 1920, 1080)
    current_progress += 41
    show_loading_screen(current_progress, total_load_steps)

    # Загрузка matrix-анимаций
    matrix_durov = create_pepe_animation(
        "matrix_durov", 55, "Holomatrix Durov", 350, 350
    )
    current_progress += 55
    show_loading_screen(current_progress, total_load_steps)

    matrix_pepe = create_pepe_animation("matrix_pepe", 47, "Holomatrix pepe", 350, 350)
    current_progress += 47
    show_loading_screen(current_progress, total_load_steps)

    changer_img = load_image_with_fallback("changer.png", 50, 50, GRAY)
    current_progress += 1
    show_loading_screen(current_progress, total_load_steps)

    # Загрузка XP баров (рамок для HP-бара) из папки XP bars.
    xp_left_durov = load_image_with_fallback("XP bars/левый_дуров.png", 400, 100, GRAY)
    current_progress += 1
    show_loading_screen(current_progress, total_load_steps)

    xp_right_durov = load_image_with_fallback(
        "XP bars/правый_дуров.png", 400, 100, GRAY
    )
    current_progress += 1
    show_loading_screen(current_progress, total_load_steps)

    xp_left_pepe = load_image_with_fallback("XP bars/левый_пепе.png", 400, 100, GRAY)
    current_progress += 1
    show_loading_screen(current_progress, total_load_steps)

    xp_right_pepe = load_image_with_fallback("XP bars/правый_пепе.png", 400, 100, GRAY)
    current_progress += 1
    show_loading_screen(current_progress, total_load_steps)

    return {
        "durov": {
            "run": durov_run,
            "jump": durov_jump,
            "hit": durov_hit,
            "idle": durov_idle,
        },
        "pepe": {
            "run": pepe_run,
            "jump": pepe_jump,
            "hit": pepe_hit,
            "idle": pepe_idle,
        },
        "bullets": {
            "ton": ton_bullet,
            "pepe": pepe_bullet,
        },
        "video": main_video,
        "video_lobby": lobby_video,
        "start_game_anim": start_game_anim,
        "ai_image": ai_image,
        "left_glow": left_glow,
        "right_glow": right_glow,
        "matrix_durov": matrix_durov,
        "matrix_pepe": matrix_pepe,
        "changer": changer_img,
        "xp_left_durov": xp_left_durov,
        "xp_right_durov": xp_right_durov,
        "xp_left_pepe": xp_left_pepe,
        "xp_right_pepe": xp_right_pepe,
    }


def shop_screen():
    scroll_offset = 0
    squares = []
    square_size = 200
    gap = 50
    base_x = 200
    base_y = 200
    for col in range(2):
        for row in range(2):
            x = base_x + col * (square_size + gap)
            y = base_y + row * (square_size + gap)
            squares.append(pygame.Rect(x, y, square_size, square_size))
    back_button = Button(pygame.Rect(50, SCREEN_HEIGHT - 100, 200, 60), BLUE, "Back")
    running = True
    while running:
        screen.fill(WHITE)
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_UP:
                    scroll_offset += 50
                if event.key == K_DOWN:
                    scroll_offset -= 50
            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                pos = pygame.mouse.get_pos()
                if back_button.is_clicked(pos):
                    running = False
        for sq in squares:
            shifted_rect = sq.move(0, scroll_offset)
            pygame.draw.rect(screen, ORANGE, shifted_rect)
        back_button.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)


class AIPlayerLocal(Player):
    def inputer(
        self, other, keys, controls, bullets_group, bullet_animation_frames, bullet_type
    ):
        # "Умный" AI: анализ расстояния до противника, корректировка дистанции,
        # выбор действий (движение, прыжок, стрельба, удар).
        self.is_moving = False
        current_time = time.time()
        dx = other.rect.centerx - self.rect.centerx
        distance = abs(dx)

        # Оптимальные границы дистанции (в пикселях)
        optimal_min = 200
        optimal_max = 400
        move_speed = self.speed

        # Если противник слишком далеко – приближаемся
        if distance > optimal_max:
            if dx > 0:
                self.rect.x += move_speed
                if not self.facing_right:
                    self.facing_right = True
                    self.flip_images()
            else:
                self.rect.x -= move_speed
                if self.facing_right:
                    self.facing_right = False
                    self.flip_images()
            self.is_moving = True

        # Если противник слишком близко – отступаем
        elif distance < optimal_min:
            if dx > 0:
                self.rect.x -= move_speed
                if self.facing_right:
                    self.facing_right = False
                    self.flip_images()
            else:
                self.rect.x += move_speed
                if not self.facing_right:
                    self.facing_right = True
                    self.flip_images()
            self.is_moving = True

        # Если дистанция в оптимальном диапазоне – небольшое случайное движение
        else:
            if random.random() < 0.1:
                step = random.choice([-move_speed, move_speed])
                self.rect.x += step
                self.is_moving = True
                if step > 0 and not self.facing_right:
                    self.facing_right = True
                    self.flip_images()
                elif step < 0 and self.facing_right:
                    self.facing_right = False
                    self.flip_images()

        # Периодический прыжок, если на земле
        if self.on_ground and random.random() < 0.02:
            self.dy = self.jump_speed
            self.on_ground = False
            self.is_jumping = True

        # Если противник в оптимальном диапазоне – стреляем
        shoot_cooldown = 0.5
        if (
            optimal_min <= distance <= optimal_max
            and (current_time - self.last_shot_time) > shoot_cooldown
        ):
            self.last_shot_time = current_time
            # Направление для пули определяется относительно позиции противника
            direction = 1 if self.rect.x < other.rect.x else -1
            for i in range(3):
                bullet = Bullet(
                    self.rect.centerx,
                    self.rect.centery - 10 + i * 10,
                    direction,
                    self,
                    bullet_animation_frames,
                    bullet_type,
                )
                bullets_group.add(bullet)

        # Если очень близко – выполняем удар (хит)
        hit_cooldown = 0.5
        if distance < 100 and (current_time - self.last_hit_time) > hit_cooldown:
            self.is_hitting = True
            self.hit_frame = 0
            self.last_hit_time = current_time
            # Небольшое движение для симуляции удара
            if dx > 0:
                self.rect.x += 10
            else:
                self.rect.x -= 10
            if self.rect.colliderect(other.rect):
                other.health -= 15


def main_game(player1_choice, player2_choice, assets):
    score1 = 0
    score2 = 0
    round_number = 0

    while score1 < 2 and score2 < 2:
        round_number += 1
        assets["video"].set(cv2.CAP_PROP_POS_FRAMES, 0)
        shadow_img = pygame.image.load("тень.png").convert_alpha()
        shadow_img = pygame.transform.scale(
            shadow_img, (shadow_img.get_width() // 4, shadow_img.get_height() // 4)
        )
        fixed_shadow_y = SCREEN_HEIGHT - 100 - (shadow_img.get_height() // 2)

        def get_video_frame_surface():
            ret, frame = assets["video"].read()
            if not ret:
                assets["video"].set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = assets["video"].read()
                if not ret:
                    return None
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (SCREEN_WIDTH, SCREEN_HEIGHT))
            return pygame.surfarray.make_surface(np.transpose(frame, (1, 0, 2)))

        player1_controls = {
            "left": K_a,
            "right": K_d,
            "jump": K_w,
            "shoot": K_SPACE,
            "hit": K_e,
        }
        player2_controls = {
            "left": K_LEFT,
            "right": K_RIGHT,
            "jump": K_UP,
            "shoot": K_RCTRL,
            "hit": K_LALT,
        }

        if player1_choice == "durov":
            p1_run_frames = assets["durov"]["run"]
            p1_jump_frames = assets["durov"]["jump"]
            p1_hit_frames = assets["durov"]["hit"]
            p1_idle_frames = assets["durov"]["idle"]
            p1_is_pepe = False
        elif player1_choice == "pepe":
            p1_run_frames = assets["pepe"]["run"]
            p1_jump_frames = assets["pepe"]["jump"]
            p1_hit_frames = assets["pepe"]["hit"]
            p1_idle_frames = assets["pepe"]["idle"]
            p1_is_pepe = True
        else:
            p1_run_frames = assets["durov"]["run"]
            p1_jump_frames = assets["durov"]["jump"]
            p1_hit_frames = assets["durov"]["hit"]
            p1_idle_frames = assets["durov"]["idle"]
            p1_is_pepe = False

        if player2_choice == "durov":
            p2_run_frames = assets["durov"]["run"]
            p2_jump_frames = assets["durov"]["jump"]
            p2_hit_frames = assets["durov"]["hit"]
            p2_idle_frames = assets["durov"]["idle"]
            p2_is_pepe = False
        elif player2_choice == "pepe":
            p2_run_frames = assets["pepe"]["run"]
            p2_jump_frames = assets["pepe"]["jump"]
            p2_hit_frames = assets["pepe"]["hit"]
            p2_idle_frames = assets["pepe"]["idle"]
            p2_is_pepe = True
        else:
            p2_run_frames = assets["durov"]["run"]
            p2_jump_frames = assets["durov"]["jump"]
            p2_hit_frames = assets["durov"]["hit"]
            p2_idle_frames = assets["durov"]["idle"]
            p2_is_pepe = False

        p1_bullet_frames = (
            assets["bullets"]["pepe"] if p1_is_pepe else assets["bullets"]["ton"]
        )
        p2_bullet_frames = (
            assets["bullets"]["pepe"] if p2_is_pepe else assets["bullets"]["ton"]
        )
        p1_bullet_type = "pepe" if p1_is_pepe else "ton"
        p2_bullet_type = "pepe" if p2_is_pepe else "ton"

        if player1_choice == "ai":
            player1 = AIPlayerLocal(
                100,
                SCREEN_HEIGHT - 250,
                p1_run_frames,
                p1_jump_frames,
                p1_hit_frames,
                p1_idle_frames,
                is_pepe=p1_is_pepe,
            )
        else:
            player1 = Player(
                100,
                SCREEN_HEIGHT - 250,
                p1_run_frames,
                p1_jump_frames,
                p1_hit_frames,
                p1_idle_frames,
                is_pepe=p1_is_pepe,
            )

        if player2_choice == "ai":
            player2 = AIPlayerLocal(
                SCREEN_WIDTH - 200,
                SCREEN_HEIGHT - 250,
                p2_run_frames,
                p2_jump_frames,
                p2_hit_frames,
                p2_idle_frames,
                is_pepe=p2_is_pepe,
            )
        else:
            player2 = Player(
                SCREEN_WIDTH - 200,
                SCREEN_HEIGHT - 250,
                p2_run_frames,
                p2_jump_frames,
                p2_hit_frames,
                p2_idle_frames,
                is_pepe=p2_is_pepe,
            )

        # Присваиваем XP рамки (окоемки) для HP-бара:
        if p1_is_pepe:
            player1.xp_frame = assets["xp_left_pepe"]
        else:
            player1.xp_frame = assets["xp_left_durov"]

        if p2_is_pepe:
            player2.xp_frame = assets["xp_right_pepe"]
        else:
            player2.xp_frame = assets["xp_right_durov"]

        all_sprites = pygame.sprite.Group()
        all_sprites.add(player1, player2)
        bullets = pygame.sprite.Group()

        round_duration = 60
        round_start_time = time.time()
        running_round = True

        while running_round:
            video_surface = get_video_frame_surface()
            if video_surface:
                screen.blit(video_surface, (0, 0))
            else:
                screen.fill(WHITE)

            elapsed = time.time() - round_start_time
            remaining = round_duration - elapsed
            info_text = f"Time: {int(remaining)}   Score: P1 {score1} - {score2} P2   Round: {round_number}"
            info_surf = pygame.font.SysFont(None, 50).render(info_text, True, YELLOW)
            info_rect = info_surf.get_rect(center=(SCREEN_WIDTH // 2, 50))
            screen.blit(info_surf, info_rect)

            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()

            keys = pygame.key.get_pressed()
            p1_keys = {key: keys[key] for key in player1_controls.values()}
            p2_keys = {key: keys[key] for key in player2_controls.values()}

            player1.update(
                player2,
                p1_keys,
                player1_controls,
                bullets,
                p1_bullet_frames,
                p1_bullet_type,
            )
            player2.update(
                player1,
                p2_keys,
                player2_controls,
                bullets,
                p2_bullet_frames,
                p2_bullet_type,
            )
            bullets.update()

            for bullet in bullets:
                if bullet.owner != player1 and pygame.sprite.collide_mask(
                    bullet, player1
                ):
                    player1.health = max(0, player1.health - 1)
                    bullet.kill()
                if bullet.owner != player2 and pygame.sprite.collide_mask(
                    bullet, player2
                ):
                    player2.health = max(0, player2.health - 1)
                    bullet.kill()

            if player1.health <= 0 or player2.health <= 0 or remaining <= 0:
                running_round = False

            shadow_x1 = player1.rect.centerx - shadow_img.get_width() // 2
            screen.blit(
                shadow_img,
                (shadow_x1, SCREEN_HEIGHT - 100 - (shadow_img.get_height() // 2)),
            )
            shadow_x2 = player2.rect.centerx - shadow_img.get_width() // 2
            screen.blit(
                shadow_img,
                (shadow_x2, SCREEN_HEIGHT - 100 - (shadow_img.get_height() // 2)),
            )

            all_sprites.draw(screen)
            bullets.draw(screen)

            # Изменённое позиционирование HP-баров:
            # Для персонажа 1 – отступ от левого края 100 пикселей (x=100)
            player1.draw_health_bar(screen, 100, 40)
            # Для персонажа 2 – отступ от правого края 100 пикселей (x = SCREEN_WIDTH - 300 - 100 = SCREEN_WIDTH - 400)
            player2.draw_health_bar(screen, SCREEN_WIDTH - 400, 40)

            pygame.display.flip()
            clock.tick(FPS)

        if player1.health <= 0 and player2.health > 0:
            round_winner = "Player 2"
            score2 += 1
        elif player2.health <= 0 and player1.health > 0:
            round_winner = "Player 1"
            score1 += 1
        else:
            if player1.health > player2.health:
                round_winner = "Player 1"
                score1 += 1
            elif player2.health > player1.health:
                round_winner = "Player 2"
                score2 += 1
            else:
                round_winner = "Draw"

        result_text = f"Round {round_number} Result: {round_winner}"
        result_surf = pygame.font.SysFont(None, 74).render(result_text, True, YELLOW)
        result_rect = result_surf.get_rect(
            center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        )
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        screen.blit(result_surf, result_rect)
        pygame.display.flip()
        pygame.time.wait(2000)

    if score1 > score2:
        final_text = "Player 1 WINS the match!"
    elif score2 > score1:
        final_text = "Player 2 WINS the match!"
    else:
        final_text = "MATCH DRAW!"
    final_surf = pygame.font.SysFont(None, 74).render(final_text, True, YELLOW)
    final_rect = final_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))
    screen.blit(final_surf, final_rect)
    pygame.display.flip()
    pygame.time.wait(3000)


def main_menu(assets):

    if "left_glow" not in assets:
        assets["left_glow"] = create_pepe_animation(
            "свечение_левое", 41, "Left glow", 1920, 1080
        )
    if "right_glow" not in assets:
        assets["right_glow"] = create_pepe_animation(
            "свечение_правое", 41, "Right glow", 1920, 1080
        )
    if "matrix_durov" not in assets:
        assets["matrix_durov"] = create_pepe_animation(
            "matrix_durov", 55, "Holomatrix Durov", 350, 350
        )
    if "matrix_pepe" not in assets:
        assets["matrix_pepe"] = create_pepe_animation(
            "matrix_pepe", 47, "Holomatrix pepe", 350, 350
        )

    cap_lobby = assets["video_lobby"]
    ai_image = assets["ai_image"]

    cap_lobby.set(cv2.CAP_PROP_POS_FRAMES, 0)

    left_glow_time = 0
    right_glow_time = 0
    glow_duration = 1.0
    left_glow_frames = assets["left_glow"]
    right_glow_frames = assets["right_glow"]

    left_matrix_time = time.time()
    right_matrix_time = time.time()

    start_game_anim_start = time.time()

    font = pygame.font.SysFont(None, 74)
    font_label = pygame.font.SysFont(None, 36)

    shop_button = Button(pygame.Rect(20, 20, 150, 50), BLUE, "Shop")
    # Изменено: увеличиваем кнопку "Start Game" по вертикали (высота с 100 до 200), ширина (300) остаётся неизменной.
    start_button = Button(
        pygame.Rect(SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT - 100, 500, 150),
        GREEN,
        "Start Game",
        no_background=True,
    )

    options = ["durov", "pepe", "ai"]
    player1_index = 0
    player2_index = 0

    # Определяем прямоугольники превью для игроков.
    preview_rect1 = pygame.Rect(325, 600, 350, 350)
    preview_rect2 = pygame.Rect(SCREEN_WIDTH - 525, 600, 350, 350)

    arrow_width, arrow_height = 50, 50
    left_arrow_img = pygame.transform.flip(assets["changer"], True, False)
    right_arrow_img = assets["changer"]

    margin = 10
    p1_left_arrow_rect = pygame.Rect(
        preview_rect1.left - arrow_width - margin,
        preview_rect1.top + (preview_rect1.height - arrow_height) // 2,
        arrow_width,
        arrow_height,
    )
    p1_right_arrow_rect = pygame.Rect(
        preview_rect1.right + margin,
        preview_rect1.top + (preview_rect1.height - arrow_height) // 2,
        arrow_width,
        arrow_height,
    )
    p2_left_arrow_rect = pygame.Rect(
        preview_rect2.left - arrow_width - margin,
        preview_rect2.top + (preview_rect2.height - arrow_height) // 2,
        arrow_width,
        arrow_height,
    )
    p2_right_arrow_rect = pygame.Rect(
        preview_rect2.right + margin,
        preview_rect2.top + (preview_rect2.height - arrow_height) // 2,
        arrow_width,
        arrow_height,
    )

    while True:
        if not cap_lobby.isOpened():
            assets["video_lobby"] = cv2.VideoCapture("лобби.mp4")
            cap_lobby = assets["video_lobby"]

        lobby_surf = get_frame_surface(cap_lobby, SCREEN_WIDTH, SCREEN_HEIGHT)
        if lobby_surf:
            screen.blit(lobby_surf, (0, 0))
        else:
            screen.fill(WHITE)

        # Отрисовка превью для Player 1 (без зеркалирования)
        if options[player1_index] == "ai":
            ai_img_scaled = pygame.transform.scale(
                ai_image, (preview_rect1.width, preview_rect1.height)
            )
            screen.blit(ai_img_scaled, preview_rect1.topleft)
        else:
            if options[player1_index] == "durov":
                matrix_frames = assets["matrix_durov"]
            else:
                matrix_frames = assets["matrix_pepe"]
            frame_index = int(
                ((time.time() - left_matrix_time) * 10) % len(matrix_frames)
            )
            scaled_matrix = pygame.transform.scale(
                matrix_frames[frame_index], (preview_rect1.width, preview_rect1.height)
            )
            screen.blit(scaled_matrix, preview_rect1.topleft)

        # Отрисовка превью для Player 2:
        # Если выбран вариант "ai" – отрисовываем без изменений, иначе зеркалим матричную анимацию.
        if options[player2_index] == "ai":
            ai_img_scaled = pygame.transform.scale(
                ai_image, (preview_rect2.width, preview_rect2.height)
            )
            screen.blit(ai_img_scaled, preview_rect2.topleft)
        else:
            if options[player2_index] == "durov":
                matrix_frames = assets["matrix_durov"]
            else:
                matrix_frames = assets["matrix_pepe"]
            frame_index = int(
                ((time.time() - right_matrix_time) * 10) % len(matrix_frames)
            )
            # Зеркалим выбранный кадр по горизонтали:
            frame = matrix_frames[frame_index]
            flipped_frame = pygame.transform.flip(frame, True, False)
            scaled_matrix = pygame.transform.scale(
                flipped_frame, (preview_rect2.width, preview_rect2.height)
            )
            screen.blit(scaled_matrix, preview_rect2.topleft)

        current_time = time.time()
        if current_time - left_glow_time < glow_duration:
            frame_index = int(
                ((current_time - left_glow_time) / glow_duration)
                * len(left_glow_frames)
            )
            if frame_index >= len(left_glow_frames):
                frame_index = len(left_glow_frames) - 1
            glow_frame = left_glow_frames[frame_index]
            scaled_glow = pygame.transform.scale(
                glow_frame, (SCREEN_WIDTH, SCREEN_HEIGHT)
            )
            screen.blit(scaled_glow, (0, 0))
        if current_time - right_glow_time < glow_duration:
            frame_index = int(
                ((current_time - right_glow_time) / glow_duration)
                * len(right_glow_frames)
            )
            if frame_index >= len(right_glow_frames):
                frame_index = len(right_glow_frames) - 1
            glow_frame = right_glow_frames[frame_index]
            scaled_glow = pygame.transform.scale(
                glow_frame, (SCREEN_WIDTH, SCREEN_HEIGHT)
            )
            screen.blit(scaled_glow, (0, 0))

        screen.blit(left_arrow_img, p1_left_arrow_rect)
        screen.blit(right_arrow_img, p1_right_arrow_rect)
        screen.blit(left_arrow_img, p2_left_arrow_rect)
        screen.blit(right_arrow_img, p2_right_arrow_rect)

        shop_button.draw(screen)

        start_game_frames = assets["start_game_anim"]
        anim_elapsed = time.time() - start_game_anim_start
        anim_frame_index = int(anim_elapsed * 10) % len(start_game_frames)
        anim_frame = start_game_frames[anim_frame_index]
        scaled_anim_frame = pygame.transform.scale(
            anim_frame, (start_button.rect.width, start_button.rect.height)
        )
        screen.blit(scaled_anim_frame, start_button.rect.topleft)

        for event in pygame.event.get():
            if event.type == QUIT:
                cap_lobby.release()
                pygame.quit()
                sys.exit()
            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                pos = pygame.mouse.get_pos()
                if p1_left_arrow_rect.collidepoint(pos):
                    player1_index = (player1_index - 1) % len(options)
                    left_glow_time = time.time()
                    left_matrix_time = time.time()
                elif p1_right_arrow_rect.collidepoint(pos):
                    player1_index = (player1_index + 1) % len(options)
                    left_glow_time = time.time()
                    left_matrix_time = time.time()
                if p2_left_arrow_rect.collidepoint(pos):
                    player2_index = (player2_index - 1) % len(options)
                    right_glow_time = time.time()
                    right_matrix_time = time.time()
                elif p2_right_arrow_rect.collidepoint(pos):
                    player2_index = (player2_index + 1) % len(options)
                    right_glow_time = time.time()
                    right_matrix_time = time.time()
                if shop_button.is_clicked(pos):
                    shop_screen()
                    cap_lobby.set(cv2.CAP_PROP_POS_FRAMES, 0)
                if start_button.is_clicked(pos):
                    cap_lobby.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    player1_choice = options[player1_index]
                    player2_choice = options[player2_index]
                    cap_lobby.release()
                    main_game(player1_choice, player2_choice, assets)
                    assets["video_lobby"] = cv2.VideoCapture("лобби.mp4")
                    cap_lobby = assets["video_lobby"]
                    start_game_anim_start = time.time()

        pygame.display.flip()
        clock.tick(FPS)


def main():
    assets = load_all_assets()
    main_menu(assets)


if __name__ == "__main__":
    main()
